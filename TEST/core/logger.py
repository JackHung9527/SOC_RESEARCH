"""CSV time-series logger for bench tests.

Writes one row per sample with consistent columns across phases so the
analysis scripts don't need to special-case file formats. Header is fixed:

  t_s, mode, v, i, soc_cc, dvdi, note

`mode` is a free-form tag for the test phase ("discharge", "perturb_low",
"perturb_high", "rest", ...). `dvdi` and `note` may be empty.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional


HEADER = ["t_s", "mode", "v", "i", "soc_cc", "dvdi", "note"]


class CsvLogger:
    def __init__(self, out_dir: Path | str, tag: str):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = out_dir / f"{tag}_{ts}.csv"
        self._fp = self.path.open("w", newline="")
        self._w = csv.writer(self._fp)
        self._w.writerow(HEADER)
        self._fp.flush()

    def log(
        self,
        t_s: float,
        mode: str,
        v: float,
        i: float,
        soc_cc: float,
        dvdi: Optional[float] = None,
        note: str = "",
    ) -> None:
        self._w.writerow([
            f"{t_s:.3f}",
            mode,
            f"{v:.5f}",
            f"{i:.5f}",
            f"{soc_cc:.5f}",
            "" if dvdi is None else f"{dvdi:.5f}",
            note,
        ])
        self._fp.flush()

    def close(self) -> None:
        if not self._fp.closed:
            self._fp.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
