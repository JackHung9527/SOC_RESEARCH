#!/usr/bin/env python3
"""Phase 2 — new-cell baseline CC discharge with periodic dV/dI perturbation.

Per meeting_0416 slide 7:
    "CC 放電 (0.5C) 100%→0% / 記錄 V, I, dV/dI vs SOC / 擬合拋物線參數 a, b, c
     記錄 a_origin 作為 SOH 基準"

A pure CC discharge gives V vs SoC but dI ≈ 0, so dV/dI is undefined.
This script injects a brief current step every PHASE2.perturb_period_s:

    base CC (1.075A)  ──▶  perturb LOW (0.43A, 0.2C) ──▶ base CC again
    ↑ measure V_high,I_high       ↑ measure V_low,I_low
                                  └─ dV/dI = (V_high − V_low) / (I_high − I_low)

The baseline V, I, SoC stream is written every 1 s; perturb events are
tagged in the `mode` column ("perturb_low" / "perturb_high") and carry
the resulting dV/dI value on the perturb_high row.

Pre-conditions:
  - Cell has been charged to full and rested at OCV (≥ 30 min recommended)
  - PSU CH1 output is OFF (this script does not touch the PSU)
  - Load is wired across the cell with correct polarity

Usage:
  python3 TEST/phase2_baseline.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from TEST.config import BAUD, BATTERY, PHASE2, PORT_LOAD, PORT_PSU, SAFETY
from TEST.core.coulomb import CoulombCounter
from TEST.core.logger import CsvLogger
from TEST.core.safety import SafetyAbort, SafetyGuard
from TEST.drivers.it6302 import IT6302
from TEST.drivers.it8512 import IT8512


DATA_DIR = Path(__file__).resolve().parent / "data"
SAMPLE_DT = SAFETY.sample_period_s


def assert_psu_off() -> None:
    """Verify PSU CH1 is off so we don't fight against a charge source."""
    with IT6302.open(PORT_PSU, BAUD) as psu:
        psu.all_outputs(False)


def precheck_voltage(load: IT8512) -> float:
    """Briefly enable the load at near-zero current to read the cell OCV.

    The load needs INP ON to take a measurement; we enable it at the smallest
    representative draw (10 mA) for one sample, then disable.
    """
    load.set_mode("CC")
    load.set_cc(0.010)
    load.input_on()
    time.sleep(0.5)
    v = load.measure_voltage()
    load.input_off()
    return v


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
    base_A = BATTERY.i_discharge_cc
    low_A = BATTERY.q_rated_mAh / 1000.0 * PHASE2.perturb_low_C
    print(f"[phase2] battery={BATTERY.name} Q={BATTERY.q_rated_mAh:.0f} mAh")
    print(f"[phase2] base CC={base_A:.3f} A, perturb low={low_A:.3f} A "
          f"every {PHASE2.perturb_period_s} s")
    print(f"[phase2] cutoff V<{BATTERY.v_min:.2f} V")

    assert_psu_off()

    guard = SafetyGuard(
        v_high=SAFETY.v_hard_high,
        v_low=SAFETY.v_hard_low,
        i_high=SAFETY.i_hard_high,
    )
    coul = CoulombCounter(q_rated_mAh=BATTERY.q_rated_mAh, soc_init=1.0)
    logger = CsvLogger(DATA_DIR, tag="phase2_baseline")
    print(f"[phase2] log -> {logger.path}")

    with IT8512.open(PORT_LOAD, BAUD) as load:
        print(f"[phase2] {load.idn()}")
        load.set_mode("CC")
        load.set_cc(base_A)
        load.set_voltage_off_threshold(BATTERY.v_min)   # instrument auto-cut on UV

        # 1) Precheck — read OCV before any real load is applied
        v_pre = precheck_voltage(load)
        print(f"[phase2] OCV precheck = {v_pre:.4f} V")
        if v_pre < BATTERY.v_max - 0.10:
            print(f"[phase2] WARN: cell not full ({v_pre:.3f} V < {BATTERY.v_max:.2f} V) — "
                  "run TEST/charge.py first if you want a clean baseline.")
        if v_pre < BATTERY.v_min:
            print("[phase2] ABORT: cell already below cutoff voltage.")
            return 1

        # 2) Pre-discharge rest (OCV settle) — log V at 1 Hz
        print(f"[phase2] pre-rest {PHASE2.pre_rest_s} s (OCV settle)...")
        t0 = time.monotonic()
        try:
            while time.monotonic() - t0 < PHASE2.pre_rest_s:
                t = time.monotonic() - t0
                v = load.measure_voltage()
                guard.check(v, 0.0)
                logger.log(t, "rest", v, 0.0, soc_cc=coul.soc, note="pre-rest")
                time.sleep(SAMPLE_DT)

            # 3) Start CC discharge
            print("[phase2] starting CC discharge")
            load.set_cc(base_A)
            load.input_on()
            time.sleep(0.5)

            t_start = time.monotonic()
            t_last = t_start
            t_next_perturb = t_start + PHASE2.perturb_period_s

            while True:
                now = time.monotonic()
                t = now - t_start
                v = load.measure_voltage()
                i = load.measure_current()

                # update SoC integrator (positive I = discharge → SoC drops)
                dt = now - t_last
                t_last = now
                soc = coul.update(i, dt)

                guard.check(v, i)

                # Cutoff
                if v <= BATTERY.v_min:
                    logger.log(t, "discharge", v, i, soc, note="cutoff")
                    print(f"[phase2] cutoff reached at t={t:.1f}s "
                          f"(V={v:.3f}, SoC_cc={soc:.3f}, Ah_used={coul.ah_used:.3f})")
                    break

                logger.log(t, "discharge", v, i, soc)
                if int(t) % 30 == 0:
                    print(f"  t={t:7.1f}s  V={v:.4f}  I={i:.4f}  SoC={soc*100:5.1f}%")

                # Perturbation step
                if now >= t_next_perturb:
                    v_lo, i_lo, v_hi, i_hi = perturb_step(
                        load, base_A=base_A, low_A=low_A, dwell_s=PHASE2.perturb_dwell_s,
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
                          f"dI={di:.3f} → dV/dI={dvdi*1000:.2f} mΩ")
                    t_next_perturb = time.monotonic() + PHASE2.perturb_period_s
                    # don't sleep — already burned ~2*dwell_s
                else:
                    time.sleep(SAMPLE_DT)

        except KeyboardInterrupt:
            print("\n[phase2] interrupted by user")
        except SafetyAbort as e:
            print(f"\n[phase2] SAFETY ABORT: {e}")
        finally:
            load.input_off()
            logger.close()

    print(f"[phase2] done. CSV: {logger.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
