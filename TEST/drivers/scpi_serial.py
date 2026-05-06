"""Thin SCPI-over-serial helper shared by IT6302 and IT8512A+ drivers."""
from __future__ import annotations

import time
from typing import Optional

import serial


class ScpiSerial:
    def __init__(self, port: str, baud: int = 9600, timeout: float = 0.6):
        self._ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=8,
            parity=serial.PARITY_NONE,
            stopbits=1,
            timeout=timeout,
            write_timeout=timeout,
        )
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

    def close(self) -> None:
        if self._ser.is_open:
            self._ser.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def write(self, cmd: str) -> None:
        self._ser.write((cmd + "\n").encode("ascii"))
        self._ser.flush()
        # ITECH boxes need a brief gap between back-to-back writes.
        time.sleep(0.05)

    def query(self, cmd: str, settle_s: float = 0.15) -> str:
        self._ser.reset_input_buffer()
        self.write(cmd)
        time.sleep(settle_s)
        return self._ser.read(256).decode("ascii", errors="replace").strip()

    def query_float(self, cmd: str, default: Optional[float] = None) -> float:
        raw = self.query(cmd)
        try:
            return float(raw.split(",")[0])
        except (ValueError, IndexError):
            if default is not None:
                return default
            raise RuntimeError(f"query {cmd!r} returned non-float: {raw!r}")
