#!/usr/bin/env python3
"""GITT-based pseudo-OCV table builder.

Builds a pseudo-open-circuit-voltage (pseudo-OCV) table by running a GITT
(Galvanostatic Intermittent Titration Technique) protocol in both
directions, separated by 1-hour rests at every 5% SoC step. The bench
auto-charges to full first, runs the discharge sweep, then runs the
charge sweep — so the cell starts and ends fully charged and is safe to
chain a round_runner_v1 invocation right after.

Pseudo-OCV at each SoC bin = mean of discharge-direction V_eq and
charge-direction V_eq, which cancels the hysteresis loop.

Schedule (≈46 h for a 2000 mAh NMC cell at 0.5C):

    PHASE 1   pre-charge CC-CV → V_cv                    (~2.5 h)
    PHASE 2   discharge GITT, 100% → ~0%                 (≈22 h)
                ×20 of: discharge q_rated × 5% at 0.5C, rest 60 min
    PHASE 3   charge GITT,    ~0% → ~100%                (≈22 h)
                ×20 of: charge q_rated × 5% at 0.5C,    rest 60 min

Outputs (timestamp suffix, all under TEST/data/):
    gitt_trace_*.csv      — full sample-rate time-series, all modes
    gitt_summary_*.csv    — one row per GITT step (incl. v_rest_5/15/30/45/60min)
    ocv_table_*.csv       — final SoC, V_disch, V_chg, V_pseudo

Usage (from project root):

    python3 TEST/gitt_ocv_runner.py
    python3 TEST/gitt_ocv_runner.py --dry-run
    python3 TEST/gitt_ocv_runner.py --step-pct 5 --rest-min 60 --c-rate 0.5

A battery profile MUST be active (run TEST/select_battery.py first).
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean
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


DATA_DIR = Path(__file__).resolve().parent / "data"

# --- defaults (overridable via CLI) ---------------------------------
DEFAULT_STEP_PCT      = 5.0      # SoC increment per GITT step
DEFAULT_REST_MIN      = 60.0     # rest after each step
DEFAULT_C_RATE        = 0.5      # charge & discharge rate (CC)

# --- analysis windows -----------------------------------------------
V_EQ_AVG_WINDOW_S     = 30.0     # average last N seconds of rest as V_eq
DV_DT_WINDOW_S        = 5 * 60   # compute dV/dt over last 5 min of rest

# --- sampling rates -------------------------------------------------
REST_SAMPLE_DT_S      = 5.0      # sample voltage every 5 s during rest
ACTIVE_SAMPLE_DT_S    = 1.0      # sample every 1 s during discharge/charge

# --- pre-charge tunables (mirrors round_runner CC-CV termination) ---
PRECHARGE_I_TERM_C    = 0.1      # 0.1C taper threshold
PRECHARGE_V_TERM_MARGIN = 0.10   # within 100 mV of V_cv
PRECHARGE_TERM_HOLD_S = 3.0      # both conditions held this long
PRECHARGE_T_MIN_S     = 30.0     # min elapsed before TERM may fire

# --- per-step safety guard ------------------------------------------
# A 5%-SoC step at 0.5C takes ~6 min on a 2 Ah cell. Allow generous
# slack but cap absolute runaway.
STEP_MAX_DURATION_S   = 30 * 60

# In charge GITT we want to stay strictly in CC, so we stop just below
# V_cv rather than letting CV taper kick in (CV taper makes the
# loaded-end voltage uninformative for the OCV table).
CHARGE_V_STOP_MARGIN  = 0.005    # stop charge step when V ≥ V_cv − 5 mV


# ───────────────────────── data classes ───────────────────────────

@dataclass
class StepResult:
    step_idx: int
    direction: str              # "discharge" | "charge" | "precharge_rest"
    soc_before: float           # 0..1
    soc_after: float            # 0..1
    q_target_mAh: float
    q_actual_mAh: float
    duration_s: float
    v_start_loaded: float
    v_end_loaded: float
    v_rest_curve: list[tuple[float, float]] = field(default_factory=list)
    v_eq: float = 0.0
    dv_dt_last_window_mvpermin: float = 0.0
    note: str = ""


# ───────────────────────── helpers ────────────────────────────────

def _print(msg: str) -> None:
    print(msg, flush=True)


def _interp_v_at(curve: list[tuple[float, float]], t_target_s: float) -> Optional[float]:
    """Return V from the sample whose t is closest to t_target_s, or None."""
    if not curve:
        return None
    best = min(curve, key=lambda p: abs(p[0] - t_target_s))
    # Reject if no sample within 10s of the requested time.
    if abs(best[0] - t_target_s) > 10.0:
        return None
    return best[1]


def _read_cell_voltage(psu, load) -> float:
    """Read open-cell voltage during rest. PSU MEAS:VOLT? is preferred
    because IT6302 returns terminal V even with output OFF; fall back to
    load voltmeter if PSU read raises."""
    try:
        return psu.measure_voltage()
    except Exception:
        return load.measure_voltage()


# ───────────────────────── pre-charge ─────────────────────────────

def precharge_to_full(
    *, psu, load, bench, battery, guard, c_rate: float,
    trace: CsvLogger, run_t0: float,
) -> tuple[float, float, str]:
    """CC-CV charge from any starting SoC up to V_cv with 0.1C taper.

    Returns (v_start, v_end, note). Standalone — no cycle_log writes.
    """
    c1_A = battery.q_rated_mAh / 1000.0
    i_cc = c_rate * c1_A
    v_cv = battery.v_charge_cutoff
    i_term = PRECHARGE_I_TERM_C * c1_A

    _print(
        f"  [precharge] CC-CV  I_cc={i_cc:.3f} A  V_cv={v_cv:.3f} V  "
        f"I_term={i_term:.3f} A ({PRECHARGE_I_TERM_C:.2f}C)"
    )

    psu.select(1)
    psu.set_voltage(v_cv)
    psu.set_current(i_cc)
    time.sleep(0.3)
    # Verify CURR setpoint took effect (IT6302 APPL chicanery).
    tol = max(0.005, 0.05 * i_cc)
    rb = psu.s.query_float("CURR?")
    if abs(rb - i_cc) > tol:
        psu.set_current(i_cc)
        time.sleep(0.3)
        rb = psu.s.query_float("CURR?")
        if abs(rb - i_cc) > tol:
            raise RuntimeError(
                f"PSU CURR refuses to set: target {i_cc:.4f} A, "
                f"readback {rb:.4f} A"
            )
    bench.start_charge(ch=1)

    t0 = time.monotonic()
    v_start: Optional[float] = None
    v_last = 0.0
    t_in_band: Optional[float] = None
    note = "term"
    try:
        while True:
            now = time.monotonic()
            t = now - t0
            v = psu.measure_voltage()
            i = psu.measure_current()
            if v_start is None:
                v_start = v
            v_last = v
            guard.check(v, i)
            stage = "precharge_cc" if i >= i_cc * 0.95 else "precharge_cv"
            trace.log(now - run_t0, stage, v, i, soc_cc=0.0)
            if int(t) % 30 == 0:
                _print(
                    f"    t={t:6.1f}s  V={v:.4f}  I={i:+.4f}  [{stage}]"
                )
            v_ok = v >= v_cv - PRECHARGE_V_TERM_MARGIN
            i_ok = i <= i_term
            if v_ok and i_ok:
                if t_in_band is None:
                    t_in_band = now
                hold = now - t_in_band
                if t >= PRECHARGE_T_MIN_S and hold >= PRECHARGE_TERM_HOLD_S:
                    _print(
                        f"    → PRECHARGE TERM (V={v:.4f}≥{v_cv-PRECHARGE_V_TERM_MARGIN:.3f}, "
                        f"I={i:.4f}≤{i_term:.3f}, held {hold:.1f}s)"
                    )
                    break
            else:
                t_in_band = None
            if t >= 6 * 3600:
                note = "timeout"
                _print("    !!! precharge timeout (>6 h) — aborting")
                break
            time.sleep(ACTIVE_SAMPLE_DT_S)
    finally:
        bench.stop_charge()

    return v_start or v_last, v_last, note


# ───────────────────────── rest + V_eq capture ────────────────────

def run_rest_capture(
    *, psu, load, rest_s: float, soc_after: float,
    mode_tag: str, step_label: str,
    trace: CsvLogger, run_t0: float,
) -> tuple[float, float, list[tuple[float, float]]]:
    """Sleep through rest, sample V every REST_SAMPLE_DT_S, return
    (v_eq, dv_dt_mv_per_min, rest_curve).

    rest_curve: list of (t_in_rest_s, V).
    """
    _print(f"    [rest {step_label}] {rest_s/60:.0f} min "
           f"(PSU/Load both OFF — cell relaxing)")
    curve: list[tuple[float, float]] = []
    t_rest0 = time.monotonic()
    next_print = t_rest0 + 300
    while True:
        now = time.monotonic()
        elapsed = now - t_rest0
        if elapsed >= rest_s:
            break
        v = _read_cell_voltage(psu, load)
        curve.append((elapsed, v))
        trace.log(now - run_t0, mode_tag, v, 0.0,
                  soc_cc=soc_after, note=step_label)
        if now >= next_print:
            _print(f"    rest: {elapsed/60:5.1f}/{rest_s/60:.0f} min  "
                   f"V={v:.5f}")
            next_print = now + 300
        time.sleep(REST_SAMPLE_DT_S)

    # V_eq = mean of last V_EQ_AVG_WINDOW_S seconds
    last_window = [v for (t, v) in curve if t >= rest_s - V_EQ_AVG_WINDOW_S]
    v_eq = mean(last_window) if last_window else (
        curve[-1][1] if curve else 0.0
    )
    # dV/dt over last DV_DT_WINDOW_S seconds (mV/min)
    dvdt_w = [(t, v) for (t, v) in curve if t >= rest_s - DV_DT_WINDOW_S]
    if len(dvdt_w) >= 2:
        dv = dvdt_w[-1][1] - dvdt_w[0][1]
        dt = dvdt_w[-1][0] - dvdt_w[0][0]
        dv_dt = (dv / dt) * 60.0 * 1000.0 if dt > 0 else 0.0
    else:
        dv_dt = 0.0

    _print(f"    rest done: V_eq={v_eq:.5f} V  "
           f"|dV/dt|_last5min={abs(dv_dt):.3f} mV/min")
    return v_eq, dv_dt, curve


# ───────────────────────── one GITT step (CC + rest) ──────────────

def run_gitt_step(
    *, direction: str,
    psu, load, bench, battery, guard,
    c_rate: float, q_target_mAh: float, soc_before: float,
    rest_s: float, step_idx: int,
    trace: CsvLogger, run_t0: float,
) -> StepResult:
    """Run one CC step (discharge OR charge) followed by a 1-h rest.

    direction: "discharge" or "charge".
    Stops the CC step when q_actual ≥ q_target_mAh OR safety V-limit hit.
    Records V_eq from the trailing portion of the rest.
    """
    c1_A = battery.q_rated_mAh / 1000.0
    i_cc = c_rate * c1_A
    v_cv = battery.v_charge_cutoff
    v_cut = battery.v_discharge_cutoff
    q_rated = battery.q_rated_mAh

    soc_after_nom = (
        soc_before - q_target_mAh / q_rated
        if direction == "discharge"
        else soc_before + q_target_mAh / q_rated
    )
    _print("")
    _print("-" * 64)
    _print(
        f"  GITT step {step_idx:2d}  {direction:9s}  "
        f"I_cc={i_cc:.3f} A  Q_target={q_target_mAh:.1f} mAh  "
        f"(SoC {soc_before*100:.2f}% → ~{soc_after_nom*100:.2f}%)"
    )

    # ── instrument setup + start ──────────────────────────────────
    if direction == "charge":
        psu.select(1)
        psu.set_voltage(v_cv)
        psu.set_current(i_cc)
        time.sleep(0.3)
        tol = max(0.005, 0.05 * i_cc)
        rb = psu.s.query_float("CURR?")
        if abs(rb - i_cc) > tol:
            psu.set_current(i_cc)
            time.sleep(0.3)
            rb = psu.s.query_float("CURR?")
            if abs(rb - i_cc) > tol:
                raise RuntimeError(
                    f"PSU CURR refuses to set: target {i_cc:.4f} A, "
                    f"readback {rb:.4f} A"
                )
        bench.start_charge(ch=1)
        meas_v = psu.measure_voltage
        meas_i = psu.measure_current
        coul_sign = -1.0     # charge current is negative in coulomb convention
        v_limit = v_cv - CHARGE_V_STOP_MARGIN
        v_limit_hit = lambda vv: vv >= v_limit
        trace_mode = "gitt_charge"
        rest_mode = "gitt_rest_chg"
    elif direction == "discharge":
        load.set_mode("CC")
        load.set_cc(i_cc)
        load.set_voltage_off_threshold(v_cut)
        load.set_current_protection(SAFETY.i_hard_high)
        bench.start_discharge()
        time.sleep(0.3)
        meas_v = load.measure_voltage
        meas_i = load.measure_current
        coul_sign = +1.0
        v_limit = v_cut
        v_limit_hit = lambda vv: vv <= v_limit
        trace_mode = "gitt_discharge"
        rest_mode = "gitt_rest_disch"
    else:
        raise ValueError(f"unknown direction {direction!r}")

    # ── CC loop until q_target or v_limit ─────────────────────────
    # CoulombCounter starts at soc=1 by default; we use ah_used as a
    # delta-Q meter, sign convention discharge-positive.
    coul = CoulombCounter(q_rated_mAh=q_rated, soc_init=1.0)
    t0 = time.monotonic()
    t_last = t0
    v_start_loaded: Optional[float] = None
    v_end_loaded = 0.0
    note = "q_reached"
    try:
        while True:
            now = time.monotonic()
            t = now - t0
            v = meas_v()
            i = meas_i()
            if v_start_loaded is None:
                v_start_loaded = v
            v_end_loaded = v
            dt = now - t_last
            t_last = now
            coul.update(coul_sign * i, dt)
            q_actual_mAh = abs(coul.ah_used) * 1000.0
            guard.check(v, i)
            trace.log(now - run_t0, trace_mode, v, i, soc_cc=0.0,
                      note=f"step{step_idx}")
            if int(t) % 30 == 0:
                _print(
                    f"    t={t:5.1f}s  V={v:.4f}  I={i:+.4f}  "
                    f"q={q_actual_mAh:6.1f}/{q_target_mAh:.1f} mAh  "
                    f"[{direction}]"
                )
            if q_actual_mAh >= q_target_mAh:
                note = "q_reached"
                break
            if v_limit_hit(v):
                note = "v_limited"
                _print(
                    f"    → V-limit hit ({v:.4f} vs {v_limit:.4f}) — "
                    f"stopping step at q={q_actual_mAh:.1f} mAh"
                )
                break
            if t >= STEP_MAX_DURATION_S:
                note = "timeout"
                _print(f"    !!! step timeout (>{STEP_MAX_DURATION_S}s)")
                break
            time.sleep(ACTIVE_SAMPLE_DT_S)
    finally:
        if direction == "charge":
            bench.stop_charge()
        else:
            bench.stop_discharge()

    q_actual_mAh = abs(coul.ah_used) * 1000.0
    delta_soc = q_actual_mAh / q_rated
    if direction == "discharge":
        soc_after = max(0.0, soc_before - delta_soc)
    else:
        soc_after = min(1.0, soc_before + delta_soc)
    step_duration = time.monotonic() - t0

    _print(
        f"    step done: q={q_actual_mAh:.2f} mAh  "
        f"V_loaded_end={v_end_loaded:.4f}  SoC→{soc_after*100:.2f}%  "
        f"note={note}"
    )

    # ── rest + V_eq capture ───────────────────────────────────────
    v_eq, dv_dt, rest_curve = run_rest_capture(
        psu=psu, load=load, rest_s=rest_s, soc_after=soc_after,
        mode_tag=rest_mode, step_label=f"step{step_idx}",
        trace=trace, run_t0=run_t0,
    )

    return StepResult(
        step_idx=step_idx, direction=direction,
        soc_before=soc_before, soc_after=soc_after,
        q_target_mAh=q_target_mAh, q_actual_mAh=q_actual_mAh,
        duration_s=step_duration,
        v_start_loaded=v_start_loaded or v_end_loaded,
        v_end_loaded=v_end_loaded,
        v_rest_curve=rest_curve, v_eq=v_eq,
        dv_dt_last_window_mvpermin=dv_dt,
        note=note,
    )


# ───────────────────────── output writers ────────────────────────

def write_summary_row(w, fp, res: StepResult) -> None:
    def at(t_s: float) -> str:
        v = _interp_v_at(res.v_rest_curve, t_s)
        return f"{v:.5f}" if v is not None else ""
    w.writerow([
        res.step_idx, res.direction,
        f"{res.soc_before*100:.4f}", f"{res.soc_after*100:.4f}",
        f"{res.q_target_mAh:.4f}", f"{res.q_actual_mAh:.4f}",
        f"{res.duration_s:.2f}",
        f"{res.v_start_loaded:.5f}", f"{res.v_end_loaded:.5f}",
        at(5*60), at(15*60), at(30*60), at(45*60), at(60*60),
        f"{res.v_eq:.5f}",
        f"{res.dv_dt_last_window_mvpermin:.4f}",
        res.note,
    ])
    fp.flush()


def build_pseudo_ocv(
    disch: list[StepResult], chg: list[StepResult], step_pct: float,
) -> list[dict]:
    """Bin both directions onto a common SoC grid (step_pct, 2×step_pct, …,
    100-step_pct) and compute pseudo-OCV = mean of available V_eq."""
    bins = [step_pct * k for k in range(1, int(round(100.0 / step_pct)))]
    half = step_pct / 2.0
    rows = []
    for b in bins:
        d = _pick_nearest(disch, b, half)
        c = _pick_nearest(chg, b, half)
        if d is None and c is None:
            continue
        v_d = d.v_eq if d else None
        v_c = c.v_eq if c else None
        if v_d is not None and v_c is not None:
            v_pseudo = (v_d + v_c) / 2.0
        elif v_d is not None:
            v_pseudo = v_d
        else:
            v_pseudo = v_c
        rows.append({
            "soc_pct": b,
            "v_discharge": v_d,
            "v_charge": v_c,
            "v_pseudo_ocv": v_pseudo,
        })
    return rows


def _pick_nearest(results: list[StepResult], soc_pct: float, tol_pct: float):
    candidates = [
        r for r in results
        if abs(r.soc_after * 100.0 - soc_pct) <= tol_pct
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda r: abs(r.soc_after * 100.0 - soc_pct))


def write_ocv_table(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["soc_pct", "v_discharge", "v_charge", "v_pseudo_ocv"])
        for r in rows:
            w.writerow([
                f"{r['soc_pct']:.2f}",
                f"{r['v_discharge']:.5f}" if r['v_discharge'] is not None else "",
                f"{r['v_charge']:.5f}"    if r['v_charge']    is not None else "",
                f"{r['v_pseudo_ocv']:.5f}",
            ])


# ───────────────────────── orchestrator ──────────────────────────

def run_gitt(
    step_pct: float, rest_min: float, c_rate: float, dry_run: bool = False,
) -> int:
    battery = require_battery()
    print_summary(battery)

    step_frac = step_pct / 100.0
    rest_s = rest_min * 60.0
    q_step_mAh = battery.q_rated_mAh * step_frac
    n_steps_per_dir = int(round(1.0 / step_frac))
    c1_A = battery.q_rated_mAh / 1000.0
    i_cc = c_rate * c1_A

    # Step duration ≈ q_step / i_cc; one phase = n × (step + rest)
    step_h = (q_step_mAh / 1000.0) / i_cc / 3600.0
    rest_h = rest_min / 60.0
    one_phase_h = n_steps_per_dir * (step_h + rest_h)
    precharge_h_ub = 1.0 / c_rate + 0.5
    total_h = precharge_h_ub + 2 * one_phase_h

    now = datetime.now()
    eta = now + timedelta(hours=total_h)

    _print("")
    _print("=" * 64)
    _print(f"GITT pseudo-OCV builder — battery: {battery.name}")
    _print("=" * 64)
    _print(f"  step size       : {step_pct:.2f}%  ({q_step_mAh:.2f} mAh)")
    _print(f"  rest per step   : {rest_min:.0f} min")
    _print(f"  C-rate (CC)     : {c_rate:.2f}C  ({i_cc:.3f} A)")
    _print(f"  V_cv / V_cutoff : {battery.v_charge_cutoff:.3f} V / "
           f"{battery.v_discharge_cutoff:.3f} V")
    _print(f"  steps per dir   : {n_steps_per_dir}")
    _print(f"  V_eq window     : last {V_EQ_AVG_WINDOW_S:.0f} s of rest")
    _print(f"  dV/dt window    : last {DV_DT_WINDOW_S/60:.0f} min of rest")
    _print("")
    _print(f"  PHASE 1 precharge (upper bound) ≈ {precharge_h_ub:.1f} h")
    _print(f"  PHASE 2 discharge GITT          ≈ {one_phase_h:.1f} h")
    _print(f"  PHASE 3 charge    GITT          ≈ {one_phase_h:.1f} h")
    _print(f"  TOTAL (upper bound)             ≈ {total_h:.1f} h")
    _print(f"  start: {now.strftime('%Y-%m-%d %H:%M')}  "
           f"→ ETA: {eta.strftime('%Y-%m-%d %H:%M %a')}")
    _print("")

    if dry_run:
        _print("--dry-run: not driving the bench. Exit.")
        return 0

    # ── Set up logging files; share timestamp across all three ────
    trace = CsvLogger(DATA_DIR, tag="gitt_trace")
    # Derive shared ts from CsvLogger's filename so all three CSVs pair.
    ts = trace.path.stem.replace("gitt_trace_", "")
    summary_path = DATA_DIR / f"gitt_summary_{ts}.csv"
    ocv_path     = DATA_DIR / f"ocv_table_{ts}.csv"

    summary_fp = summary_path.open("w", newline="")
    summary_w = csv.writer(summary_fp)
    summary_w.writerow([
        "step_idx", "direction", "soc_before_pct", "soc_after_pct",
        "q_target_mAh", "q_actual_mAh", "duration_s",
        "v_start_loaded", "v_end_loaded",
        "v_rest_5min", "v_rest_15min", "v_rest_30min",
        "v_rest_45min", "v_rest_60min",
        "v_eq", "dv_dt_last5min_mvpermin", "note",
    ])
    summary_fp.flush()

    _print(f"[gitt] trace   → {trace.path}")
    _print(f"[gitt] summary → {summary_path}")
    _print(f"[gitt] ocv     → {ocv_path}")

    guard = SafetyGuard.from_profile(battery, i_hard_high=SAFETY.i_hard_high)

    disch_results: list[StepResult] = []
    chg_results: list[StepResult] = []

    with IT6302.open(PORT_PSU, BAUD) as psu, IT8512.open(PORT_LOAD, BAUD) as load:
        _print(f"[gitt] PSU : {psu.idn()}")
        _print(f"[gitt] LOAD: {load.idn()}")
        bench = BenchInterlock(psu=psu, load=load, deadtime_s=SAFETY.deadtime_s)

        run_t0 = time.monotonic()
        try:
            bench.assert_idle()

            # ── PHASE 1: pre-charge to full ───────────────────────
            _print("\n" + "=" * 64)
            _print(" PHASE 1/3 — pre-charge to full")
            _print("=" * 64)
            v0, v1, pc_note = precharge_to_full(
                psu=psu, load=load, bench=bench, battery=battery,
                guard=guard, c_rate=c_rate, trace=trace, run_t0=run_t0,
            )
            _print(f"[gitt] precharge done: V {v0:.4f} → {v1:.4f} ({pc_note})")

            # Anchor rest to capture OCV at ~100% SoC for the discharge
            # series. Treated as a synthetic step with idx=0.
            _print("\n  [precharge → discharge GITT] settle rest at full SoC")
            v_eq0, dvdt0, curve0 = run_rest_capture(
                psu=psu, load=load, rest_s=rest_s, soc_after=1.0,
                mode_tag="gitt_rest_init", step_label="precharge_rest",
                trace=trace, run_t0=run_t0,
            )
            anchor = StepResult(
                step_idx=0, direction="precharge_rest",
                soc_before=1.0, soc_after=1.0,
                q_target_mAh=0.0, q_actual_mAh=0.0,
                duration_s=rest_s,
                v_start_loaded=v1, v_end_loaded=v1,
                v_rest_curve=curve0, v_eq=v_eq0,
                dv_dt_last_window_mvpermin=dvdt0,
                note="anchor_full",
            )
            write_summary_row(summary_w, summary_fp, anchor)
            # Anchor is the discharge-direction OCV at 100% SoC.
            disch_results.append(anchor)

            # ── PHASE 2: discharge GITT (100% → ~0%) ──────────────
            _print("\n" + "=" * 64)
            _print(f" PHASE 2/3 — discharge GITT  "
                   f"({n_steps_per_dir} × {step_pct:.1f}%)")
            _print("=" * 64)
            soc = 1.0
            for k in range(n_steps_per_dir):
                if soc <= 0.001:
                    break
                idx = k + 1
                res = run_gitt_step(
                    direction="discharge",
                    psu=psu, load=load, bench=bench, battery=battery,
                    guard=guard,
                    c_rate=c_rate, q_target_mAh=q_step_mAh,
                    soc_before=soc, rest_s=rest_s, step_idx=idx,
                    trace=trace, run_t0=run_t0,
                )
                disch_results.append(res)
                write_summary_row(summary_w, summary_fp, res)
                soc = res.soc_after
                if res.note == "v_limited":
                    _print(f"  [gitt] V_cutoff reached after step {idx} — "
                           f"ending discharge phase at SoC={soc*100:.2f}%")
                    break

            # ── PHASE 3: charge GITT (~0% → ~100%) ────────────────
            _print("\n" + "=" * 64)
            _print(f" PHASE 3/3 — charge GITT  "
                   f"({n_steps_per_dir} × {step_pct:.1f}%)")
            _print("=" * 64)
            soc = max(0.0, soc)
            # Extra slack in case v_limited fires before nominal full SoC.
            for k in range(n_steps_per_dir + 4):
                if soc >= 0.999:
                    break
                idx = len(disch_results) + k
                res = run_gitt_step(
                    direction="charge",
                    psu=psu, load=load, bench=bench, battery=battery,
                    guard=guard,
                    c_rate=c_rate, q_target_mAh=q_step_mAh,
                    soc_before=soc, rest_s=rest_s, step_idx=idx,
                    trace=trace, run_t0=run_t0,
                )
                chg_results.append(res)
                write_summary_row(summary_w, summary_fp, res)
                soc = res.soc_after
                if res.note == "v_limited":
                    _print(f"  [gitt] V_cv reached after step {idx} — "
                           f"ending charge phase at SoC={soc*100:.2f}%")
                    break

            # ── Build pseudo-OCV table ────────────────────────────
            _print("\n" + "=" * 64)
            _print(" Building pseudo-OCV table")
            _print("=" * 64)
            ocv_rows = build_pseudo_ocv(disch_results, chg_results, step_pct)
            write_ocv_table(ocv_path, ocv_rows)
            _print(f"[gitt] OCV table written: {ocv_path}  "
                   f"({len(ocv_rows)} SoC bins)")
            for r in ocv_rows:
                vd = f"{r['v_discharge']:.5f}" if r['v_discharge'] is not None else "  —    "
                vc = f"{r['v_charge']:.5f}"    if r['v_charge']    is not None else "  —    "
                _print(f"    SoC {r['soc_pct']:5.1f}%  "
                       f"V_disch={vd}  V_chg={vc}  "
                       f"V_pseudo={r['v_pseudo_ocv']:.5f}")

            _print("\n" + "=" * 64)
            _print(" GITT complete — cell at full charge, "
                   "ready for next round")
            _print("=" * 64)

        except KeyboardInterrupt:
            _print("\n\n[gitt] !!! interrupted by user — emergency stop")
        except SafetyAbort as e:
            _print(f"\n\n[gitt] !!! SAFETY ABORT: {e}")
        except BenchInterlockError as e:
            _print(f"\n\n[gitt] !!! BENCH INTERLOCK: {e}")
        except Exception as e:
            _print(f"\n\n[gitt] !!! unexpected: {type(e).__name__}: {e}")
            raise
        finally:
            try:
                bench.emergency_stop()
            except Exception as e:
                _print(f"[gitt] emergency_stop secondary failure: {e}")
            try:
                summary_fp.close()
            except Exception:
                pass
            try:
                trace.close()
            except Exception:
                pass

    return 0


# ───────────────────────── entrypoint ────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan without driving the bench")
    ap.add_argument("--step-pct", type=float, default=DEFAULT_STEP_PCT,
                    help=f"SoC step size in %% (default {DEFAULT_STEP_PCT})")
    ap.add_argument("--rest-min", type=float, default=DEFAULT_REST_MIN,
                    help=f"rest duration per step in min "
                         f"(default {DEFAULT_REST_MIN:.0f})")
    ap.add_argument("--c-rate", type=float, default=DEFAULT_C_RATE,
                    help=f"CC C-rate for both directions "
                         f"(default {DEFAULT_C_RATE})")
    args = ap.parse_args()
    return run_gitt(
        step_pct=args.step_pct,
        rest_min=args.rest_min,
        c_rate=args.c_rate,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
