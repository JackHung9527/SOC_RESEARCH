#!/usr/bin/env python3
"""One round of rate-capability characterisation, all in one shot.

A "round" is four (charge, rest, discharge, rest) blocks. The charge is
always at the profile's standard rate (0.5C); the discharge sweeps the
configured C-rates in order. Each completed charge or discharge appends a
row to data/cycle_log.csv with cycle counter, round id, retention %, and
cumulative Ah throughput.

Schedule (one round, default ~16-18 h for a 2000 mAh NMC cell):

    step 1   charge 0.5C → cutoff
    step 2   rest 30 min
    step 3   discharge 0.5C → cutoff      ← baseline V(SoC) @ 0.5C
    step 4   rest 30 min
    step 5   charge 0.5C → cutoff
    step 6   rest 30 min
    step 7   discharge 1.0C → cutoff
    step 8   rest 30 min
    step 9   charge 0.5C → cutoff
    step 10  rest 30 min
    step 11  discharge 1.5C → cutoff
    step 12  rest 30 min
    step 13  charge 0.5C → cutoff
    step 14  rest 30 min
    step 15  discharge 2.0C → cutoff
    step 16  rest 30 min

Run from the project root:

    python3 TEST/round_runner.py

Add --dry-run to print the plan without driving the bench.

Resumes across runs by reading data/cycle_log.csv — the next invocation
will pick up the next round_id automatically.
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from TEST.config import BAUD, PHASE2, PORT_LOAD, PORT_PSU, SAFETY, require_battery
from TEST.core.bench import BenchInterlock, BenchInterlockError
from TEST.core.coulomb import CoulombCounter
from TEST.core.cycle_log import CycleLog
from TEST.core.logger import CsvLogger
from TEST.core.safety import SafetyAbort, SafetyGuard
from TEST.drivers.it6302 import IT6302
from TEST.drivers.it8512 import IT8512
from TEST.profiles import print_summary


DATA_DIR = Path(__file__).resolve().parent / "data"
CYCLE_LOG_PATH = DATA_DIR / "cycle_log.csv"

# Discharge C-rates swept in one round, in execution order.
DISCHARGE_RATES_C = [0.5, 1.0, 1.5, 2.0]

# Charge is fixed at the profile's standard rate. We do not vary charge
# C-rate across the round — high-rate charging would stress the cell and
# corrupt the SoH baseline that the round is supposed to measure.
CHARGE_RATE_C = 0.5

REST_S = 30 * 60                # rest between every charge↔discharge transition
SAMPLE_DT = SAFETY.sample_period_s


# ───────────────────────── plan building ──────────────────────────

@dataclass
class Step:
    kind: str           # "charge" | "discharge" | "rest"
    c_rate: float       # 0 for rest
    duration_s: float   # only used for rest


def build_round_plan() -> list[Step]:
    plan: list[Step] = []
    for d_rate in DISCHARGE_RATES_C:
        plan.append(Step("charge", CHARGE_RATE_C, 0.0))
        plan.append(Step("rest", 0.0, REST_S))
        plan.append(Step("discharge", d_rate, 0.0))
        plan.append(Step("rest", 0.0, REST_S))
    return plan


def print_plan(plan: list[Step], battery, round_id: int) -> None:
    print()
    print("=" * 64)
    print(f"Round {round_id} plan — battery: {battery.name}")
    print("=" * 64)
    c1_A = battery.q_rated_mAh / 1000.0
    for i, s in enumerate(plan, 1):
        if s.kind == "rest":
            print(f"  step {i:2d}  rest        {s.duration_s/60:.0f} min")
        else:
            i_A = s.c_rate * c1_A
            est_h = (1.0 / s.c_rate) if s.kind == "discharge" else 2.3
            print(f"  step {i:2d}  {s.kind:9s} {s.c_rate:.1f}C  "
                  f"({i_A:.3f} A)   ~{est_h:.1f} h")
    print()


# ───────────────────────── step executors ─────────────────────────

def _live_print(t: float, v: float, i: float, soc: float, tag: str,
                interval_s: int = 30) -> None:
    """One-line status print at 30 s intervals."""
    if int(t) % interval_s == 0:
        print(f"    t={t:7.1f}s  V={v:.4f}  I={i:+.4f}  "
              f"SoC={soc * 100:5.1f}%   [{tag}]")


def run_charge_step(
    psu: IT6302, load: IT8512, bench: BenchInterlock,
    battery, c_rate: float, guard: SafetyGuard, cycle_id: int, round_id: int,
) -> tuple[float, float, float, Optional[Path], str]:
    """CC-CV charge to termination. Returns (v_start, v_end, ah_in, csv_path, note)."""
    c1_A = battery.q_rated_mAh / 1000.0
    i_cc = c_rate * c1_A
    v_cv = battery.v_charge_cutoff
    i_term = battery.i_charge_term

    logger = CsvLogger(
        DATA_DIR, tag=f"round{round_id:03d}_cyc{cycle_id:03d}_charge_{c_rate:.1f}C"
    )
    print(f"  [charge {c_rate:.1f}C]  V_cv={v_cv:.3f} V  "
          f"I_cc={i_cc:.3f} A  I_term={i_term:.3f} A  → {logger.path.name}")

    psu.select(1)
    # IT6302's APPL command does not reliably update CURR on sequential
    # writes — the channel may keep the previous CURR limit (seen as a
    # 1C runaway in the first attempt). Write V and I separately and
    # verify CURR by readback before enabling the output.
    psu.set_voltage(v_cv)
    psu.set_current(i_cc)
    time.sleep(0.3)
    tol = max(0.005, 0.05 * i_cc)
    rb_i = psu.s.query_float("CURR?")
    if abs(rb_i - i_cc) > tol:
        print(f"    CURR readback {rb_i:.4f} A != target {i_cc:.4f} A — retry")
        psu.set_current(i_cc)
        time.sleep(0.3)
        rb_i = psu.s.query_float("CURR?")
        if abs(rb_i - i_cc) > tol:
            raise RuntimeError(
                f"PSU CURR refuses to set: target {i_cc:.4f} A, "
                f"readback {rb_i:.4f} A — aborting charge step"
            )
    rb_v = psu.s.query_float("VOLT?")
    print(f"    setpoint readback: V={rb_v:.4f} V  I={rb_i:.4f} A")
    bench.start_charge(ch=1)

    t0 = time.monotonic()
    coul = CoulombCounter(q_rated_mAh=battery.q_rated_mAh, soc_init=0.0)
    t_last = t0
    v_start: Optional[float] = None
    v_last = 0.0
    note = "term"
    try:
        while True:
            now = time.monotonic()
            t = now - t0
            v = psu.measure_voltage()
            i = psu.measure_current()
            if v_start is None:
                v_start = v

            dt = now - t_last
            t_last = now
            # Charging: sign convention "discharge = +I", so I_psu is +I leaving
            # the supply = -I from cell's perspective. CoulombCounter uses
            # discharge-positive; pass -i to make ah_used go *negative*, which
            # we then negate at the end to get ah_in.
            coul.update(-i, dt)
            guard.check(v, i)

            stage = "CC" if i >= i_cc * 0.95 else "CV"
            logger.log(t, "charge", v, i, soc_cc=0.0, note=stage)
            _live_print(t, v, i, 0.0, stage)

            v_last = v
            if v >= v_cv - 0.02 and i <= i_term:
                logger.log(t, "charge", v, i, soc_cc=0.0, note="term")
                break

            time.sleep(SAMPLE_DT)
    finally:
        bench.stop_charge()
        logger.close()

    ah_in = -coul.ah_used   # negate: charge moved INTO cell
    return v_start or v_last, v_last, ah_in, logger.path, note


def run_discharge_step(
    load: IT8512, bench: BenchInterlock,
    battery, c_rate: float, guard: SafetyGuard, cycle_id: int, round_id: int,
) -> tuple[float, float, float, Optional[Path], str]:
    """CC discharge to cutoff with periodic dV/dI perturbation.

    Every PHASE2.perturb_period_s the load briefly drops from the base
    C-rate to PHASE2.perturb_low_C (0.2C by default), dwells, then steps
    back. ΔV/ΔI from those two settled samples is the dynamic-impedance
    estimate at that SoC. Bigger base C-rate → bigger ΔI → cleaner dV/dI.

    Returns (v_start, v_end, ah_out, csv_path, note).
    """
    c1_A = battery.q_rated_mAh / 1000.0
    i_cc = c_rate * c1_A
    i_low = PHASE2.perturb_low_C * c1_A
    dwell = PHASE2.perturb_dwell_s
    period = PHASE2.perturb_period_s
    v_cutoff = battery.v_discharge_cutoff

    logger = CsvLogger(
        DATA_DIR, tag=f"round{round_id:03d}_cyc{cycle_id:03d}_discharge_{c_rate:.1f}C"
    )
    print(f"  [discharge {c_rate:.1f}C]  I_cc={i_cc:.3f} A  "
          f"V_cutoff={v_cutoff:.3f} V  → {logger.path.name}")
    print(f"    perturb: every {period}s step to {i_low:.3f} A "
          f"for {dwell:.1f}s, ΔI={i_cc-i_low:+.3f} A")

    load.set_mode("CC")
    load.set_cc(i_cc)
    load.set_voltage_off_threshold(v_cutoff)
    load.set_current_protection(SAFETY.i_hard_high)

    bench.start_discharge()
    time.sleep(0.5)

    t0 = time.monotonic()
    coul = CoulombCounter(q_rated_mAh=battery.q_rated_mAh, soc_init=1.0)
    t_last = t0
    t_next_perturb = t0 + period
    v_start: Optional[float] = None
    v_last = 0.0
    note = "cutoff"
    try:
        while True:
            now = time.monotonic()
            t = now - t0
            v = load.measure_voltage()
            i = load.measure_current()
            if v_start is None:
                v_start = v

            dt = now - t_last
            t_last = now
            soc = coul.update(i, dt)

            # Cutoff check first — let it win over the absolute guard at
            # V == v_cutoff exactly.
            if v <= v_cutoff:
                logger.log(t, "discharge", v, i, soc, note="cutoff")
                v_last = v
                break

            guard.check(v, i)
            logger.log(t, "discharge", v, i, soc)
            _live_print(t, v, i, soc, f"{c_rate:.1f}C")
            v_last = v

            if now >= t_next_perturb:
                # ── step DOWN to i_low ──
                load.set_cc(i_low)
                t_lo_start = time.monotonic()
                time.sleep(dwell)
                v_lo = load.measure_voltage()
                i_lo_meas = load.measure_current()
                t_lo_end = time.monotonic()
                # account coulomb for the low dwell (treat i_lo as constant
                # over the dwell — load slew is < 100 ms, error < 0.5%)
                coul.update(i_lo_meas, t_lo_end - t_lo_start)

                # ── step back UP to base i_cc ──
                load.set_cc(i_cc)
                t_hi_start = time.monotonic()
                time.sleep(dwell)
                v_hi = load.measure_voltage()
                i_hi_meas = load.measure_current()
                t_hi_end = time.monotonic()
                coul.update(i_hi_meas, t_hi_end - t_hi_start)

                di = i_hi_meas - i_lo_meas
                dvdi = (v_hi - v_lo) / di if abs(di) > 1e-6 else float("nan")
                soc = coul.soc

                logger.log(t_lo_end - t0, "perturb_low", v_lo, i_lo_meas, soc,
                           note=f"step_to_{i_low:.3f}A")
                logger.log(t_hi_end - t0, "perturb_high", v_hi, i_hi_meas, soc,
                           dvdi=dvdi, note=f"step_to_{i_cc:.3f}A")
                print(f"    [perturb] V_lo={v_lo:.4f} V_hi={v_hi:.4f}  "
                      f"ΔI={di:+.3f} A → dV/dI={dvdi*1000:+.2f} mΩ  "
                      f"(SoC {soc*100:.1f}%)")

                # If we tipped past cutoff during the high-current sample,
                # exit cleanly — don't keep stressing the cell.
                if v_hi <= v_cutoff:
                    note = "cutoff_during_perturb"
                    v_last = v_hi
                    break

                guard.check(v_lo, i_lo_meas)
                guard.check(v_hi, i_hi_meas)

                # reset main-loop pacing so next dt doesn't double-count
                t_last = time.monotonic()
                t_next_perturb = t_last + period
            else:
                time.sleep(SAMPLE_DT)
    finally:
        bench.stop_discharge()
        logger.close()

    return v_start or v_last, v_last, coul.ah_used, logger.path, note


def run_rest_step(duration_s: float) -> None:
    """Sleep through the rest period; print countdown every 5 min."""
    print(f"  [rest]  {duration_s/60:.0f} min  (PSU/Load both OFF — cell relaxing)")
    t0 = time.monotonic()
    next_print = t0 + 300
    while True:
        now = time.monotonic()
        elapsed = now - t0
        if elapsed >= duration_s:
            return
        if now >= next_print:
            remain = duration_s - elapsed
            print(f"    rest: {elapsed/60:.0f}/{duration_s/60:.0f} min  "
                  f"({remain/60:.0f} min left)")
            next_print = now + 300
        time.sleep(min(30.0, duration_s - elapsed))


# ───────────────────────── orchestrator ───────────────────────────

def run_round(dry_run: bool = False) -> int:
    battery = require_battery()
    print_summary(battery)

    plan = build_round_plan()
    cycle_log = CycleLog(CYCLE_LOG_PATH)
    state = cycle_log.state
    round_id = state.next_round_id
    cycle_id = state.next_cycle_id   # this advances on each discharge completion

    print_plan(plan, battery, round_id)
    print(f"[round_runner] cycle_log → {cycle_log.path}")
    print(f"[round_runner] starting at cycle_id={cycle_id}, "
          f"cumulative_throughput so far = {state.cumulative_ah:.3f} Ah")

    if dry_run:
        print("\n--dry-run: not driving the bench. Exit.")
        return 0

    guard = SafetyGuard.from_profile(battery, i_hard_high=SAFETY.i_hard_high)

    with IT6302.open(PORT_PSU, BAUD) as psu, IT8512.open(PORT_LOAD, BAUD) as load:
        print(f"[round_runner] PSU: {psu.idn()}")
        print(f"[round_runner] LOAD: {load.idn()}")

        bench = BenchInterlock(psu=psu, load=load, deadtime_s=SAFETY.deadtime_s)

        try:
            bench.assert_idle()

            for i, step in enumerate(plan, 1):
                print()
                print("-" * 64)
                print(f"Round {round_id}  step {i}/{len(plan)}  "
                      f"({step.kind} {step.c_rate}C)")
                print("-" * 64)

                t_iso = cycle_log.utc_now_iso()
                t_step0 = time.monotonic()

                if step.kind == "charge":
                    v0, v1, ah, csv_path, note = run_charge_step(
                        psu, load, bench, battery, step.c_rate, guard,
                        cycle_id=cycle_id, round_id=round_id,
                    )
                    cycle_log.append_step(
                        cycle_id=cycle_id, round_id=round_id,
                        direction="charge", c_rate=step.c_rate,
                        c_rate_A=step.c_rate * battery.q_rated_mAh / 1000.0,
                        v_start=v0, v_end=v1, ah=ah,
                        q_rated_mAh=battery.q_rated_mAh,
                        t_start_iso=t_iso,
                        duration_s=time.monotonic() - t_step0,
                        csv_path=csv_path, note=note,
                    )

                elif step.kind == "discharge":
                    v0, v1, ah, csv_path, note = run_discharge_step(
                        load, bench, battery, step.c_rate, guard,
                        cycle_id=cycle_id, round_id=round_id,
                    )
                    cycle_log.append_step(
                        cycle_id=cycle_id, round_id=round_id,
                        direction="discharge", c_rate=step.c_rate,
                        c_rate_A=step.c_rate * battery.q_rated_mAh / 1000.0,
                        v_start=v0, v_end=v1, ah=ah,
                        q_rated_mAh=battery.q_rated_mAh,
                        t_start_iso=t_iso,
                        duration_s=time.monotonic() - t_step0,
                        csv_path=csv_path, note=note,
                    )
                    cycle_id += 1   # advance for the next charge/discharge pair

                else:   # rest
                    run_rest_step(step.duration_s)

            print()
            print("=" * 64)
            print(f"Round {round_id} complete.")
            print(f"  cycles run this round: {len(DISCHARGE_RATES_C)}")
            print(f"  cycle_id advanced to: {cycle_id - 1}")
            print(f"  cumulative throughput: "
                  f"{cycle_log.state.cumulative_ah:.3f} Ah")
            print("=" * 64)

        except KeyboardInterrupt:
            print("\n\n[round_runner] !!! interrupted by user — emergency stop")
        except SafetyAbort as e:
            print(f"\n\n[round_runner] !!! SAFETY ABORT: {e}")
        except BenchInterlockError as e:
            print(f"\n\n[round_runner] !!! BENCH INTERLOCK: {e}")
        except Exception as e:
            print(f"\n\n[round_runner] !!! unexpected: {type(e).__name__}: {e}")
            raise
        finally:
            try:
                bench.emergency_stop()
            except Exception as e:
                print(f"[round_runner] emergency_stop secondary failure: {e}")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan without driving the bench")
    args = ap.parse_args()
    return run_round(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
