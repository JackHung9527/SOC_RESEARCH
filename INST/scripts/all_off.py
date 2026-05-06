#!/usr/bin/env python3
"""Kill switch — turn IT8512A+ load OFF and IT6302 all-channel output OFF."""
from __future__ import annotations

import sys
import time

import serial


LOAD_PORT = "/dev/ttyACM0"  # IT8512A
PSU_PORT = "/dev/ttyACM1"   # IT6302
BAUD = 9600


def open_port(port: str) -> serial.Serial:
    return serial.Serial(
        port=port, baudrate=BAUD, bytesize=8, parity=serial.PARITY_NONE,
        stopbits=1, timeout=0.6, write_timeout=0.6,
    )


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
    # 1) Load off first — drops the current draw before PSU collapses.
    with open_port(LOAD_PORT) as load:
        load.reset_input_buffer()
        load.reset_output_buffer()
        send(load, "SYST:REM")
        send(load, "INP OFF")
        time.sleep(0.2)
        print(f"[IT8512A] INP? = {query(load, 'INP?')}    (0 = OFF)")

    # 2) PSU off — disable all channels.
    with open_port(PSU_PORT) as psu:
        psu.reset_input_buffer()
        psu.reset_output_buffer()
        send(psu, "SYST:REM")
        send(psu, "OUTP OFF")              # OUTP[:STAT][:ALL] OFF
        time.sleep(0.2)
        print(f"[IT6302 ] OUTP? = {query(psu, 'OUTP?')}   (0 = OFF)")
        # Also report each channel just to be sure
        for ch in (1, 2, 3):
            send(psu, f"INST:NSEL {ch}")
            time.sleep(0.05)
            print(f"           CH{ch} CHAN:OUTP? = {query(psu, 'CHAN:OUTP?')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
