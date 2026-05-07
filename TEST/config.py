"""Test bench configuration.

Battery-specific values now live in TEST/profiles.py (selected via
`python3 TEST/select_battery.py`). This file holds bench-wide knobs:
serial ports, baud, default phase parameters, dead-time between
charge/discharge.

Backward compatibility: legacy code that imports BATTERY / SAFETY from
this module will receive values derived from the active profile (if one
has been selected). If no profile is selected, BATTERY is None and
SAFETY uses chemistry-agnostic conservative defaults — phase scripts
should refuse to run in that state.
"""
from __future__ import annotations

from dataclasses import dataclass

from TEST.profiles import try_load_active_profile


# --- Serial port mapping (confirmed by *IDN? probe on 2026-05-06) ---
PORT_LOAD = "/dev/ttyACM0"   # IT8512A (electronic load)
PORT_PSU = "/dev/ttyACM1"    # IT6302  (DC power supply)
BAUD = 9600


# --- Active battery profile -----------------------------------------------
# None if user hasn't run select_battery.py yet.
BATTERY = try_load_active_profile()


# --- Hard safety envelope (instrument enforces these no matter what) ---
@dataclass(frozen=True)
class SafetyLimits:
    i_hard_high: float = 4.30     # abort if |I| exceeds this (wiring limit)
    sample_period_s: float = 1.0  # main loop period (paper: 1 Hz)
    deadtime_s: float = 5.0       # mandatory rest after every output disable


SAFETY = SafetyLimits()


# --- Phase 2 baseline parameters ---
@dataclass(frozen=True)
class Phase2Params:
    rate_C: float = 0.5
    perturb_period_s: int = 60    # inject a current step every N seconds
    perturb_low_C: float = 0.2    # step down to 0.2 C briefly
    perturb_dwell_s: float = 1.0  # hold each level for this long
    pre_rest_s: int = 60          # OCV settle time before discharge starts


PHASE2 = Phase2Params()


# --- Phase 3 multi-rate sweep ---
PHASE3_RATES = [0.2, 0.5, 1.0, 2.0]   # C-rates, in test order
PHASE3_PULSE_ON_S = 10
PHASE3_PULSE_OFF_S = 30


# --- Phase 4 aging cycle ---
PHASE4_CYCLES_PER_CHECKPOINT = 50     # record SOH every N cycles
PHASE4_TARGET_CYCLES = 500


def require_battery():
    """Phase scripts call this first — fails loudly if no profile selected."""
    if BATTERY is None:
        raise SystemExit(
            "ERROR: no active battery profile.\n"
            "  Run: python3 TEST/select_battery.py\n"
            "  to pick a cell before running any test."
        )
    return BATTERY
