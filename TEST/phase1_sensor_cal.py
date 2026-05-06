#!/usr/bin/env python3
"""Phase 1 — sensor calibration (placeholder).

Per meeting_0416 slide 7:
    1. INA226 偏移校正
    2. 與 DMM 比對電壓/電流精度
    3. 確認 I2C 通訊穩定性
    4. 設定 Shunt Resistor 倍率

This script is a stub until the STM32 + INA226 hardware is online. It will
read INA226 over I2C from the MCU (via UART forward), sweep the IT6302
through known V/I points, and emit per-sample errors vs. a DMM-stored
reference table.

For now, when run, it just prints the planned sequence and exits — kept
in the repo so the test framework imports stay honest and the phase
ordering matches the slide deck.
"""
from __future__ import annotations

import sys


PLAN = [
    ("0.0 V", "0.0 A", "INA226 zero-offset reading (both V and I shunt)"),
    ("3.7 V", "0.5 A", "Mid-range linearity vs. DMM"),
    ("4.2 V", "1.075 A", "Operating CC point (matches Phase 2 baseline)"),
    ("4.2 V", "2.0 A", "High-current sanity (1C)"),
]


def main() -> int:
    print("[phase1] sensor calibration — STUB (waiting on INA226+STM32 hookup)")
    print("[phase1] planned sweep:")
    for v, i, note in PLAN:
        print(f"  V={v:>6}  I={i:>7}  — {note}")
    print("[phase1] when MCU is online, fill in:")
    print("         - UART read of INA226 frames from STM32")
    print("         - DMM golden values via JSON config")
    print("         - per-point error log → data/phase1_cal_*.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
