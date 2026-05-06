"""Test bench configuration.

All experiment parameters live here so phase scripts stay short.
Match values to meeting_0416 plan; adjust per battery batch as needed.
"""
from __future__ import annotations

from dataclasses import dataclass


# --- Serial port mapping (confirmed by *IDN? probe on 2026-05-06) ---
PORT_LOAD = "/dev/ttyACM0"   # IT8512A (electronic load)
PORT_PSU = "/dev/ttyACM1"    # IT6302  (DC power supply)
BAUD = 9600


# --- Battery under test: 18650, per meeting_0416 slide 5 ---
@dataclass(frozen=True)
class BatterySpec:
    name: str = "18650-Sample"
    q_rated_mAh: float = 2150.0   # nominal capacity
    v_nominal: float = 3.7
    v_max: float = 4.20           # full-charge / hard upper cutoff
    v_min: float = 2.75           # discharge / hard lower cutoff
    v_charge_cv: float = 4.20     # CV target during charge
    i_charge_cc: float = 1.075    # 0.5 C charge current  (A)
    i_charge_term: float = 0.05   # CV cut-off current     (A)
    i_discharge_cc: float = 1.075 # 0.5 C baseline discharge current (A)


BATTERY = BatterySpec()


# --- Hard safety envelope (instrument enforces these no matter what) ---
@dataclass(frozen=True)
class SafetyLimits:
    v_hard_high: float = 4.25     # abort if V exceeds this
    v_hard_low: float = 2.70      # abort if V drops below this
    i_hard_high: float = 4.30     # abort if |I| exceeds this
    sample_period_s: float = 1.0  # main loop period (paper: 1 Hz)


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
