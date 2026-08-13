# -*- coding: utf-8 -*-
"""產生 A4 論文精華海報專用圖（1:1 列印尺寸，字級以列印後可讀為準）。

輸出（皆 dpi=300、白底）：
  poster_fig1_arch.png     欄內寬 8.5 cm — 測試平台系統架構
  poster_fig2_zdomain.png  欄內寬 8.5 cm — 動態阻抗量測域對照（核心發現）
  poster_fig3_soc.png      跨欄寬 18.0 cm — 三法 SOC 軌跡（1.0C / 2.0C 兩面板）

資料來源與論文圖 3-1／4-5／4-6 完全相同，僅重新排版為海報尺寸。
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
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(ROOT, "TEST", "data")

names = {f.name for f in font_manager.fontManager.ttflist}
CJK = next((c for c in ("Microsoft JhengHei", "Noto Sans CJK TC") if c in names),
           "sans-serif")
plt.rcParams["font.family"] = CJK
plt.rcParams["axes.unicode_minus"] = False

COL_W = 3.35   # 欄內圖寬（吋）≈ 8.5 cm
FULL_W = 7.09  # 跨欄圖寬（吋）≈ 18.0 cm


# ---------------------------------------------------------------- 圖 1 架構
def gen_arch():
    ARROW, TXT = "#5A5A5A", "#1A1A1A"
    S = {"host": dict(fc="#2E5C9A", ec="#1F3864", tc="white"),
         "inst": dict(fc="#DCE6F4", ec="#2E5C9A", tc=TXT),
         "mcu": dict(fc="#E2EFDA", ec="#548235", tc=TXT),
         "dut": dict(fc="#FFF2CC", ec="#BF9000", tc=TXT)}

    def box(ax, cx, cy, w, h, lines, kind):
        st = S[kind]
        ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                     boxstyle="round,pad=0.02,rounding_size=0.10",
                     fc=st["fc"], ec=st["ec"], lw=1.1))
        n = len(lines)
        for i, (t, b, fs) in enumerate(lines):
            yy = cy + (n - 1) / 2 * 0.52 - i * 0.52
            ax.text(cx, yy, t, ha="center", va="center", family=CJK,
                    fontsize=fs, fontweight=("bold" if b else "normal"),
                    color=st["tc"])

    def arrow(ax, p1, p2, label=None, lpos=None, fs=5.6):
        ax.annotate("", xy=p2, xytext=p1,
                    arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=1.0,
                                    shrinkA=1, shrinkB=1, mutation_scale=8))
        if label:
            lx, ly = lpos
            ax.text(lx, ly, label, ha="center", va="center", family=CJK,
                    fontsize=fs, color="#666666")

    fig, ax = plt.subplots(figsize=(COL_W, 2.20), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0.4, 10)
    ax.axis("off")

    box(ax, 6.0, 9.1, 11.5, 1.0,
        [("上位機　自動化排程 · 安全監控 · 資料紀錄", True, 6.6)], "host")
    box(ax, 2.05, 6.0, 3.7, 1.35,
        [("IT6302 直流電源", True, 5.8), ("充電 CC-CV", False, 5.2)], "inst")
    box(ax, 6.0, 6.0, 3.7, 1.35,
        [("IT8512A+ 電子負載", True, 5.8), ("放電 CC", False, 5.2)], "inst")
    box(ax, 9.95, 6.0, 3.7, 1.35,
        [("STM32 + INA226", True, 5.8), ("嵌入式估測標的", False, 5.2)], "mcu")
    box(ax, 4.05, 2.0, 4.0, 1.3,
        [("DUT 受測電池", True, 6.0), ("鋰離子 2000 mAh", False, 5.2)], "dut")

    arrow(ax, (2.05, 8.60), (2.05, 6.72), "SCPI", (2.70, 7.66))
    arrow(ax, (6.00, 8.60), (6.00, 6.72), "SCPI", (6.65, 7.66))
    arrow(ax, (9.95, 8.60), (9.95, 6.72), "USB", (10.60, 7.66))
    arrow(ax, (2.40, 5.30), (3.35, 2.70), "充電", (2.30, 3.95))
    arrow(ax, (5.60, 5.30), (4.75, 2.70), "放電", (5.75, 3.95))
    arrow(ax, (6.15, 2.10), (8.65, 5.30), "10 mΩ shunt\n量測 V／I", (8.45, 3.20))

    fig.savefig(os.path.join(HERE, "poster_fig1_arch.png"), dpi=300,
                bbox_inches="tight", pad_inches=0.02, facecolor="white")
    plt.close(fig)
    print("saved poster_fig1_arch.png")


# ------------------------------------------------------------ 圖 2 量測域
def gen_zdomain():
    bench = []
    pat = re.compile(r"dV/dI=-([\d.]+) mΩ  \(SoC ([\d.]+)%\)")
    with open(os.path.join(DATA, "round_console_20260707_0113.log"),
              encoding="utf-8", errors="replace") as f:
        for ln in f:
            m = pat.search(ln)
            if m:
                bench.append((float(m.group(2)), float(m.group(1))))

    rows, prev_n = [], None
    with open(os.path.join(DATA, "mcu_soc_log_20260707_011325.log"),
              encoding="utf-8", errors="replace") as f:
        for ln in f:
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
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                t.append(float(r["t_s"]))
                s.append(float(r["soc_cc"]) * 100)
        e0 = datetime.strptime(re.search(r"(\d{8}_\d{6})", path).group(1),
                               "%Y%m%d_%H%M%S").timestamp()
        return e0, t, s

    segs = [load(p) for p in
            sorted(glob.glob(os.path.join(DATA, "round040_cyc18*_discharge_*.csv")))]
    board = []
    for e, z in rows:
        for e0, t, s in segs:
            if e0 <= e <= e0 + t[-1]:
                j = bisect.bisect_right(t, e - e0)
                if 0 < j < len(t):
                    x0, x1, y0, y1 = t[j - 1], t[j], s[j - 1], s[j]
                    board.append((y0 + (y1 - y0) * (e - e0 - x0) / (x1 - x0), z))
                break

    fig, ax = plt.subplots(figsize=(COL_W, 2.05), dpi=300)
    xs = [x / 200 for x in range(0, 20001)]

    def quad(a, b, c):
        return [a * (x / 100) ** 2 + b * (x / 100) + c for x in xs]

    ax.scatter([p[0] for p in bench], [p[1] for p in bench], s=2.0, alpha=0.40,
               color="#1f77b4", edgecolors="none",
               label="台架量測（負載端）", zorder=3)
    ax.scatter([p[0] for p in board], [p[1] for p in board], s=2.0, alpha=0.40,
               color="#d62728", edgecolors="none",
               label="板端量測（電池端子）", zorder=3)
    ax.plot(xs, quad(20.2, -21.6, 63.6), color="#1f77b4", lw=1.1,
            label="台架域擬合", zorder=4)
    ax.plot(xs, quad(18.0, -21.1, 39.6), color="#d62728", lw=1.1,
            label="板端域擬合", zorder=4)

    x_ann = 20.0
    y_top = 20.2 * 0.04 - 21.6 * 0.2 + 63.6
    y_bot = 18.0 * 0.04 - 21.1 * 0.2 + 39.6
    ax.annotate("", xy=(x_ann, y_bot + 0.6), xytext=(x_ann, y_top - 0.6),
                arrowprops=dict(arrowstyle="<->", color="#444444", lw=0.9))
    ax.text(x_ann + 2.0, (y_top + y_bot) / 2,
            "量測域差約 24 mΩ\n（線材／接點電阻）",
            ha="left", va="center", fontsize=6.0, color="#333333")

    ax.set_xlabel("SOC (%)", fontsize=6.8, labelpad=1.5)
    ax.set_ylabel("動態阻抗 |ΔV/ΔI| (mΩ)", fontsize=6.8, labelpad=1.5)
    ax.set_xlim(0, 100)
    ax.set_ylim(25, 82)
    ax.grid(True, lw=0.3, alpha=0.5)
    ax.tick_params(labelsize=6.0, length=2, pad=1.5)
    for s in ax.spines.values():
        s.set_linewidth(0.6)
    ax.legend(loc="upper right", fontsize=5.6, framealpha=0.95,
              handlelength=1.4, borderpad=0.3, labelspacing=0.25,
              handletextpad=0.4)
    fig.tight_layout(pad=0.25)
    fig.savefig(os.path.join(HERE, "poster_fig2_zdomain.png"), facecolor="white")
    plt.close(fig)
    print(f"saved poster_fig2_zdomain.png  台架點={len(bench)} 板端點={len(board)}")


# -------------------------------------------------------------- 圖 3 軌跡
def gen_soc():
    RE_SOC = re.compile(
        r"soc cc=([\d.]+)%\((\d+)cyc\) ekf=([\d.]+)%\((\d+)cyc\)"
        r"(?: z=(?:--\(no event yet\)|([\d.]+)%\(n=(\d+),([\d.]+)mohm,(\d+)cyc\)))?")
    RE_ALIVE = re.compile(r"Ical=(-?[\d.]+)mA")

    soc_rows, alive_rows = [], []
    with open(os.path.join(DATA, "mcu_soc_log_20260707_210836.log"),
              encoding="utf-8", errors="replace") as f:
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

    csvs = sorted(glob.glob(os.path.join(DATA, "round041_cyc*_discharge_*.csv")))
    picks = [(csvs[1], "(a) 1.0C 放電"), (csvs[3], "(b) 2.0C 放電")]

    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, 2.05), dpi=300)
    for (path, title), ax in zip(picks, axes):
        e0, t, soc_true = load_bench(path)
        t_end = t[-1]
        seg = [(e, cc, ekf, z) for e, cc, ekf, z in soc_rows
               if e0 <= e <= e0 + t_end]

        ax.plot([x / 60.0 for x in t], soc_true, color="#222222", lw=1.3,
                label="儀器庫倫（台架真值）", zorder=5)
        ax.plot([(e - e0) / 60.0 for e, *_ in seg], [cc for _, cc, _, _ in seg],
                color="#1f77b4", lw=1.0, ls="--", label="板端庫倫計數", zorder=4)
        ax.plot([(e - e0) / 60.0 for e, *_ in seg], [ekf for _, _, ekf, _ in seg],
                color="#2ca02c", lw=1.0, label="板端 EKF", zorder=6)
        ax.plot([(e - e0) / 60.0 for e, _, _, z in seg if z is not None],
                [z for _, _, _, z in seg if z is not None],
                color="#d62728", lw=0.8, alpha=0.85, label="板端動態阻抗", zorder=3)

        rmse = {}
        for name, idx in (("庫倫", 1), ("EKF", 2), ("阻抗", 3)):
            errs = [row[idx] - interp(t, soc_true, row[0] - e0)
                    for row in seg if row[idx] is not None]
            if errs:
                rmse[name] = math.sqrt(sum(x * x for x in errs) / len(errs))
        txt = "RMSE：" + "、".join(f"{n} {v:.2f}%" if v < 10 else f"{n} {v:.1f}%"
                                  for n, v in rmse.items())
        ax.text(0.03, 0.05, txt, transform=ax.transAxes, fontsize=5.8,
                ha="left", va="bottom", zorder=7,
                bbox=dict(facecolor="white", edgecolor="#999999", lw=0.4,
                          alpha=0.92, pad=1.6))

        ax.set_title(title, fontsize=7.0, pad=3)
        ax.set_xlim(0, math.ceil(t_end / 60.0 / 5.0) * 5)
        ax.set_ylim(-3, 105)
        ax.grid(True, lw=0.3, alpha=0.5)
        ax.tick_params(labelsize=6.0, length=2, pad=1.5)
        ax.set_xlabel("放電時間 (min)", fontsize=6.8, labelpad=1.5)
        ax.set_ylabel("SOC (%)", fontsize=6.8, labelpad=1.5)
        for s in ax.spines.values():
            s.set_linewidth(0.6)
        print(f"  {os.path.basename(path)}: n={len(seg)}  " +
              "  ".join(f"{n}={v:.2f}%" for n, v in rmse.items()))

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, fontsize=6.4,
               frameon=False, bbox_to_anchor=(0.5, 1.015), handlelength=1.8,
               columnspacing=1.6)
    fig.tight_layout(rect=[0, 0, 1, 0.90], pad=0.3, w_pad=1.2)
    fig.savefig(os.path.join(HERE, "poster_fig3_soc.png"), facecolor="white")
    plt.close(fig)
    print("saved poster_fig3_soc.png")


if __name__ == "__main__":
    gen_arch()
    gen_zdomain()
    gen_soc()
