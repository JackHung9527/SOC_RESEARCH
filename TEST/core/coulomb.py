"""Coulomb counter for SoC tracking.

Sign convention: discharge current is *positive* (energy leaving the cell),
charge current is *negative*. SoC decreases when integrating positive I.

`q_rated_mAh` is the cell's nameplate capacity. SoC = 1.0 means full.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CoulombCounter:
    q_rated_mAh: float
    soc_init: float = 1.0

    _charge_drawn_mAs: float = 0.0   # accumulated A·s out of the cell

    def __post_init__(self):
        self.q_rated_mAs = self.q_rated_mAh * 3600.0 / 1000.0
        self._charge_drawn_mAs = (1.0 - self.soc_init) * self.q_rated_mAs

    def update(self, current_A: float, dt_s: float) -> float:
        """Advance integrator. Returns current SoC in [0, 1]."""
        self._charge_drawn_mAs += current_A * dt_s
        return self.soc

    @property
    def soc(self) -> float:
        soc = 1.0 - (self._charge_drawn_mAs / self.q_rated_mAs)
        return max(0.0, min(1.0, soc))

    @property
    def ah_used(self) -> float:
        return self._charge_drawn_mAs / 3600.0
