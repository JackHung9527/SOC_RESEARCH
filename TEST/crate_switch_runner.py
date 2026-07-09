#!/usr/bin/env python3
"""C-rate 切換壓力測試（表 4-5 第二列）。

流程：充 0.5C 至截止（複用 round_runner.run_charge_step，含 already-full
bypass 與 CC-CV 終止紀律）→ 休 30 min（板端充飽自動重錨窗）→ 放電中做
倍率階梯切換至截止。放電段**不做**例行 dV/dI 擾動——切換本身就是受測事件。

階梯（各段時長見 LADDER；末段放到截止）：
    0.5C → 2.0C → 0.5C → 1.5C → 1.0C → 2.0C(→cutoff)
共 5 個切換點，SOC 覆蓋約 95% 至截止。

產出：TEST/data/crateswitch_<ts>.csv（t_s, mode, v, i, soc_cc, note；
切換樣本 note=switch_to_<rate>C）。板端三法輸出由 mcu_uart_logger 並行收。
本測試不寫 cycle_log（非標準 cycle，避免污染輪次統計）。

用法：
    python3 TEST/crate_switch_runner.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from TEST.config import BAUD, PORT_LOAD, PORT_PSU, SAFETY, require_battery
from TEST.core.bench import BenchInterlock, BenchInterlockError
from TEST.core.coulomb import CoulombCounter
from TEST.core.logger import CsvLogger
from TEST.core.safety import SafetyAbort, SafetyGuard
from TEST.drivers.it6302 import IT6302
from TEST.drivers.it8512 import IT8512
from TEST.profiles import print_summary
from TEST.round_runner import DATA_DIR, SAMPLE_DT, run_charge_step, run_rest_step

# (C-rate, 段長秒)；末段 None = 放到截止
LADDER: list[tuple[float, Optional[float]]] = [
    (0.5, 480.0),
    (2.0, 480.0),
    (0.5, 480.0),
    (1.5, 480.0),
    (1.0, 480.0),
    (2.0, None),
]

CHARGE_RATE_C = 0.5
REST_S = 30 * 60.0


def run_ladder_discharge(load, bench, battery, guard) -> str:
    c1_A = battery.q_rated_mAh / 1000.0
    v_cutoff = battery.v_discharge_cutoff
    logger = CsvLogger(DATA_DIR, tag="crateswitch")
    print(f"  [ladder] → {logger.path.name}")
    for k, (c, dur) in enumerate(LADDER):
        print(f"    stage {k}: {c:.1f}C"
              + (f" × {dur:.0f}s" if dur else " → cutoff"))

    stage = 0
    i_cc = LADDER[0][0] * c1_A
    load.set_mode("CC")
    load.set_cc(i_cc)
    load.set_voltage_off_threshold(v_cutoff)
    load.set_current_protection(SAFETY.i_hard_high)

    bench.start_discharge()
    time.sleep(0.5)

    t0 = time.monotonic()
    t_stage0 = t0
    coul = CoulombCounter(q_rated_mAh=battery.q_rated_mAh, soc_init=1.0)
    t_last = t0
    note = "cutoff"
    try:
        while True:
            now = time.monotonic()
            t = now - t0
            v = load.measure_voltage()
            i = load.measure_current()
            dt = now - t_last
            t_last = now
            soc = coul.update(i, dt)

            if v <= v_cutoff:
                logger.log(t, "discharge", v, i, soc, note="cutoff")
                break
            guard.check(v, i)

            dur = LADDER[stage][1]
            if dur is not None and (now - t_stage0) >= dur and stage + 1 < len(LADDER):
                stage += 1
                new_c = LADDER[stage][0]
                i_cc = new_c * c1_A
                load.set_cc(i_cc)
                t_stage0 = time.monotonic()
                logger.log(t, "discharge", v, i, soc,
                           note=f"switch_to_{new_c:.1f}C")
                print(f"    [switch] t={t:7.1f}s SoC={soc*100:5.1f}%  "
                      f"→ {new_c:.1f}C ({i_cc:.3f} A)")
                continue

            logger.log(t, "discharge", v, i, soc)
            if int(t) % 60 < 1:
                print(f"    t={t:7.1f}s  V={v:.4f}  I={i:+.4f}  "
                      f"SoC={soc*100:5.1f}%  [{LADDER[stage][0]:.1f}C]")
            time.sleep(SAMPLE_DT)
    finally:
        bench.stop_discharge()
        logger.close()
    print(f"  [ladder] done: q={coul.ah_used*1000:.1f} mAh  note={note}")
    return note


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    battery = require_battery()
    print_summary(battery)
    print("\nC-rate switch test plan:")
    print(f"  1. charge {CHARGE_RATE_C}C → term")
    print(f"  2. rest {REST_S/60:.0f} min (板端充飽自動重錨窗)")
    for k, (c, dur) in enumerate(LADDER):
        print(f"  3.{k} discharge {c:.1f}C"
              + (f" × {dur:.0f}s" if dur else " → cutoff"))
    if args.dry_run:
        print("\n--dry-run: not driving the bench. Exit.")
        return 0

    guard = SafetyGuard.from_profile(battery, i_hard_high=SAFETY.i_hard_high)
    with IT6302.open(PORT_PSU, BAUD) as psu, IT8512.open(PORT_LOAD, BAUD) as load:
        print(f"[crate_switch] PSU: {psu.idn()}")
        print(f"[crate_switch] LOAD: {load.idn()}")
        bench = BenchInterlock(psu=psu, load=load, deadtime_s=SAFETY.deadtime_s)
        try:
            bench.assert_idle()
            v0, v1, ah_in, _, note = run_charge_step(
                psu, load, bench, battery, CHARGE_RATE_C, guard,
                cycle_id=900, round_id=900,
            )
            print(f"[crate_switch] charge done: {v0:.3f}→{v1:.3f} V  "
                  f"ah_in={ah_in:.3f}  ({note})")
            run_rest_step(REST_S)
            run_ladder_discharge(load, bench, battery, guard)
            print("\n[crate_switch] COMPLETE")
        except KeyboardInterrupt:
            print("\n[crate_switch] interrupted — emergency stop")
        except (SafetyAbort, BenchInterlockError) as e:
            print(f"\n[crate_switch] !!! {type(e).__name__}: {e}")
        finally:
            bench.emergency_stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
