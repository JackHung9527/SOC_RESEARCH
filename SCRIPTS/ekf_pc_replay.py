#!/usr/bin/env python3
"""ekf_pc_replay.py — 韌體 EKF 之 PC 重放驗證與 Q/R 初調（論文 4.2.5 前置）。

逐行鏡射 MCU/soc_research_mcu/USER_CODE/soc_ekf/soc_ekf.c 的方程式
（ZOH 離散化、純量增益、Joseph form、分段線性 OCV），參數與 OCV 表
直接以 regex 讀 model_set.h / soc_ekf_ocv_table.h，確保 PC 與韌體一致。
唯一差異：trace 取樣非等距（放電 ~2.6 s、鬆弛 ~5.8 s），重放按實際 dt
重算 a22/b2；韌體上線後為固定 1 Hz，不受影響。

情境：
  A) 正確初值（SOC=100%）      → 穩態追蹤 RMSE
  B) 錯誤初值（SOC=50%）       → 收斂時間（進入 ±3% 帶並不再離開）＋收斂後 RMSE
  C) 電壓 seed（首筆 V 反查）  → 同 A 指標

真值：trace 之 soc_cc 欄（台架 INA226 庫倫計數，論文 4.0 之 ground truth）。

用法：
    python3 SCRIPTS/ekf_pc_replay.py TEST/data/gitt_trace_YYYYMMDD_HHMMSS.csv \
        [--grid]     # 掃 Q/R 網格；預設只跑 model_set.h 現值
"""

import argparse
import csv
import math
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
MODEL_SET = os.path.join(ROOT, "MCU", "soc_research_mcu", "USER_CODE",
                         "model_set.h")
OCV_HDR = os.path.join(ROOT, "MCU", "soc_research_mcu", "USER_CODE",
                       "soc_ekf", "soc_ekf_ocv_table.h")


def parse_defines(path, names):
    txt = open(path, encoding="utf-8").read()
    out = {}
    for n in names:
        m = re.search(rf"#define\s+{n}\s+([-\d.eE+]+)f?", txt)
        if not m:
            sys.exit(f"{path}: 找不到 #define {n}")
        out[n] = float(m.group(1))
    return out


def parse_ocv_table(path):
    txt = open(path, encoding="utf-8").read()
    arrays = re.findall(r"=\s*\{([^}]*)\}", txt)
    if len(arrays) < 2:
        sys.exit(f"{path}: 解析不到兩個陣列")
    soc = [float(x) for x in re.findall(r"([\d.]+)f", arrays[0])]
    v = [float(x) for x in re.findall(r"([\d.]+)f", arrays[1])]
    assert len(soc) == len(v) and len(soc) >= 3
    return soc, v


class FwEkf:
    """soc_ekf.c 的逐行鏡射（變數名對應 s_*）。"""

    def __init__(self, p, ocv_soc, ocv_v):
        self.p = p
        self.ocv_soc, self.ocv_v = ocv_soc, ocv_v
        self.cap_as = p["SOC_EKF_CAPACITY_MAH"] * 3.6
        self.reset(p["SOC_EKF_SOC0_PCT"])

    def reset(self, soc0_pct):
        self.soc = soc0_pct / 100.0
        self.v1 = 0.0
        self.p00 = self.p["SOC_EKF_P0_SOC"]
        self.p01 = 0.0
        self.p11 = self.p["SOC_EKF_P0_V1"]

    def seed_from_voltage(self, v_mv):
        v = v_mv * 1e-3
        tv, ts = self.ocv_v, self.ocv_soc
        if v <= tv[0]:
            self.soc = ts[0]
        elif v >= tv[-1]:
            self.soc = ts[-1]
        else:
            i = 0
            while tv[i + 1] < v:
                i += 1
            self.soc = ts[i] + (ts[i + 1] - ts[i]) * (v - tv[i]) / (tv[i + 1] - tv[i])
        self.v1 = 0.0
        self.p00 = self.p["SOC_EKF_P0_SOC"]
        self.p01 = 0.0
        self.p11 = self.p["SOC_EKF_P0_V1"]

    def ocv_lookup(self, soc):
        ts, tv = self.ocv_soc, self.ocv_v
        if soc <= ts[0]:
            i = 0
        elif soc >= ts[-1]:
            i = len(ts) - 2
        else:
            i = 0
            while ts[i + 1] < soc:
                i += 1
        k = (tv[i + 1] - tv[i]) / (ts[i + 1] - ts[i])
        return tv[i] + k * (soc - ts[i]), k

    def update(self, i_ma, v_mv, dt, q_soc=None, r_meas=None):
        p = self.p
        q_soc = p["SOC_EKF_Q_SOC"] if q_soc is None else q_soc
        r_meas = p["SOC_EKF_R_MEAS_V2"] if r_meas is None else r_meas
        a22 = math.exp(-dt / p["SOC_EKF_TAU1_S"])
        b2 = p["SOC_EKF_R1_OHM"] * (1.0 - a22)
        i_a, v_t = i_ma * 1e-3, v_mv * 1e-3

        # 時間更新
        self.soc -= (dt / self.cap_as) * i_a
        self.v1 = a22 * self.v1 + b2 * i_a
        self.p01 = a22 * self.p01
        self.p11 = a22 * a22 * self.p11 + p["SOC_EKF_Q_V1"] * dt
        self.p00 = self.p00 + q_soc * dt

        # 量測更新（純量增益）
        voc, dvoc = self.ocv_lookup(self.soc)
        e = v_t - (voc - i_a * p["SOC_EKF_R0_OHM"] - self.v1)
        pc0 = dvoc * self.p00 - self.p01
        pc1 = dvoc * self.p01 - self.p11
        s = dvoc * pc0 - pc1 + r_meas
        k0, k1 = pc0 / s, pc1 / s
        self.soc += k0 * e
        self.v1 += k1 * e

        # Joseph form
        m00, m01 = 1.0 - k0 * dvoc, k0
        m10, m11 = -(k1 * dvoc), 1.0 + k1
        t00 = m00 * self.p00 + m01 * self.p01
        t01 = m00 * self.p01 + m01 * self.p11
        t10 = m10 * self.p00 + m11 * self.p01
        t11 = m10 * self.p01 + m11 * self.p11
        self.p00 = t00 * m00 + t01 * m01 + k0 * k0 * r_meas
        self.p01 = t10 * m00 + t11 * m01 + k0 * k1 * r_meas
        self.p11 = t10 * m10 + t11 * m11 + k1 * k1 * r_meas

        self.soc = min(max(self.soc, 0.0), 1.0)
        self.v1 = min(max(self.v1, -0.5), 0.5)


def load_trace(path, cap_mah=1665.0):   # 實測容量（active_profile.json）
    """回傳 GITT 主段樣本 [(t, v_mV, i_mA, soc_true_pct)]（放電為正）。

    真值不用 trace 的 soc_cc 欄（runner 只在鬆弛列填值、放電列為 0），
    改以電流梯形積分自建連續庫倫 SOC（自滿電 100% 起算，與 runner 的
    q 積分同源，即論文 4.0 之 ground truth 定義）。"""
    raw = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["mode"] not in ("gitt_discharge", "gitt_rest_disch"):
                continue
            raw.append((float(r["t_s"]), float(r["v"]) * 1e3,
                        float(r["i"]) * 1e3))
    raw.sort()
    rows = []
    q_mah = 0.0
    for k, (t, v, i) in enumerate(raw):
        if k > 0:
            t0, _, i0 = raw[k - 1]
            dt = t - t0
            if dt < 30.0:                       # 段間長空隙不積分（I=0）
                q_mah += 0.5 * (i + i0) * dt / 3600.0
        rows.append((t, v, i, 100.0 * (1.0 - q_mah / cap_mah)))
    return rows


def replay(ekf, rows, q_soc=None, r_meas=None, seed=None, seed_v=False):
    if seed_v:
        ekf.seed_from_voltage(rows[0][1])
    elif seed is not None:
        ekf.reset(seed)
    t_prev = None
    out = []
    for t, v_mv, i_ma, soc_true in rows:
        dt = min(max(t - t_prev, 0.5), 30.0) if t_prev is not None else 1.0
        t_prev = t
        ekf.update(i_ma, v_mv, dt, q_soc, r_meas)
        out.append((t, ekf.soc * 100.0, soc_true))
    return out


def metrics(out, settle_band_pct=3.0, skip_s=600.0):
    t0 = out[0][0]
    err = [(t, est - tru) for t, est, tru in out]
    conv_t = None                      # 進帶後不再離開的時刻
    for i in range(len(err)):
        if abs(err[i][1]) <= settle_band_pct:
            if all(abs(e) <= settle_band_pct for _, e in err[i:]):
                conv_t = err[i][0] - t0
                break
    tail = [e for t, e in err if t - t0 >= skip_s]
    rmse = math.sqrt(sum(e * e for e in tail) / len(tail))
    maxe = max(abs(e) for e in tail)
    return rmse, maxe, conv_t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace_csv")
    ap.add_argument("--grid", action="store_true", help="掃 Q_SOC × R_MEAS 網格")
    args = ap.parse_args()

    names = ["SOC_EKF_CAPACITY_MAH", "SOC_EKF_SOC0_PCT", "SOC_EKF_R0_OHM",
             "SOC_EKF_R1_OHM", "SOC_EKF_TAU1_S", "SOC_EKF_Q_SOC",
             "SOC_EKF_Q_V1", "SOC_EKF_R_MEAS_V2", "SOC_EKF_P0_SOC",
             "SOC_EKF_P0_V1"]
    p = parse_defines(MODEL_SET, names)
    ocv_soc, ocv_v = parse_ocv_table(OCV_HDR)
    rows = load_trace(args.trace_csv)
    print(f"[replay] {len(rows)} 樣本  "
          f"span {rows[0][0]:.0f}–{rows[-1][0]:.0f} s  "
          f"(R0={p['SOC_EKF_R0_OHM']*1e3:.1f}mΩ R1={p['SOC_EKF_R1_OHM']*1e3:.1f}mΩ "
          f"τ1={p['SOC_EKF_TAU1_S']:.0f}s)")

    def run_all(q, r, tag):
        ekf = FwEkf(p, ocv_soc, ocv_v)
        a = metrics(replay(ekf, rows, q, r, seed=100.0))
        b = metrics(replay(ekf, rows, q, r, seed=50.0))
        c = metrics(replay(ekf, rows, q, r, seed_v=True))
        conv = f"{b[2]:.0f}s" if b[2] is not None else "不收斂"
        print(f"  {tag:<28} A:RMSE={a[0]:5.2f}% max={a[1]:5.2f}%   "
              f"B(50%起):conv={conv:>7} RMSE={b[0]:5.2f}%   "
              f"C(V-seed):RMSE={c[0]:5.2f}%")
        return a, b, c

    print("\n[現值 model_set.h]")
    run_all(None, None,
            f"Q={p['SOC_EKF_Q_SOC']:.0e} R={p['SOC_EKF_R_MEAS_V2']:.0e}")

    if args.grid:
        print("\n[Q/R 網格]  （RMSE 取 t>600s；收斂帶 ±3%）")
        for q in (1e-9, 1e-8, 1e-7, 1e-6):
            for r in ((0.005) ** 2, (0.010) ** 2, (0.020) ** 2):
                run_all(q, r, f"Q={q:.0e} R=({math.sqrt(r)*1e3:.0f}mV)²")
    return 0


if __name__ == "__main__":
    sys.exit(main())
