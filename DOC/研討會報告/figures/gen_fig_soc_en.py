#!/usr/bin/env python3
"""Figure: on-board SOC trajectories of the three methods vs bench Coulomb
ground truth (Round 41 board measurement, four discharge rates). English labels.

Data (identical pipeline to thesis fig4-6):
  bench truth : round041_cyc189-192_discharge_{0.5,1.0,1.5,2.0}C CSV (soc_cc)
  on-board    : mcu_soc_log_20260707_210836.log per-second soc lines (cc/ekf/z)
"""
import bisect
import csv
import glob
import math
import os
import re
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["mathtext.fontset"] = "stix"

HERE = os.path.dirname(os.path.abspath(__file__))
# repo root = .../SOC_RESEARCH  (this file is DOC/研討會報告/figures/)
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "fig_soc_en.png")
MCU_LOG = os.path.join(ROOT, "TEST", "data", "mcu_soc_log_20260707_210836.log")

RE_SOC = re.compile(
    r"soc cc=([\d.]+)%\((\d+)cyc\) ekf=([\d.]+)%\((\d+)cyc\)"
    r"(?: z=(?:--\(no event yet\)|([\d.]+)%\(n=(\d+),([\d.]+)mohm,(\d+)cyc\)))?")
RE_ALIVE = re.compile(r"Ical=(-?[\d.]+)mA")

soc_rows, alive_rows = [], []
with open(MCU_LOG, encoding="utf-8") as f:
    for ln in f:
        parts = ln.rstrip("\n").split("\t", 3)
        if len(parts) < 4 or parts[2] != "mcu":
            continue
        epoch, text = float(parts[0]), parts[3]
        m = RE_SOC.search(text)
        if m:
            z = float(m.group(5)) if m.group(5) else None
            soc_rows.append((epoch, float(m.group(1)), float(m.group(3)), z))
            continue
        m = RE_ALIVE.search(text)
        if m:
            alive_rows.append((epoch, float(m.group(1))))
print(f"[mcu] {len(soc_rows)} soc / {len(alive_rows)} alive")


def load_bench(path):
    t, soc, i_a = [], [], []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            t.append(float(r["t_s"]))
            soc.append(float(r["soc_cc"]) * 100.0)
            i_a.append(float(r["i"]))
    e0 = datetime.strptime(re.search(r"(\d{8}_\d{6})", path).group(1),
                           "%Y%m%d_%H%M%S").timestamp()
    thr = 0.4 * max(i_a) * 1000.0
    cand = [e for e, i_ma in alive_rows if abs(e - e0) <= 90.0 and i_ma > thr]
    if cand and abs(min(cand) - e0) > 5.0:
        e0 = min(cand)
    return e0, t, soc


def interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    j = bisect.bisect_right(xs, x)
    x0, x1, y0, y1 = xs[j - 1], xs[j], ys[j - 1], ys[j]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


csvs = sorted(glob.glob(os.path.join(ROOT, "TEST", "data",
                                     "round041_cyc*_discharge_*.csv")))
labels = ["(a) 0.5C discharge", "(b) 1.0C discharge",
          "(c) 1.5C discharge", "(d) 2.0C discharge"]

fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4), dpi=200)

for k, (path, ax) in enumerate(zip(csvs, axes.flat)):
    e0, t, soc_true = load_bench(path)
    t_end = t[-1]
    seg = [(e, cc, ekf, z) for e, cc, ekf, z in soc_rows
           if e0 <= e <= e0 + t_end]

    tmin = [x / 60.0 for x in t]
    ax.plot(tmin, soc_true, color="#222222", lw=1.8,
            label="Bench Coulomb (reference)", zorder=5)
    ax.plot([(e - e0) / 60.0 for e, *_ in seg], [cc for _, cc, _, _ in seg],
            color="#1f77b4", lw=1.2, ls="--", label="On-board Coulomb", zorder=4)
    ax.plot([(e - e0) / 60.0 for e, *_ in seg], [ekf for _, _, ekf, _ in seg],
            color="#2ca02c", lw=1.2, label="On-board EKF", zorder=6)
    zx = [(e - e0) / 60.0 for e, _, _, z in seg if z is not None]
    zy = [z for _, _, _, z in seg if z is not None]
    ax.plot(zx, zy, color="#d62728", lw=1.0, alpha=0.85,
            label="On-board dynamic impedance", zorder=3)

    rmse = {}
    for name, idx in (("Coul", 1), ("EKF", 2), ("Imp", 3)):
        errs = [row[idx] - interp(t, soc_true, row[0] - e0)
                for row in seg if row[idx] is not None]
        if errs:
            rmse[name] = math.sqrt(sum(x * x for x in errs) / len(errs))
    txt = "RMSE: " + ", ".join(f"{n} {v:.2f}%" if v < 10 else f"{n} {v:.1f}%"
                               for n, v in rmse.items())
    ax.text(0.03, 0.06, txt, transform=ax.transAxes, fontsize=7.4,
            ha="left", va="bottom", zorder=7,
            bbox=dict(facecolor="white", edgecolor="#999999",
                      lw=0.5, alpha=0.9, pad=2.2))

    ax.set_title(labels[k], fontsize=9.8)
    ax.set_xlim(0, math.ceil(t_end / 60.0 / 5.0) * 5)
    ax.set_ylim(-3, 105)
    ax.grid(True, lw=0.4, alpha=0.5)
    ax.tick_params(labelsize=8)
    if k >= 2:
        ax.set_xlabel("Discharge time (min)", fontsize=9.5)
    if k % 2 == 0:
        ax.set_ylabel("SOC (%)", fontsize=9.5)
    print(f"  {os.path.basename(path)}: n={len(seg)}  " +
          "  ".join(f"{n}={v:.2f}%" for n, v in rmse.items()))

handles, leg_labels = axes.flat[0].get_legend_handles_labels()
fig.legend(handles, leg_labels, loc="upper center", ncol=4, fontsize=8.2,
           frameon=False, bbox_to_anchor=(0.5, 1.0))
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(OUT, facecolor="white")
print(f"[done] {OUT}")
