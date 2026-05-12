#!/usr/bin/env python3
"""One round of rate-capability characterisation — v1.

v1 vs v0 (TEST/round_runner.py):
  * Adds a FINAL storage-charge step that returns the cell to ~3.9 V at
    0.5C after the last discharge+rest. Reason: leaving a freshly
    discharged Li-ion cell sitting at 2.5–3.0 V between rounds is bad
    for calendar aging; 3.9 V (~60% SoC) is the standard storage point
    for NMC chemistries.
  * Shares the same data/cycle_log.csv so round_id continues to advance
    seamlessly across v0 → v1 invocations.

A "round" is four (charge, rest, discharge, rest) blocks followed by a
storage charge. The charge is always at the profile's standard rate
(0.5C); the discharge sweeps the configured C-rates in order. Each
completed charge or discharge appends a row to data/cycle_log.csv with
cycle counter, round id, retention %, and cumulative Ah throughput.

Schedule (one round, default ~16-18 h for a 1665 mAh NMC cell):

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
    step 17  storage_charge 0.5C → 3.9 V  ← NEW in v1

Run from the project root:

    python3 TEST/round_runner_v1.py

Add --dry-run to print the plan without driving the bench.

Resumes across runs by reading data/cycle_log.csv — the next invocation
will pick up the next round_id automatically (works regardless of which
runner — v0 or v1 — wrote the previous round).
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
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

# ── Storage charge (v1 addition) ───────────────────────────────────────
# Park the cell at ~3.9 V (≈60% SoC for NMC) between rounds. Same rate
# as the standard round charge so we don't introduce a new stress
# profile. i_term is tighter than the normal CC-CV: at the storage
# voltage we want the cell's *open-circuit* V to land at 3.9 V after
# rest, which means letting CV taper further so the IR-drop component
# of terminal V approaches zero.
STORAGE_VOLTAGE_V = 3.9
STORAGE_CHARGE_RATE_C = 0.5
STORAGE_I_TERM_C = 0.05         # 1/20 C — looser would leave OCV well below 3.9 V


# ───────────────────────── plan building ──────────────────────────

@dataclass
class Step:
    kind: str                   # "charge" | "discharge" | "rest" | "storage_charge"
    c_rate: float               # 0 for rest
    duration_s: float           # only used for rest
    v_target: Optional[float] = None        # only used for storage_charge
    i_term_c_override: Optional[float] = None  # tighter taper for storage


def build_round_plan() -> list[Step]:
    plan: list[Step] = []
    for d_rate in DISCHARGE_RATES_C:
        plan.append(Step("charge", CHARGE_RATE_C, 0.0))
        plan.append(Step("rest", 0.0, REST_S))
        plan.append(Step("discharge", d_rate, 0.0))
        plan.append(Step("rest", 0.0, REST_S))
    # v1: storage charge to ~3.9 V at the end of the round.
    plan.append(Step(
        "storage_charge", STORAGE_CHARGE_RATE_C, 0.0,
        v_target=STORAGE_VOLTAGE_V,
        i_term_c_override=STORAGE_I_TERM_C,
    ))
    return plan


def estimate_step_hours(step: Step) -> float:
    """Rough wall-clock estimate per step.

    Calibrated against the v0 plan executing on a 1665 mAh NMC cell:
      * Full CC-CV charge at 0.5C from V_cutoff up to ~0.1C taper:
        ≈ 1/c_rate (CC, empty → V_cv) + 0.3 h (CV taper).
      * Full discharge at C-rate: ≈ 1/c_rate.
      * Storage charge from low SoC up to ~60% SoC with tighter (1/20C)
        taper: ≈ 0.55/c_rate (CC portion) + 0.5 h (longer CV).
      * Rest: exactly its duration_s.

    Estimates are intentionally conservative — they assume the cell
    actually charges fully, ignoring the already-full bypass that can
    shrink a charge step to seconds. The displayed ETA is therefore an
    upper bound; real round may finish 1-2 h earlier if any charge
    bypasses.
    """
    if step.kind == "rest":
        return step.duration_s / 3600.0
    if step.kind == "discharge":
        return 1.0 / step.c_rate
    if step.kind == "charge":
        return 1.0 / step.c_rate + 0.3
    if step.kind == "storage_charge":
        return 0.55 / step.c_rate + 0.5
    return 0.0


def print_plan(plan: list[Step], battery, round_id: int) -> None:
    print()
    print("=" * 64)
    print(f"Round {round_id} plan (v1) — battery: {battery.name}")
    print("=" * 64)
    c1_A = battery.q_rated_mAh / 1000.0
    for i, s in enumerate(plan, 1):
        if s.kind == "rest":
            print(f"  step {i:2d}  rest         {s.duration_s/60:.0f} min")
        elif s.kind == "storage_charge":
            i_A = s.c_rate * c1_A
            print(f"  step {i:2d}  storage_chg {s.c_rate:.1f}C  "
                  f"({i_A:.3f} A)  → {s.v_target:.2f} V")
        else:
            i_A = s.c_rate * c1_A
            est_h = (1.0 / s.c_rate) if s.kind == "discharge" else 2.3
            print(f"  step {i:2d}  {s.kind:9s}  {s.c_rate:.1f}C  "
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
    v_cv_override: Optional[float] = None,
    i_term_c_override: Optional[float] = None,
    tag_suffix: str = "charge",
) -> tuple[float, float, float, Optional[Path], str]:
    """CC-CV charge to termination. Returns (v_start, v_end, ah_in, csv_path, note).

    When ``v_cv_override`` is given, charges to that voltage instead of
    ``battery.v_charge_cutoff`` — used by the storage_charge step to park
    the cell at ~3.9 V. ``i_term_c_override`` lets storage tighten the
    CV taper (default 0.1 C is too loose for an OCV-accurate park).
    """
    c1_A = battery.q_rated_mAh / 1000.0
    i_cc = c_rate * c1_A
    v_cv = v_cv_override if v_cv_override is not None else battery.v_charge_cutoff
    # ─── Termination tunables ──────────────────────────────────────────
    # See round_runner.run_charge_step for the full rationale. Knobs are
    # duplicated here (not imported) so this file can be edited without
    # touching the v0 runner that may still be live.
    i_term_c = i_term_c_override if i_term_c_override is not None else 0.1
    v_term_margin = 0.10            # 100 mV — must be within this of V_cv
    i_term = i_term_c * c1_A        # i_term_c × C (default 0.1, storage uses 0.05)
    t_term_min = 30.0               # min elapsed before NORMAL TERM may fire
    term_hold_s = 3.0               # both conditions must hold this long
    full_v_margin = 0.030           # 30 mV bypass V threshold
    full_i_max = 0.050              # 50 mA bypass I threshold
    full_window_s = 5.0             # bypass observation window
    # ───────────────────────────────────────────────────────────────────
    logger = CsvLogger(
        DATA_DIR, tag=f"round{round_id:03d}_cyc{cycle_id:03d}_{tag_suffix}_{c_rate:.1f}C"
    )
    print(f"  [{tag_suffix} {c_rate:.1f}C]  V_cv={v_cv:.3f} V  "
          f"I_cc={i_cc:.3f} A  I_term={i_term:.3f} A ({i_term_c:.2f}C)  "
          f"→ {logger.path.name}")
    print(f"    term: V≥{v_cv-v_term_margin:.3f} & I≤{i_term:.3f} "
          f"held {term_hold_s:.0f}s after t≥{t_term_min:.0f}s")

    psu.select(1)
    # IT6302's APPL command does not reliably update CURR on sequential
    # writes — the channel may keep the previous CURR limit. Write V and
    # I separately and verify CURR by readback before enabling output.
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
    cc_entered = False
    full_check_until = t0 + full_window_s
    full_seen_break = False
    t_in_band: Optional[float] = None
    print(f"    [bypass-check] V≥{v_cv-full_v_margin:.3f} & I<{full_i_max:.3f} "
          f"for {full_window_s:.0f}s → skip step")
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
            coul.update(-i, dt)
            guard.check(v, i)

            if i >= i_cc * 0.5:
                cc_entered = True
            in_bypass_window = now < full_check_until
            if in_bypass_window and (v < v_cv - full_v_margin or i >= full_i_max):
                full_seen_break = True

            stage = "CC" if i >= i_cc * 0.95 else "CV"
            logger.log(t, tag_suffix, v, i, soc_cc=0.0, note=stage)
            if in_bypass_window:
                print(f"    t={t:5.1f}s  V={v:.4f}  I={i:+.4f}  "
                      f"[{stage}] bypass-watch (break={full_seen_break})")
            else:
                _live_print(t, v, i, 0.0, stage)

            v_last = v

            if now >= full_check_until and not full_seen_break and not cc_entered:
                logger.log(t, tag_suffix, v, i, soc_cc=0.0, note="already_full")
                print(f"    → ALREADY FULL (V={v:.4f}, I={i:+.4f}) — skipping step")
                note = "already_full"
                break

            v_ok = v >= v_cv - v_term_margin
            i_ok = i <= i_term
            if v_ok and i_ok:
                if t_in_band is None:
                    t_in_band = now
                hold = now - t_in_band
                if t >= t_term_min and hold >= term_hold_s:
                    logger.log(t, tag_suffix, v, i, soc_cc=0.0,
                               note=f"term(hold={hold:.1f}s)")
                    print(f"    → TERM (V={v:.4f}≥{v_cv-v_term_margin:.3f}, "
                          f"I={i:.4f}≤{i_term:.3f}, held {hold:.1f}s)")
                    break
            else:
                if t_in_band is not None:
                    t_in_band = None

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
    """CC discharge to cutoff with periodic dV/dI perturbation."""
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

            if v <= v_cutoff:
                logger.log(t, "discharge", v, i, soc, note="cutoff")
                v_last = v
                break

            guard.check(v, i)
            logger.log(t, "discharge", v, i, soc)
            _live_print(t, v, i, soc, f"{c_rate:.1f}C")
            v_last = v

            if now >= t_next_perturb:
                load.set_cc(i_low)
                t_lo_start = time.monotonic()
                time.sleep(dwell)
                v_lo = load.measure_voltage()
                i_lo_meas = load.measure_current()
                t_lo_end = time.monotonic()
                coul.update(i_lo_meas, t_lo_end - t_lo_start)

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

                if v_hi <= v_cutoff:
                    note = "cutoff_during_perturb"
                    v_last = v_hi
                    break

                guard.check(v_lo, i_lo_meas)
                guard.check(v_hi, i_hi_meas)

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
    cycle_id = state.next_cycle_id

    print_plan(plan, battery, round_id)

    # ── ETA estimate ───────────────────────────────────────────────────
    total_h = sum(estimate_step_hours(s) for s in plan)
    now = datetime.now()
    eta = now + timedelta(hours=total_h)
    # Per-kind breakdown for the operator
    breakdown: dict[str, float] = {}
    for s in plan:
        breakdown[s.kind] = breakdown.get(s.kind, 0.0) + estimate_step_hours(s)
    print(f"[round_runner_v1] estimated duration: {total_h:.1f} h")
    for kind, hours in breakdown.items():
        n = sum(1 for s in plan if s.kind == kind)
        print(f"    • {kind:15s} ×{n}  ≈ {hours:.1f} h")
    print(f"[round_runner_v1] start: {now.strftime('%Y-%m-%d %H:%M')}  "
          f"→ ETA: {eta.strftime('%Y-%m-%d %H:%M')} "
          f"({eta.strftime('%a')})")
    print(f"    (upper bound — already-full bypass on any charge step "
          f"could shave 1–2 h)")
    print()

    print(f"[round_runner_v1] cycle_log → {cycle_log.path}")
    print(f"[round_runner_v1] starting at cycle_id={cycle_id}, "
          f"cumulative_throughput so far = {state.cumulative_ah:.3f} Ah")

    if dry_run:
        print("\n--dry-run: not driving the bench. Exit.")
        return 0

    guard = SafetyGuard.from_profile(battery, i_hard_high=SAFETY.i_hard_high)

    with IT6302.open(PORT_PSU, BAUD) as psu, IT8512.open(PORT_LOAD, BAUD) as load:
        print(f"[round_runner_v1] PSU: {psu.idn()}")
        print(f"[round_runner_v1] LOAD: {load.idn()}")

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
                    cycle_id += 1   # advance for next charge/discharge pair

                elif step.kind == "storage_charge":
                    v0, v1, ah, csv_path, note = run_charge_step(
                        psu, load, bench, battery, step.c_rate, guard,
                        cycle_id=cycle_id, round_id=round_id,
                        v_cv_override=step.v_target,
                        i_term_c_override=step.i_term_c_override,
                        tag_suffix="storage_charge",
                    )
                    cycle_log.append_step(
                        cycle_id=cycle_id, round_id=round_id,
                        direction="storage_charge", c_rate=step.c_rate,
                        c_rate_A=step.c_rate * battery.q_rated_mAh / 1000.0,
                        v_start=v0, v_end=v1, ah=ah,
                        q_rated_mAh=battery.q_rated_mAh,
                        t_start_iso=t_iso,
                        duration_s=time.monotonic() - t_step0,
                        csv_path=csv_path,
                        note=f"{note} → park@{step.v_target:.2f}V",
                    )

                else:   # rest
                    run_rest_step(step.duration_s)

            print()
            print("=" * 64)
            print(f"Round {round_id} complete (v1, ending at storage charge).")
            print(f"  cycles run this round: {len(DISCHARGE_RATES_C)}")
            print(f"  cycle_id advanced to: {cycle_id - 1}")
            print(f"  cumulative throughput: "
                  f"{cycle_log.state.cumulative_ah:.3f} Ah")
            print(f"  cell parked at ~{STORAGE_VOLTAGE_V:.2f} V — safe for storage")
            print("=" * 64)

        except KeyboardInterrupt:
            print("\n\n[round_runner_v1] !!! interrupted by user — emergency stop")
        except SafetyAbort as e:
            print(f"\n\n[round_runner_v1] !!! SAFETY ABORT: {e}")
        except BenchInterlockError as e:
            print(f"\n\n[round_runner_v1] !!! BENCH INTERLOCK: {e}")
        except Exception as e:
            print(f"\n\n[round_runner_v1] !!! unexpected: {type(e).__name__}: {e}")
            raise
        finally:
            try:
                bench.emergency_stop()
            except Exception as e:
                print(f"[round_runner_v1] emergency_stop secondary failure: {e}")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan without driving the bench")
    args = ap.parse_args()
    return run_round(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
