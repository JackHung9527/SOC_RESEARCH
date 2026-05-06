#!/usr/bin/env python3
"""IT8512A+ kill switch — turn the load input OFF."""
from __future__ import annotations

import sys
import time

import serial


PORT = "/dev/ttyACM0"
BAUD = 9600


def send(ser: serial.Serial, cmd: str) -> None:
    ser.write((cmd + "\n").encode("ascii"))
    ser.flush()
    time.sleep(0.05)


def query(ser: serial.Serial, cmd: str) -> str:
    ser.reset_input_buffer()
    send(ser, cmd)
    time.sleep(0.15)
    return ser.read(128).decode("ascii", errors="replace").strip()


def main() -> int:
    with serial.Serial(
        port=PORT, baudrate=BAUD, bytesize=8, parity=serial.PARITY_NONE,
        stopbits=1, timeout=0.6, write_timeout=0.6,
    ) as ser:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        send(ser, "SYST:REM")
        send(ser, "INP OFF")
        time.sleep(0.2)
        print(f"INP? : {query(ser, 'INP?')}    (0 = OFF)")
        print(f"V    : {query(ser, 'MEAS:VOLT?')} V")
        print(f"I    : {query(ser, 'MEAS:CURR?')} A")
    return 0


if __name__ == "__main__":
    sys.exit(main())
