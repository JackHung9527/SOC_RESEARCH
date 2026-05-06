#!/usr/bin/env python3
"""IT8512A+ — set CC mode @ 5 A and turn the input ON.

Per IT8500+ programming guide:
  SYSTem:REMote                   enter remote mode (required to drive INPut)
  [SOURce:]FUNCtion CC            set Constant Current mode
  [SOURce:]CURRent <NRf+>         set CC level in amps
  [SOURce:]INPut ON               enable the load input ("load on")
  MEASure:VOLTage:DC?             read back terminal voltage
  MEASure:CURRent:DC?             read back actual sink current
  MEASure:POWer:DC?               read back actual power
"""
from __future__ import annotations

import sys
import time

import serial


PORT = "/dev/ttyACM0"  # IT8512A confirmed by *IDN?
BAUD = 9600
CC_AMPS = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0


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

        print(f"IDN  : {query(ser, '*IDN?')}")

        send(ser, "SYST:REM")               # remote
        send(ser, "FUNC CC")                # CC mode
        send(ser, f"CURR {CC_AMPS:.3f}")    # 5 A
        send(ser, "INP ON")                 # load on
        time.sleep(0.3)

        print(f"FUNC : {query(ser, 'FUNC?')}")
        print(f"CURR?: {query(ser, 'CURR?')} A  (set point)")
        print(f"INP? : {query(ser, 'INP?')}    (1 = ON)")

        time.sleep(0.2)
        v = query(ser, "MEAS:VOLT?")
        i = query(ser, "MEAS:CURR?")
        p = query(ser, "MEAS:POW?")
        print(f"\nMeasured -> V = {v} V , I = {i} A , P = {p} W")

    return 0


if __name__ == "__main__":
    sys.exit(main())
