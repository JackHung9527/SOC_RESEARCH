#!/usr/bin/env python3
"""fig4-5：動態阻抗之量測域對照——台架（負載端）vs 板端（電池端子）。

資料：
  台架散點：Round 40 主控台 [perturb] 行（IT8512 端 dV/dI 與當時 SoC）
  板端散點：Round 40 MCU log 之 zdyn 事件（INA226 端），SOC 由台架 CSV 對齊
  兩條擬合拋物線：台架域（表 4-3 合併 a=20.2,b=−21.6,c=63.6）、
                板端域（Round 40 重擬合 a=18.0,b=−21.1,c=39.6）

風格比照論文 figures（白底、細格線）；中文用 Noto Sans CJK TC（Pi）。
"""

import bisect
import csv
import glob
import re
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in font_manager.fontManager.ttflist:
    if "Noto Sans CJK TC" in f.name:
        plt.rcParams["font.family"] = "Noto Sans CJK TC"
        break
plt.rcParams["axes.unicode_minus"] = False

ROOT = "/home/jackhung/Desktop/AI/SOC_RESEARCH"
OUT = f"{ROOT}/DOC/論文撰寫/figures/fig4-5.png"

# ---- 台架散點 ----
bench = []
pat = re.compile(r"dV/dI=-([\d.]+) mΩ  \(SoC ([\d.]+)%\)")
for ln in open(f"{ROOT}/TEST/data/round_console_20260707_0113.log"):
    m = pat.search(ln)
    if m:
        bench.append((float(m.group(2)), float(m.group(1))))

# ---- 板端散點（zdyn 事件 × 台架真值對齊） ----
rows, prev_n = [], None
for ln in open(f"{ROOT}/TEST/data/mcu_soc_log_20260707_011325.log"):
    p = ln.split("\t", 3)
    if len(p) < 4 or p[2] != "mcu":
        continue
    m = re.search(r"z=[\d.]+%\(n=(\d+),([\d.]+)mohm", p[3])
    if m:
        n = int(m.group(1))
        if prev_n is not None and n > prev_n:
            rows.append((float(p[0]), float(m.group(2))))
        prev_n = n

def load(path):
    t, s = [], []
    for r in csv.DictReader(open(path)):
        t.append(float(r["t_s"]))
        s.append(float(r["soc_cc"]) * 100)
    e0 = datetime.strptime(re.search(r"(\d{8}_\d{6})", path).group(1),
                           "%Y%m%d_%H%M%S").timestamp()
    return e0, t, s

segs = [load(p) for p in
        sorted(glob.glob(f"{ROOT}/TEST/data/round040_cyc18*_discharge_*.csv"))]
board = []
for e, z in rows:
    for e0, t, s in segs:
        if e0 <= e <= e0 + t[-1]:
            j = bisect.bisect_right(t, e - e0)
            if 0 < j < len(t):
                x0, x1, y0, y1 = t[j-1], t[j], s[j-1], s[j]
                board.append((y0 + (y1-y0)*(e-e0-x0)/(x1-x0), z))
            break

# ---- 畫圖 ----
fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=200)
xs = [x/1000 for x in range(0, 100001)]

def quad(a, b, c):
    return [a*(x/100)**2 + b*(x/100) + c for x in xs]

ax.scatter([p[0] for p in bench], [p[1] for p in bench], s=9, alpha=0.45,
           color="#1f77b4", edgecolors="none", label="台架量測（IT8512 負載端）", zorder=3)
ax.scatter([p[0] for p in board], [p[1] for p in board], s=9, alpha=0.45,
           color="#d62728", edgecolors="none", label="板端量測（INA226 電池端子）", zorder=3)
ax.plot(xs, quad(20.2, -21.6, 63.6), color="#1f77b4", lw=1.6,
        label="台架域擬合（表 4-3 合併）", zorder=4)
ax.plot(xs, quad(18.0, -21.1, 39.6), color="#d62728", lw=1.6,
        label="板端域擬合（Round 40）", zorder=4)

# 量測域偏移標註：在 SOC 20% 處畫雙頭箭頭（該處兩曲線間隙開闊、無散點干擾）
x_ann = 20.0
y_top = 20.2*0.04 - 21.6*0.2 + 63.6
y_bot = 18.0*0.04 - 21.1*0.2 + 39.6
ax.annotate("", xy=(x_ann, y_bot + 0.6), xytext=(x_ann, y_top - 0.6),
            arrowprops=dict(arrowstyle="<->", color="#444444", lw=1.2))
ax.text(x_ann - 2.5, (y_top + y_bot)/2, "量測域差 ≈ 24 mΩ\n（線材／接點電阻）",
        ha="right", va="center", fontsize=9, color="#333333")

ax.set_xlabel("SOC (%)")
ax.set_ylabel("動態阻抗 |ΔV/ΔI| (mΩ)")
ax.set_xlim(0, 100)
ax.set_ylim(25, 72)
ax.grid(True, lw=0.4, alpha=0.5)
ax.legend(loc="center right", fontsize=8.5, framealpha=0.95)
fig.tight_layout()
fig.savefig(OUT, facecolor="white")
print(f"[done] {OUT}  台架點={len(bench)}  板端點={len(board)}")
