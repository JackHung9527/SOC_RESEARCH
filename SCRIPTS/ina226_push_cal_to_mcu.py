#!/usr/bin/env python3
"""Push the 14-point INA226 calibration table to the MCU via UART CLI.

Reads TEST/data/calibration_ina226.json (produced by ina226_calibrate.py),
merges charge + discharge into a single signed LUT (charge ref_A flipped to
negative to preserve current direction), and pipes:

    CAL_RESET
    CAL_PUSH <raw_ma_signed> <ref_ma_signed>     × N (13 unique points)
    CAL_COMMIT
    CAL_DUMP
    CAL_GET_I

into /dev/ttyACM2. After CAL_COMMIT, the calibration record lives in flash
page 63 (0x0801_F800) and is auto-loaded on every boot.

The heartbeat keeps streaming while we do this; we filter for lines that
look like firmware responses ("OK", "ERR", "DUMP", "RAW", "CAL_I").
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import serial


VCP = "/dev/ttyACM2"
BAUD = 115200
CAL_FILE = Path(__file__).resolve().parent.parent / "TEST" / "data" / "calibration_ina226.json"


RESP_RX = re.compile(r"^(OK|ERR|DUMP|RAW|CAL_I|P\d+|CMD:)")


def merge_signed_points(raw: dict) -> list[tuple[float, float]]:
    """Return list of (raw_mA, ref_mA) with sign preserved.

    Discharge: positive raw, positive ref (current leaving cell).
    Charge:    negative raw (firmware reports negative through shunt),
               flip ref sign too so cal output is negative = charging.
    """
    points: dict[float, float] = {}   # keyed by raw_mA to dedupe zero point
    for p in raw["discharge"]:
        r_ma = p["mcu_A"] * 1000.0
        f_ma = p["ref_A"] * 1000.0   # positive: discharging
        points[round(r_ma, 4)] = f_ma
    for p in raw["charge"]:
        r_ma = p["mcu_A"] * 1000.0
        f_ma = -p["ref_A"] * 1000.0  # NEGATE: charging direction
        # Don't overwrite the shared zero point if it already came in from discharge
        if round(r_ma, 4) in points and abs(p["ref_A"]) < 0.001:
            continue
        points[round(r_ma, 4)] = f_ma

    # Sort ascending by raw_mA so the CLI sees a monotonic table (firmware
    # also sorts on commit, but cleaner to feed in order).
    return sorted(points.items(), key=lambda t: t[0])


def send_line(ser: serial.Serial, line: str) -> list[str]:
    """Send one CLI command, return response lines until next idle gap.

    The heartbeat stream is filtered out; only response-shaped lines are
    returned. We collect for up to 0.6 s after the last response line.
    """
    ser.reset_input_buffer()
    ser.write((line + "\r\n").encode("ascii"))
    ser.flush()
    out: list[str] = []
    deadline = time.monotonic() + 1.5
    last_resp = time.monotonic()
    while time.monotonic() < deadline:
        raw_ln = ser.readline()
        if not raw_ln:
            if time.monotonic() - last_resp > 0.4 and out:
                break
            continue
        text = raw_ln.decode(errors="replace").rstrip("\r\n")
        if RESP_RX.match(text):
            out.append(text)
            last_resp = time.monotonic()
        # else: heartbeat / banner line — skip
    return out


def main() -> int:
    raw = json.loads(CAL_FILE.read_text())
    points = merge_signed_points(raw)

    print(f"=== INA226 cal push ===")
    print(f"  source : {CAL_FILE}")
    print(f"  merged : {len(points)} unique points (signed)")
    for r, f in points:
        print(f"    raw={r:+10.3f} mA   ref={f:+10.3f} mA")
    print(f"  target : {VCP}")

    if len(points) > 16:
        print(f"!! too many points ({len(points)}); INA_CAL_MAX_POINTS=16 in firmware")
        return 1

    with serial.Serial(VCP, BAUD, timeout=0.2) as ser:
        ser.reset_input_buffer()

        print("\n>>> CAL_RESET")
        for ln in send_line(ser, "CAL_RESET"):
            print(f"  < {ln}")

        for i, (raw_mA, ref_mA) in enumerate(points, 1):
            cmd = f"CAL_PUSH {raw_mA:.3f} {ref_mA:.3f}"
            print(f">>> [{i}/{len(points)}] {cmd}")
            for ln in send_line(ser, cmd):
                print(f"  < {ln}")

        print("\n>>> CAL_COMMIT")
        for ln in send_line(ser, "CAL_COMMIT"):
            print(f"  < {ln}")

        print("\n>>> CAL_DUMP")
        for ln in send_line(ser, "CAL_DUMP"):
            print(f"  < {ln}")

        print("\n>>> CAL_GET_I  (one-shot read of current INA226 → cal)")
        for ln in send_line(ser, "CAL_GET_I"):
            print(f"  < {ln}")

    print("\nDone. The flash record will auto-load on next boot via")
    print("ina_cal_init() — `cal=on` should appear in subsequent heartbeats.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
