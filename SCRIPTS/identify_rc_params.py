#!/usr/bin/env python3
"""identify_rc_params.py — GITT trace → 一階 RC 參數 (R0, R1, tau1) 辨識。

讀 TEST/gitt_ocv_runner.py 產出的 gitt_trace_*.csv，對每個放電脈衝的
30 min 鬆弛段做一階指數擬合（論文 4.2.4）：

    V(t) = V_eq − A·exp(−t/τ1)          t 自斷載時刻起算

  τ1  ：對數網格搜尋（5–600 s）＋局部細化；A、V_eq 在給定 τ1 下
        有閉式線性最小平方解，不依賴 scipy。
  R1  = A / I                     （極化電阻；脈衝 364 s ≫ τ1，極化已飽和）
  R0  = (V_eq − V_end_loaded − A) / I   （歐姆內阻＝總過電位扣掉極化分量）
  R0_on：接載瞬間跳落 (V_rest_prev_end − V_first_loaded)/I 交叉驗證用，
        含首樣本前 ~2.6 s 的少量極化累積，預期略高於 R0。

輸出：
  TEST/data/rc_params_<ts>.csv   逐步參數表（含擬合 RMSE）
  終端摘要＋建議韌體單值（SOC 中段平均，兩端另列）

用法：
    python3 SCRIPTS/identify_rc_params.py TEST/data/gitt_trace_YYYYMMDD_HHMMSS.csv \
        [--mid-lo 20] [--mid-hi 90]
"""

import argparse
import csv
import math
import os
import sys
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)


def fit_exp_relax(t, v, tau_lo=5.0, tau_hi=600.0, n_grid=240):
    """min Σ (v − (Veq − A e^{−t/τ}))²，回傳 (v_eq, a, tau, rmse)。

    給定 τ 時對 (Veq, A) 是線性 LS（基底 [1, −e^{−t/τ}]）；τ 用對數
    網格掃過後在最優點附近做一次 10× 細網格。"""
    def solve_at(tau):
        e = [math.exp(-x / tau) for x in t]
        n = len(t)
        se, see = sum(e), sum(x * x for x in e)
        sv, sve = sum(v), sum(a * b for a, b in zip(v, e))
        det = n * see - se * se
        if abs(det) < 1e-12:
            return None
        v_eq = (see * sv - se * sve) / det
        a = (se * sv - n * sve) / det
        sse = sum((y - (v_eq - a * ei)) ** 2 for y, ei in zip(v, e))
        return v_eq, a, sse

    def scan(lo, hi, n):
        best = None
        for k in range(n):
            tau = lo * (hi / lo) ** (k / (n - 1))
            r = solve_at(tau)
            if r is None:
                continue
            v_eq, a, sse = r
            if best is None or sse < best[3]:
                best = (v_eq, a, tau, sse)
        return best

    b = scan(tau_lo, tau_hi, n_grid)
    lo = max(tau_lo, b[2] / 1.3)
    hi = min(tau_hi, b[2] * 1.3)
    b2 = scan(lo, hi, n_grid)
    if b2[3] < b[3]:
        b = b2
    v_eq, a, tau, sse = b
    return v_eq, a, tau, math.sqrt(sse / len(t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace_csv")
    ap.add_argument("--mid-lo", type=float, default=20.0,
                    help="韌體單值平均的 SOC 下界（%%）")
    ap.add_argument("--mid-hi", type=float, default=90.0,
                    help="韌體單值平均的 SOC 上界（%%）")
    ap.add_argument("--out", default=None, help="輸出 csv（預設同 trace 目錄）")
    args = ap.parse_args()

    disch = defaultdict(list)   # step -> [(t, v, i)]
    rest = defaultdict(list)    # step -> [(t, v)]
    rest_all = []               # 全部 rest 樣本（含 precharge_rest），查前段末電壓用
    with open(args.trace_csv, newline="") as f:
        for r in csv.DictReader(f):
            note, mode = r["note"], r["mode"]
            t, v = float(r["t_s"]), float(r["v"])
            if mode == "gitt_discharge" and note.startswith("step"):
                disch[int(note[4:])].append((t, v, float(r["i"])))
            elif mode == "gitt_rest_disch" and note.startswith("step"):
                rest[int(note[4:])].append((t, v))
                rest_all.append((t, v))
            elif mode == "gitt_rest_init":
                rest_all.append((t, v))

    steps = sorted(set(disch) & set(rest))
    if not steps:
        sys.exit("trace 內找不到成對的 discharge/rest 步")

    rows = []
    for s in steps:
        d = sorted(disch[s])
        rr = sorted(rest[s])
        i_mean = sum(x[2] for x in d) / len(d)
        t_end_loaded, v_end_loaded = d[-1][0], d[-1][1]
        # 斷載時刻 ≈ 末負載樣本 + 半個取樣間隔（取樣 ~2.6 s）
        t0 = t_end_loaded + 1.3
        t_rel = [x[0] - t0 for x in rr]
        v_rest = [x[1] for x in rr]
        v_eq, a, tau, rmse = fit_exp_relax(t_rel, v_rest)

        r1 = a / i_mean
        r0 = (v_eq - v_end_loaded - a) / i_mean
        # 接載瞬跳交叉驗證：前一段 rest 的最後樣本（時間上最接近接載且 < 首負載樣本）
        t_first, v_first = d[0][0], d[0][1]
        prev = [p for p in rest_all if p[0] < t_first - 0.5]
        r0_on = (prev[-1][1] - v_first) / i_mean if prev else float("nan")

        # 此步鬆弛終點對應的 SOC（庫倫，滿電 100% 起算，5% 步）
        soc_pct = 100.0 - 5.0 * s
        rows.append({
            "step": s, "soc_pct": soc_pct, "i_A": i_mean,
            "v_end_loaded": v_end_loaded, "v_eq_fit": v_eq,
            "r0_mohm": r0 * 1e3, "r1_mohm": r1 * 1e3, "tau1_s": tau,
            "r0_on_mohm": r0_on * 1e3, "fit_rmse_mv": rmse * 1e3,
        })

    out = args.out or os.path.join(
        os.path.dirname(os.path.abspath(args.trace_csv)),
        os.path.basename(args.trace_csv).replace("gitt_trace", "rc_params"))
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v)
                        for k, v in r.items()})

    hdr = ("step  SOC%   I(A)    R0(mΩ)  R1(mΩ)  τ1(s)   R0_on(mΩ)  "
           "fitRMSE(mV)")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['step']:>4}  {r['soc_pct']:5.1f}  {r['i_A']:.4f} "
              f"{r['r0_mohm']:8.2f} {r['r1_mohm']:7.2f} {r['tau1_s']:7.1f} "
              f"{r['r0_on_mohm']:9.2f} {r['fit_rmse_mv']:10.3f}")

    mid = [r for r in rows if args.mid_lo <= r["soc_pct"] <= args.mid_hi]
    if mid:
        n = len(mid)
        avg = {k: sum(r[k] for r in mid) / n
               for k in ("r0_mohm", "r1_mohm", "tau1_s")}
        print(f"\n[firmware] SOC {args.mid_lo:.0f}–{args.mid_hi:.0f}% "
              f"中段平均（n={n}）：")
        print(f"  SOC_EKF_R0_OHM   {avg['r0_mohm']/1e3:.4f}f")
        print(f"  SOC_EKF_R1_OHM   {avg['r1_mohm']/1e3:.4f}f")
        print(f"  SOC_EKF_TAU1_S   {avg['tau1_s']:.1f}f")
    print(f"\n[done] 逐步參數表 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
