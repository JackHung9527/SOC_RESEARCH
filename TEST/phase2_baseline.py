#!/usr/bin/env python3
"""Phase 2 — new-cell baseline CC discharge with periodic dV/dI perturbation.

Per meeting_0416 slide 7:
    "CC 放電 (0.5C) 100%→0% / 記錄 V, I, dV/dI vs SOC / 擬合拋物線參數 a, b, c
     記錄 a_origin 作為 SOH 基準"

A pure CC discharge gives V vs SoC but dI ≈ 0, so dV/dI is undefined.
This script injects a brief current step every PHASE2.perturb_period_s:

    base CC (I_discharge_cc)  ──▶  perturb LOW (0.2C, 1 s) ──▶ base CC again
    ↑ measure V_high,I_high            ↑ measure V_low,I_low
                                       └─ dV/dI = ΔV / ΔI

Pre-conditions:
  - Active battery profile selected (TEST/select_battery.py)
  - Cell has been charged to full and rested at OCV (≥ 30 min recommended)
  - Load wired across the cell with correct polarity
  - PSU output is OFF (BenchInterlock will verify)

Safety: BenchInterlock blocks load.input_on() until PSU is verified OFF.
SafetyGuard absolute envelope = chemistry V_abs_max / V_abs_min (instant trip).

Usage:
  python3 TEST/phase2_baseline.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from TEST.config import BAUD, PHASE2, PORT_LOAD, PORT_PSU, SAFETY, require_battery
from TEST.core.bench import BenchInterlock, BenchInterlockError
from TEST.core.coulomb import CoulombCounter
from TEST.core.logger import CsvLogger
from TEST.core.safety import SafetyAbort, SafetyGuard
from TEST.drivers.it6302 import IT6302
from TEST.drivers.it8512 import IT8512
from TEST.profiles import print_summary


DATA_DIR = Path(__file__).resolve().parent / "data"
SAMPLE_DT = SAFETY.sample_period_s


def perturb_step(load: IT8512, base_A: float, low_A: float, dwell_s: float):
    """Run one base→low→base step. Returns (V_low, I_low, V_high, I_high)."""
    load.set_cc(low_A)
    time.sleep(dwell_s)
    v_lo = load.measure_voltage()
    i_lo = load.measure_current()

    load.set_cc(base_A)
    time.sleep(dwell_s)
    v_hi = load.measure_voltage()
    i_hi = load.measure_current()
    return v_lo, i_lo, v_hi, i_hi


def main() -> int:
    battery = require_battery()
    print_summary(battery)

    base_A = battery.i_discharge_cc
    low_A = battery.q_rated_mAh / 1000.0 * PHASE2.perturb_low_C
    print(f"[phase2] base CC={base_A:.3f} A, perturb low={low_A:.3f} A "
          f"every {PHASE2.perturb_period_s} s")
    print(f"[phase2] discharge cutoff V<{battery.v_discharge_cutoff:.3f} V")

    guard = SafetyGuard.from_profile(battery, i_hard_high=SAFETY.i_hard_high)
    coul = CoulombCounter(q_rated_mAh=battery.q_rated_mAh, soc_init=1.0)
    logger = CsvLogger(DATA_DIR, tag="phase2_baseline")
    print(f"[phase2] log -> {logger.path}")

    with IT6302.open(PORT_PSU, BAUD) as psu, IT8512.open(PORT_LOAD, BAUD) as load:
        print(f"[phase2] PSU: {psu.idn()}")
        print(f"[phase2] LOAD: {load.idn()}")

        bench = BenchInterlock(psu=psu, load=load, deadtime_s=SAFETY.deadtime_s)
        try:
            # 1) Force both outputs OFF and confirm by readback.
            bench.assert_idle()

            # 2) Configure load: CC mode, instrument-level UVP at cutoff.
            load.set_mode("CC")
            load.set_cc(base_A)
            load.set_voltage_off_threshold(battery.v_discharge_cutoff)
            load.set_current_protection(SAFETY.i_hard_high)

            # 3) Pre-rest sample (load still off — read via load's MEAS:VOLT
            #    requires INP ON, so we briefly bring it up at 10 mA, sample,
            #    then back down through the interlock).
            bench.start_discharge()
            load.set_cc(0.010)
            time.sleep(0.5)
            v_pre = load.measure_voltage()
            print(f"[phase2] OCV precheck = {v_pre:.4f} V")
            if v_pre < battery.v_charge_cutoff - 0.10:
                print(f"[phase2] WARN: cell not full ({v_pre:.3f} V < "
                      f"{battery.v_charge_cutoff:.2f} V) — run charge.py first.")
            if v_pre < battery.v_discharge_cutoff:
                print("[phase2] ABORT: cell already below cutoff voltage.")
                bench.stop_discharge()
                return 1

            # 4) Pre-discharge rest at near-zero current — log V at 1 Hz.
            print(f"[phase2] pre-rest {PHASE2.pre_rest_s} s (OCV settle)...")
            t0 = time.monotonic()
            while time.monotonic() - t0 < PHASE2.pre_rest_s:
                t = time.monotonic() - t0
                v = load.measure_voltage()
                guard.check(v, 0.0)
                logger.log(t, "rest", v, 0.0, soc_cc=coul.soc, note="pre-rest")
                time.sleep(SAMPLE_DT)

            # 5) Start CC discharge.
            print("[phase2] starting CC discharge")
            load.set_cc(base_A)
            time.sleep(0.5)

            t_start = time.monotonic()
            t_last = t_start
            t_next_perturb = t_start + PHASE2.perturb_period_s

            while True:
                now = time.monotonic()
                t = now - t_start
                v = load.measure_voltage()
                i = load.measure_current()

                dt = now - t_last
                t_last = now
                soc = coul.update(i, dt)

                guard.check(v, i)

                if v <= battery.v_discharge_cutoff:
                    logger.log(t, "discharge", v, i, soc, note="cutoff")
                    print(f"[phase2] cutoff reached at t={t:.1f}s "
                          f"(V={v:.3f}, SoC_cc={soc:.3f}, "
                          f"Ah_used={coul.ah_used:.3f})")
                    break

                logger.log(t, "discharge", v, i, soc)
                if int(t) % 30 == 0:
                    print(f"  t={t:7.1f}s  V={v:.4f}  I={i:.4f}  "
                          f"SoC={soc * 100:5.1f}%")

                if now >= t_next_perturb:
                    v_lo, i_lo, v_hi, i_hi = perturb_step(
                        load, base_A=base_A, low_A=low_A,
                        dwell_s=PHASE2.perturb_dwell_s,
                    )
                    di = i_hi - i_lo
                    dvdi = (v_hi - v_lo) / di if abs(di) > 1e-6 else float("nan")
                    t_lo = time.monotonic() - t_start
                    logger.log(t_lo, "perturb_low", v_lo, i_lo, soc,
                               note=f"step_to_{low_A:.3f}A")
                    logger.log(time.monotonic() - t_start, "perturb_high",
                               v_hi, i_hi, soc, dvdi=dvdi,
                               note=f"step_to_{base_A:.3f}A")
                    print(f"  [perturb] V_lo={v_lo:.4f} V_hi={v_hi:.4f} "
                          f"dI={di:.3f} → dV/dI={dvdi * 1000:.2f} mΩ")
                    t_next_perturb = time.monotonic() + PHASE2.perturb_period_s
                else:
                    time.sleep(SAMPLE_DT)

        except KeyboardInterrupt:
            print("\n[phase2] interrupted by user")
        except SafetyAbort as e:
            print(f"\n[phase2] !!! SAFETY ABORT: {e}")
        except BenchInterlockError as e:
            print(f"\n[phase2] !!! BENCH INTERLOCK: {e}")
        finally:
            try:
                bench.stop_discharge()
            except Exception:
                bench.emergency_stop()
            logger.close()

    print(f"[phase2] done. CSV: {logger.path}")
    print(f"[phase2] dead-time {SAFETY.deadtime_s:.0f} s — wait before reconnecting PSU.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
