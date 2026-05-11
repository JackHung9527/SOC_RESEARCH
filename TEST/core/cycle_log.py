"""Persistent cycle log for multi-round rate-capability testing.

One row per completed charge / discharge step. Rest periods are not logged
here (they're idle time, no electrochemical event). Resumes across runs by
inspecting the existing CSV.

Sign convention:
  - ah_throughput is the magnitude of charge moved this step (always > 0).
  - cumulative_ah is the running total across all rows in this file.
  - cycle_id increments on every completed discharge-to-cutoff. Charges
    inherit the cycle_id of the discharge that follows them, so each
    (charge, discharge) pair shares one cycle_id.

CSV schema (header row written on first creation):

  cycle_id, round_id, step_id, direction, c_rate, c_rate_A,
  v_start, v_end, ah, q_actual_mAh, q_retention_pct,
  t_start_iso, duration_s, cumulative_ah, csv_path, note
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


HEADER = [
    "cycle_id", "round_id", "step_id", "direction", "c_rate", "c_rate_A",
    "v_start", "v_end", "ah", "q_actual_mAh", "q_retention_pct",
    "t_start_iso", "duration_s", "cumulative_ah", "csv_path", "note",
]


@dataclass
class CycleState:
    """Where the log is up to. Read off the existing CSV at startup."""
    next_cycle_id: int = 1          # incremented on the NEXT discharge completion
    next_round_id: int = 1          # incremented on each new round
    next_step_id: int = 1           # global, never resets
    cumulative_ah: float = 0.0      # |Ah| moved in total, charge + discharge

    @classmethod
    def from_csv(cls, path: Path) -> "CycleState":
        """Reconstruct counters from an existing cycle_log.csv."""
        if not path.exists():
            return cls()

        max_cycle = 0
        max_round = 0
        max_step = 0
        cum_ah = 0.0
        with path.open() as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                try:
                    max_cycle = max(max_cycle, int(row["cycle_id"]))
                    max_round = max(max_round, int(row["round_id"]))
                    max_step = max(max_step, int(row["step_id"]))
                    cum_ah = max(cum_ah, float(row["cumulative_ah"]))
                except (KeyError, ValueError):
                    continue

        return cls(
            next_cycle_id=max_cycle + 1,
            next_round_id=max_round + 1,
            next_step_id=max_step + 1,
            cumulative_ah=cum_ah,
        )


class CycleLog:
    """Append-only writer for cycle_log.csv, with auto-resume."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = CycleState.from_csv(self.path)
        if not self.path.exists():
            with self.path.open("w", newline="") as f:
                csv.writer(f).writerow(HEADER)

    def append_step(
        self,
        *,
        cycle_id: int,
        round_id: int,
        direction: str,                 # "charge" | "discharge"
        c_rate: float,
        c_rate_A: float,
        v_start: float,
        v_end: float,
        ah: float,
        q_rated_mAh: float,
        t_start_iso: str,
        duration_s: float,
        csv_path: Optional[Path],
        note: str = "",
    ) -> dict:
        """Append one completed step and advance counters."""
        if direction == "discharge":
            q_actual_mAh = ah * 1000.0
            q_retention_pct = 100.0 * q_actual_mAh / q_rated_mAh if q_rated_mAh > 0 else 0.0
        else:
            q_actual_mAh = ah * 1000.0
            q_retention_pct = 0.0   # not meaningful for charge

        self.state.cumulative_ah += abs(ah)

        row = {
            "cycle_id": cycle_id,
            "round_id": round_id,
            "step_id": self.state.next_step_id,
            "direction": direction,
            "c_rate": f"{c_rate:.2f}",
            "c_rate_A": f"{c_rate_A:.4f}",
            "v_start": f"{v_start:.4f}",
            "v_end": f"{v_end:.4f}",
            "ah": f"{ah:.5f}",
            "q_actual_mAh": f"{q_actual_mAh:.2f}",
            "q_retention_pct": f"{q_retention_pct:.3f}",
            "t_start_iso": t_start_iso,
            "duration_s": f"{duration_s:.1f}",
            "cumulative_ah": f"{self.state.cumulative_ah:.5f}",
            "csv_path": "" if csv_path is None else str(csv_path),
            "note": note,
        }

        with self.path.open("a", newline="") as f:
            csv.DictWriter(f, fieldnames=HEADER).writerow(row)

        self.state.next_step_id += 1
        return row

    def utc_now_iso(self) -> str:
        return datetime.now().isoformat(timespec="seconds")
