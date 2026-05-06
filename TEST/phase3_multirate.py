#!/usr/bin/env python3
"""Phase 3 — multi-rate + pulse discharge (skeleton).

Per meeting_0416 slide 7:
    1. 不同放電倍率 (0.2C ~ 2C)
    2. 脈衝放電模式 (10s ON / 30s OFF)
    3. 驗證動態阻抗即時追蹤
    4. 比對庫侖計數法結果

The framework is in place (drivers / safety / logger / coulomb). This
script will run after Phase 2 baseline confirms the rig is healthy. The
shape of each sub-test is sketched below; fill in once Phase 2 data is in.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from TEST.config import PHASE3_PULSE_OFF_S, PHASE3_PULSE_ON_S, PHASE3_RATES


def main() -> int:
    print("[phase3] multi-rate sweep — SKELETON")
    print(f"[phase3] planned C-rates: {PHASE3_RATES}")
    print(f"[phase3] pulse profile : {PHASE3_PULSE_ON_S}s ON / {PHASE3_PULSE_OFF_S}s OFF")
    print("[phase3] sub-test skeleton:")
    print("  for each C-rate in PHASE3_RATES:")
    print("    1. fully charge (run charge.py or call routine)")
    print("    2. rest 30 min")
    print("    3. CC discharge at this rate to V_min, log V/I/dV-dI")
    print("    4. record actual capacity (Ah_used) for capacity-vs-rate curve")
    print("  then pulse profile run:")
    print("    a. CC at 0.5C base, every cycle: 10s at 1C, 30s rest at 0A")
    print("    b. each pulse edge gives a clean dV/dI sample")
    return 0


if __name__ == "__main__":
    sys.exit(main())
