"""Voltage / current envelope guard.

Two layers:

  1. Absolute envelope — chemistry-imposed hard limits (e.g. Li-ion NMC
     V_abs_max=4.25 V, V_abs_min=2.50 V). Crossing these is a single-sample
     instant trip — no debounce. We will not knowingly let the cell sit
     past these even for one sample.

  2. Trip envelope — a tighter wrapper around the user's profile setpoints
     (charge cutoff, discharge cutoff). Crossing requires N consecutive
     bad samples (default 2) so we don't fire on transient noise during
     normal operation, but it still trips well before the absolute floor.

Phase scripts call SafetyGuard.check(v, i) every sample. On any trip we
raise SafetyAbort, and the phase script's `finally` block flips both
instruments to a safe state via BenchInterlock.emergency_stop().
"""
from __future__ import annotations

from dataclasses import dataclass


class SafetyAbort(RuntimeError):
    """Raised when a hard envelope limit is crossed."""


@dataclass
class SafetyGuard:
    # Soft trip envelope (debounced).
    v_high: float
    v_low: float
    i_high: float
    consecutive_required: int = 2   # require N bad samples in a row to trip

    # Absolute envelope (no debounce — instant trip). Default to ±inf so the
    # caller has to opt in. In practice phase scripts pass the chemistry
    # envelope here.
    v_abs_high: float = float("inf")
    v_abs_low: float = float("-inf")
    i_abs_high: float = float("inf")

    _v_high_count: int = 0
    _v_low_count: int = 0
    _i_high_count: int = 0

    def check(self, v: float, i: float) -> None:
        # --- Absolute envelope: instant trip, no debounce ---
        if v > self.v_abs_high:
            raise SafetyAbort(
                f"ABS V={v:.3f} > v_abs_high={self.v_abs_high:.3f} (chemistry limit)"
            )
        if v < self.v_abs_low:
            raise SafetyAbort(
                f"ABS V={v:.3f} < v_abs_low={self.v_abs_low:.3f} (chemistry limit)"
            )
        if abs(i) > self.i_abs_high:
            raise SafetyAbort(
                f"ABS |I|={abs(i):.3f} > i_abs_high={self.i_abs_high:.3f} "
                "(wiring/instrument limit)"
            )

        # --- Soft trip envelope: debounced ---
        if v > self.v_high:
            self._v_high_count += 1
            if self._v_high_count >= self.consecutive_required:
                raise SafetyAbort(f"V={v:.3f} > v_high={self.v_high:.3f}")
        else:
            self._v_high_count = 0

        if v < self.v_low:
            self._v_low_count += 1
            if self._v_low_count >= self.consecutive_required:
                raise SafetyAbort(f"V={v:.3f} < v_low={self.v_low:.3f}")
        else:
            self._v_low_count = 0

        if abs(i) > self.i_high:
            self._i_high_count += 1
            if self._i_high_count >= self.consecutive_required:
                raise SafetyAbort(f"|I|={abs(i):.3f} > i_high={self.i_high:.3f}")
        else:
            self._i_high_count = 0

    @classmethod
    def from_profile(cls, profile, i_hard_high: float = 4.30) -> "SafetyGuard":
        """Build a guard whose envelope is tight to the user's profile."""
        chem = profile.chem_envelope()
        # Soft envelope: 50 mV beyond the user's setpoint (so phase scripts can
        # measure cutoff exactly, but we trip slightly past it).
        v_high_soft = profile.v_charge_cutoff + 0.050
        v_low_soft = profile.v_discharge_cutoff - 0.050
        return cls(
            v_high=v_high_soft,
            v_low=v_low_soft,
            i_high=i_hard_high,
            v_abs_high=chem.v_abs_max,
            v_abs_low=chem.v_abs_min,
            i_abs_high=i_hard_high + 0.5,   # leave headroom over soft trip
        )
