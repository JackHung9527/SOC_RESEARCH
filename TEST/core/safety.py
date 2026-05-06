"""Voltage / current envelope guard.

Phase scripts call SafetyGuard.check(v, i) every loop iteration. If a hard
limit is breached it raises SafetyAbort, and the phase script's `finally`
block will flip both instruments to a safe state.
"""
from __future__ import annotations

from dataclasses import dataclass


class SafetyAbort(RuntimeError):
    """Raised when a hard envelope limit is crossed."""


@dataclass
class SafetyGuard:
    v_high: float
    v_low: float
    i_high: float
    consecutive_required: int = 2   # require 2 bad samples in a row to trip

    _v_high_count: int = 0
    _v_low_count: int = 0
    _i_high_count: int = 0

    def check(self, v: float, i: float) -> None:
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
