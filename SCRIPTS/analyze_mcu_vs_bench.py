#!/usr/bin/env python3
"""analyze_mcu_vs_bench.py — 板端三法 SOC vs 台架庫倫真值（表 4-4／表 4-6）。

輸入：
  - 台架放電 CSV（round_runner 產出，t_s 相對秒、soc_cc 為台架庫倫真值 0..1）
  - MCU UART log（mcu_uart_logger 產出，每行前綴 Pi epoch）

對齊：CSV 檔名時間戳（step 開始）＋ t_s → epoch；再用 MCU 端電流階躍邊緣
（|Ical| 首次 > 0.4×I_step）交叉校正，偏差 >5 s 時採邊緣對齊並警告。

輸出：
  - 各放電 cycle × 三法的 RMSE／max|err|／bias（%SOC）
  - 動態阻抗事件更新的 cycle 數統計（表 4-6 末格）

用法：
    python3 SCRIPTS/analyze_mcu_vs_bench.py TEST/data/mcu_soc_log_*.log \
        TEST/data/round040_cyc*_discharge_*.csv
"""

import csv
import math
import os
import re
import sys
from datetime import datetime

RE_SOC = re.compile(
    r"soc cc=([\d.]+)%\((\d+)cyc\) ekf=([\d.]+)%\((\d+)cyc\)"
    r"(?: z=(?:--\(no event yet\)|([\d.]+)%\(n=(\d+),([\d.]+)mohm,(\d+)cyc\)))?")
RE_ALIVE = re.compile(r"Ical=(-?[\d.]+)mA")
RE_FNAME_TS = re.compile(r"(\d{8}_\d{6})\.csv$")


def load_mcu_log(path):
    """回傳 soc_rows=[(epoch, cc, ekf, z|None, z_n|None, z_cyc|None)]、
    alive_rows=[(epoch, i_ma)]。"""
    soc_rows, alive_rows = [], []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            parts = ln.rstrip("\n").split("\t", 3)
            if len(parts) < 4 or parts[2] != "mcu":
                continue
            epoch, text = float(parts[0]), parts[3]
            m = RE_SOC.search(text)
            if m:
                z = float(m.group(5)) if m.group(5) else None
                zn = int(m.group(6)) if m.group(6) else None
                zc = int(m.group(8)) if m.group(8) else None
                soc_rows.append((epoch, float(m.group(1)), float(m.group(3)),
                                 z, zn, zc))
                continue
            m = RE_ALIVE.search(text)
            if m:
                alive_rows.append((epoch, float(m.group(1))))
    return soc_rows, alive_rows


def load_bench_csv(path):
    t, soc = [], []
    i_a = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            t.append(float(r["t_s"]))
            soc.append(float(r["soc_cc"]) * 100.0)
            i_a.append(float(r["i"]))
    m = RE_FNAME_TS.search(os.path.basename(path))
    epoch0 = datetime.strptime(m.group(1), "%Y%m%d_%H%M%S").timestamp()
    return epoch0, t, soc, i_a


def refine_epoch0(epoch0, i_step_a, alive_rows, window_s=90.0):
    """MCU 端 |Ical| 首次超過 0.4×I_step 的時刻當放電起點。"""
    thr = 0.4 * i_step_a * 1000.0
    cand = [e for e, i_ma in alive_rows
            if abs(e - epoch0) <= window_s and i_ma > thr]
    if not cand:
        return epoch0, 0.0
    return min(cand), min(cand) - epoch0


def interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    import bisect
    j = bisect.bisect_right(xs, x)
    x0, x1, y0, y1 = xs[j - 1], xs[j], ys[j - 1], ys[j]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    mcu_log = sys.argv[1]
    csvs = sorted(sys.argv[2:])

    soc_rows, alive_rows = load_mcu_log(mcu_log)
    print(f"[mcu] {len(soc_rows)} soc lines / {len(alive_rows)} alive lines\n")

    hdr = (f"{'cycle':<34} {'法':<4} {'RMSE%':>7} {'max|e|%':>8} "
           f"{'bias%':>7} {'n':>6}")
    print(hdr)
    print("-" * len(hdr))

    all_zcyc_event = []
    all_zcyc_idle = []
    prev_n = None
    for e, cc, ekf, z, zn, zc in soc_rows:
        if zn is not None and zc is not None:
            if prev_n is not None and zn > prev_n:
                all_zcyc_event.append(zc)
            elif prev_n is not None and zn == prev_n:
                all_zcyc_idle.append(zc)
            prev_n = zn

    for path in csvs:
        epoch0, t, soc_true, i_a = load_bench_csv(path)
        i_step = max(i_a)
        epoch0r, shift = refine_epoch0(epoch0, i_step, alive_rows)
        tag = ""
        if abs(shift) > 5.0:
            tag = f"  (!edge shift {shift:+.1f}s)"
            epoch0 = epoch0r
        t_end = t[-1]

        seg = [(e, cc, ekf, z) for e, cc, ekf, z, _, _ in soc_rows
               if epoch0 <= e <= epoch0 + t_end]
        name = os.path.basename(path).replace(".csv", "")
        stats = {}
        for law, idx in (("cc", 1), ("ekf", 2), ("z", 3)):
            errs = []
            for row in seg:
                est = row[idx]
                if est is None:
                    continue
                tru = interp(t, soc_true, row[0] - epoch0)
                errs.append(est - tru)
            if errs:
                rmse = math.sqrt(sum(x * x for x in errs) / len(errs))
                stats[law] = (rmse, max(abs(x) for x in errs),
                              sum(errs) / len(errs), len(errs))
        short = re.sub(r"round\d+_|_2026\d+_\d+", "", name)
        for law in ("cc", "ekf", "z"):
            if law in stats:
                r, mx, b, n = stats[law]
                print(f"{short:<34} {law:<4} {r:7.2f} {mx:8.2f} "
                      f"{b:+7.2f} {n:6d}{tag}")
                tag = ""
        print()

    def pstats(v):
        v = sorted(v)
        return (f"n={len(v)}  min={v[0]}  median={v[len(v)//2]}  "
                f"p95={v[int(len(v)*0.95)]}  max={v[-1]}")

    print("[表4-6] 動態阻抗 update cycle 數（全輪統計）")
    if all_zcyc_idle:
        print(f"  無事件（庫倫內插）: {pstats(all_zcyc_idle)}")
    if all_zcyc_event:
        print(f"  有事件（二次反解）: {pstats(all_zcyc_event)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
