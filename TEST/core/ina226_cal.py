"""Piecewise-linear calibration LUT for INA226 current readout.

Two LUTs are kept separately (discharge / charge) because the INA226 may
have asymmetric offset across the shunt depending on current direction.

LUT shape (sorted ascending by mcu_A):
    points = [(mcu_A_0, ref_A_0), (mcu_A_1, ref_A_1), ...]

Lookup:
    given mcu_A_measured, find bracket k such that
        mcu_A[k] <= mcu_A_measured <= mcu_A[k+1]
    then interpolate:
        ref_A = ref_A[k] + (ref_A[k+1] - ref_A[k]) *
                (mcu_A_measured - mcu_A[k]) / (mcu_A[k+1] - mcu_A[k])

Out-of-range:
    Below first point  → extrapolate using the first segment
    Above last point   → extrapolate using the last segment

This matches the user's requirement: piecewise linear, no polynomial fit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


CAL_FILE = Path(__file__).resolve().parent.parent / "data" / "calibration_ina226.json"


@dataclass(frozen=True)
class CalLUT:
    direction: Literal["discharge", "charge"]
    mcu_A: tuple[float, ...]
    ref_A: tuple[float, ...]

    def __post_init__(self):
        if len(self.mcu_A) != len(self.ref_A):
            raise ValueError("mcu_A and ref_A must be same length")
        if len(self.mcu_A) < 2:
            raise ValueError("need at least 2 calibration points")
        # Ensure ascending order by mcu_A; sort both together as paired tuples
        # so the mcu_A ↔ ref_A pairing is preserved (charge direction has
        # negative mcu values; naive sort of each separately mismatches).
        if list(self.mcu_A) != sorted(self.mcu_A):
            paired = sorted(zip(self.mcu_A, self.ref_A), key=lambda t: t[0])
            object.__setattr__(self, "mcu_A", tuple(p[0] for p in paired))
            object.__setattr__(self, "ref_A", tuple(p[1] for p in paired))

    def correct(self, mcu_A_measured: float) -> float:
        """Apply piecewise-linear interpolation to mcu_A_measured."""
        m = self.mcu_A
        r = self.ref_A
        # Below first point — extrapolate using first segment
        if mcu_A_measured <= m[0]:
            slope = (r[1] - r[0]) / (m[1] - m[0])
            return r[0] + slope * (mcu_A_measured - m[0])
        # Above last point — extrapolate using last segment
        if mcu_A_measured >= m[-1]:
            slope = (r[-1] - r[-2]) / (m[-1] - m[-2])
            return r[-1] + slope * (mcu_A_measured - m[-1])
        # In-range — find bracket and interpolate
        for k in range(len(m) - 1):
            if m[k] <= mcu_A_measured <= m[k + 1]:
                t = (mcu_A_measured - m[k]) / (m[k + 1] - m[k])
                return r[k] + t * (r[k + 1] - r[k])
        # Should be unreachable; fail explicitly
        raise RuntimeError("bracket search failed (LUT inconsistent)")


def load_cal(path: Path = CAL_FILE) -> tuple[CalLUT, CalLUT]:
    """Load discharge + charge LUTs from the calibration JSON."""
    raw = json.loads(path.read_text())

    def to_lut(direction: str) -> CalLUT:
        pts = raw[direction]
        return CalLUT(
            direction=direction,
            mcu_A=tuple(p["mcu_A"] for p in pts),
            ref_A=tuple(p["ref_A"] for p in pts),
        )

    return to_lut("discharge"), to_lut("charge")


def correct(mcu_A_measured: float,
            direction: Literal["discharge", "charge"]) -> float:
    """One-shot helper that loads the LUT on each call. For batch use
    `load_cal()` once and call .correct() many times."""
    disc, chg = load_cal()
    lut = disc if direction == "discharge" else chg
    return lut.correct(mcu_A_measured)
