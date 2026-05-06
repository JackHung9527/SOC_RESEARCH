#!/usr/bin/env python3
"""IT6302 CH1 — set 5 V, current limit = MAX, output ON.

Per IT6302 programming guide:
  SYSTem:REMote                          enter remote mode
  INSTrument:NSELect 1                   select CH1
  [SOURce:]VOLTage <NRf+>                set output voltage
  [SOURce:]CURRent <NRf+> | MAX          set current limit
  [SOURce:]CHANnel:OUTPut ON             enable selected channel only
"""
from __future__ import annotations

import sys
import time

import serial


PORT = "/dev/ttyACM1"  # IT6302 confirmed by *IDN?
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

        print(f"IDN  : {query(ser, '*IDN?')}")

        send(ser, "SYST:REM")
        send(ser, "INST:NSEL 1")            # select CH1
        time.sleep(0.1)

        i_max = query(ser, "CURR? MAX")     # ask channel its own max
        print(f"CH1 CURR MAX = {i_max} A")

        send(ser, "VOLT 5.0")
        send(ser, f"CURR {i_max}")          # set to channel max
        send(ser, "CHAN:OUTP ON")           # enable CH1 output only
        time.sleep(0.3)

        print(f"\n--- CH1 readback ---")
        print(f"VOLT?    : {query(ser, 'VOLT?')} V  (set point)")
        print(f"CURR?    : {query(ser, 'CURR?')} A  (limit)")
        print(f"OUTP?    : {query(ser, 'CHAN:OUTP?')}    (1 = ON)")
        time.sleep(0.2)
        print(f"MEAS V   : {query(ser, 'MEAS:VOLT?')} V")
        print(f"MEAS I   : {query(ser, 'MEAS:CURR?')} A")
        print(f"MEAS P   : {query(ser, 'MEAS:POW?')} W")

    return 0


if __name__ == "__main__":
    sys.exit(main())
