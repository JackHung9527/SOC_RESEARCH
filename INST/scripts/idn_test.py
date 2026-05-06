#!/usr/bin/env python3
"""Probe ITECH instruments on /dev/ttyACM0 and /dev/ttyACM1.

Tries two protocols:
  1) SCPI ASCII (`*IDN?`) with \\n, \\r, \\r\\n terminators — used by IT6302.
  2) ITECH legacy 26-byte binary frame, command 0x6A "read product info" —
     used by IT8500+ series including IT8512A+ when SCPI mode is off.
"""
from __future__ import annotations

import sys
import time

import serial


PORTS = ["/dev/ttyACM0", "/dev/ttyACM1"]
BAUDS = [9600, 4800, 19200, 38400, 115200]


def open_port(port: str, baud: int) -> serial.Serial:
    return serial.Serial(
        port=port,
        baudrate=baud,
        bytesize=8,
        parity=serial.PARITY_NONE,
        stopbits=1,
        timeout=0.6,
        write_timeout=0.6,
    )


def try_scpi(port: str, baud: int) -> bytes | None:
    """Send *IDN? with a few terminators; return any response bytes."""
    for term in (b"\n", b"\r\n", b"\r"):
        try:
            with open_port(port, baud) as ser:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.write(b"*IDN?" + term)
                ser.flush()
                time.sleep(0.25)
                resp = ser.read(256)
                if resp:
                    return resp
        except serial.SerialException:
            return None
    return None


def itech_frame(addr: int, cmd: int, data: bytes = b"") -> bytes:
    body = bytes([0xAA, addr, cmd]) + data.ljust(22, b"\x00")
    chk = sum(body) & 0xFF
    return body + bytes([chk])


def try_itech_binary(port: str, baud: int) -> bytes | None:
    """Send 26-byte ITECH frame, cmd 0x6A (read product info)."""
    frame = itech_frame(addr=0x00, cmd=0x6A)
    for addr in (0x00, 0x01, 0xFE):
        frame = itech_frame(addr=addr, cmd=0x6A)
        try:
            with open_port(port, baud) as ser:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.write(frame)
                ser.flush()
                time.sleep(0.3)
                resp = ser.read(26)
                if resp:
                    return resp
        except serial.SerialException:
            return None
    return None


def probe(port: str) -> None:
    print(f"\n=== {port} ===")
    for baud in BAUDS:
        scpi = try_scpi(port, baud)
        if scpi:
            print(f"  [SCPI  @ {baud:>6}] *IDN? -> {scpi!r}")
            return
        bin_resp = try_itech_binary(port, baud)
        if bin_resp:
            print(f"  [ITECH @ {baud:>6}] 0x6A   -> {bin_resp.hex(' ')}")
            # Decode product info frame: bytes 3..7 = model ASCII
            model = bin_resp[3:8].rstrip(b"\x00").decode("ascii", errors="replace")
            print(f"                       model field   = {model!r}")
            return
        print(f"  [{baud:>6}] no response (SCPI nor binary)")
    print("  -> no answer at any baud / protocol")


def main() -> int:
    for p in PORTS:
        probe(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
