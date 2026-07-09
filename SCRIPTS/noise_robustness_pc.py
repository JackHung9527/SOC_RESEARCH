#!/usr/bin/env python3
"""noise_robustness_pc.py — 表 4-5「噪聲下 SOC 抖動」之 PC 端壓力測試。

資料：Round 41 cyc189（0.5C 放電）之 MCU log alive 行（V/Ical @1 Hz，
電池端子量測域，與韌體參數同域）。

方法：對 V、I 逐樣本注入 iid 高斯噪聲，等級：
    L1「INA226 級」   σ_I=5 mA,  σ_V=2 mV
    L2「10× 退化」    σ_I=20 mA, σ_V=10 mV
    L3「劣質感測」    σ_I=50 mA, σ_V=20 mV
每級 N_SEED 個亂數種子。三法之 PC 鏡射（庫倫直接積分、EKF 沿用
ekf_pc_replay.FwEkf、動態阻抗依 soc_zdyn.c 逐行移植，參數 parse 韌體標頭）。

指標：各法輸出相對「同一資料、無噪聲」基準軌跡之
    jitter RMS、max |dev|、（庫倫另計）終點漂移
——與自身乾淨軌跡比較，將噪聲敏感度自模型誤差中隔離。

用法：python3 SCRIPTS/noise_robustness_pc.py
"""

import csv
import math
import os
import random
import re
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

from ekf_pc_replay import FwEkf, parse_defines, parse_ocv_table, MODEL_SET, OCV_HDR  # noqa: E402

MCU_LOG = os.path.join(ROOT, "TEST", "data", "mcu_soc_log_20260707_210836.log")
BENCH_CSV = os.path.join(ROOT, "TEST", "data",
                         "round041_cyc189_discharge_0.5C_20260707_234604.csv")
N_SEED = 10
LEVELS = [("L1 INA226級", 5.0, 2.0), ("L2 10×退化", 20.0, 10.0),
          ("L3 劣質感測", 50.0, 20.0)]


class PcZdyn:
    """soc_zdyn.c 之逐行鏡射（板端域係數；含放電向過濾）。"""

    def __init__(self, p):
        self.a = p["SOC_ZDYN_COEF_A_MOHM"]
        self.b = p["SOC_ZDYN_COEF_B_MOHM"]
        self.c = p["SOC_ZDYN_COEF_C_MOHM"]
        self.cap = p["SOC_ZDYN_CAPACITY_MAH"]
        self.di_min = p["SOC_ZDYN_DI_MIN_MA"]
        self.di_max = p["SOC_ZDYN_DI_MAX_MA"]
        self.z_max = p["SOC_ZDYN_Z_MAX_MOHM"]
        self.i_floor = p["SOC_ZDYN_I_FLOOR_MA"]
        self.prev_valid = False
        self.prev_i = self.prev_v = 0.0
        self.anchored = False
        self.soc_anchor = 0.0
        self.q_out = 0.0
        self.prev_z_valid = False
        self.prev_z = 0.0

    def soc_now(self):
        if not self.anchored:
            return -1.0
        return min(max(self.soc_anchor - self.q_out / (self.cap * 3600.0), 0.0), 1.0)

    def _solve(self, z, i_ma):
        vert = -self.b / (2.0 * self.a)
        disc = self.b * self.b - 4.0 * self.a * (self.c - z)
        if disc <= 0.0:
            return min(max(vert, 0.0), 1.0)
        sq = math.sqrt(disc)
        s_lo = min(max((-self.b - sq) / (2.0 * self.a), 0.0), 1.0)
        s_hi = min(max((-self.b + sq) / (2.0 * self.a), 0.0), 1.0)
        if self.anchored:
            now = self.soc_now()
            return s_lo if abs(s_lo - now) <= abs(s_hi - now) else s_hi
        if self.prev_z_valid:
            below = (i_ma > 0) == (z > self.prev_z)
            return s_lo if below else s_hi
        return s_hi

    def update(self, i_ma, v_mv):
        if self.anchored:
            self.q_out += i_ma
        if self.prev_valid:
            di = i_ma - self.prev_i
            adi = abs(di)
            in_domain = i_ma > self.i_floor and self.prev_i > self.i_floor
            if in_domain and self.di_min <= adi <= self.di_max:
                z = abs((v_mv - self.prev_v) / di) * 1000.0
                if z <= self.z_max:
                    self.soc_anchor = self._solve(z, i_ma)
                    self.q_out = 0.0
                    self.anchored = True
                    self.prev_z = z
                    self.prev_z_valid = True
        self.prev_i, self.prev_v, self.prev_valid = i_ma, v_mv, True


def load_samples():
    """cyc189 放電窗之 (v_mv, i_ma) @1Hz。"""
    m = re.search(r"(\d{8}_\d{6})", os.path.basename(BENCH_CSV))
    e0 = datetime.strptime(m.group(1), "%Y%m%d_%H%M%S").timestamp()
    t_end = max(float(r["t_s"]) for r in csv.DictReader(open(BENCH_CSV)))
    out = []
    for ln in open(MCU_LOG):
        p = ln.split("\t", 3)
        if len(p) < 4 or p[2] != "mcu":
            continue
        mm = re.search(r"alive V=([\d.]+)mV I=(-?[\d.]+)mA Ical=(-?[\d.]+)mA", p[3])
        if mm and e0 <= float(p[0]) <= e0 + t_end:
            out.append((float(mm.group(1)), float(mm.group(3))))
    return out


def run_all(samples, p, ocv_soc, ocv_v, rng=None, si=0.0, sv=0.0):
    """回傳三法逐秒輸出（%SOC；zdyn 未錨定前為 None）。"""
    cap_uas = p["SOC_EKF_CAPACITY_MAH"] * 3600.0 * 1000.0  # 與庫倫同容量
    q_out_uas = 0.0
    ekf = FwEkf(p, ocv_soc, ocv_v)
    ekf.reset(100.0)
    zd = PcZdyn(p)
    cc_tr, ekf_tr, z_tr = [], [], []
    for v_mv, i_ma in samples:
        if rng is not None:
            i_ma = i_ma + rng.gauss(0.0, si)
            v_mv = v_mv + rng.gauss(0.0, sv)
        q_out_uas += i_ma * 1000.0
        cc = min(max(100.0 * (1.0 - q_out_uas / cap_uas / 1.0), 0.0), 100.0)
        ekf.update(i_ma, v_mv, 1.0)
        zd.update(i_ma, v_mv)
        cc_tr.append(cc)
        ekf_tr.append(ekf.soc * 100.0)
        s = zd.soc_now()
        z_tr.append(s * 100.0 if s >= 0.0 else None)
    return cc_tr, ekf_tr, z_tr


def dev_stats(noisy, clean):
    d = [a - b for a, b in zip(noisy, clean) if a is not None and b is not None]
    rms = math.sqrt(sum(x * x for x in d) / len(d))
    return rms, max(abs(x) for x in d), d[-1]


def main():
    names = ["SOC_EKF_CAPACITY_MAH", "SOC_EKF_SOC0_PCT", "SOC_EKF_R0_OHM",
             "SOC_EKF_R1_OHM", "SOC_EKF_TAU1_S", "SOC_EKF_Q_SOC",
             "SOC_EKF_Q_V1", "SOC_EKF_R_MEAS_V2", "SOC_EKF_P0_SOC",
             "SOC_EKF_P0_V1",
             "SOC_ZDYN_COEF_A_MOHM", "SOC_ZDYN_COEF_B_MOHM",
             "SOC_ZDYN_COEF_C_MOHM", "SOC_ZDYN_CAPACITY_MAH",
             "SOC_ZDYN_DI_MIN_MA", "SOC_ZDYN_DI_MAX_MA",
             "SOC_ZDYN_Z_MAX_MOHM", "SOC_ZDYN_I_FLOOR_MA"]
    p = parse_defines(MODEL_SET, names)
    ocv_soc, ocv_v = parse_ocv_table(OCV_HDR)
    samples = load_samples()
    print(f"[data] cyc189 放電窗 {len(samples)} 樣本 @1Hz  "
          f"(σ 註記格式: σ_I mA / σ_V mV)\n")

    clean = run_all(samples, p, ocv_soc, ocv_v)

    hdr = (f"{'噪聲等級':<14} {'法':<4} {'jitter RMS%':>11} "
           f"{'max|dev|%':>10} {'終點漂移%':>9}")
    print(hdr)
    print("-" * len(hdr))
    for tag, si, sv in LEVELS:
        acc = {k: [] for k in ("cc", "ekf", "z")}
        for seed in range(N_SEED):
            rng = random.Random(1000 + seed)
            noisy = run_all(samples, p, ocv_soc, ocv_v, rng, si, sv)
            for k, n_tr, c_tr in (("cc", noisy[0], clean[0]),
                                  ("ekf", noisy[1], clean[1]),
                                  ("z", noisy[2], clean[2])):
                acc[k].append(dev_stats(n_tr, c_tr))
        for k in ("cc", "ekf", "z"):
            rms = sum(a[0] for a in acc[k]) / N_SEED
            mx = max(a[1] for a in acc[k])
            drift = sum(abs(a[2]) for a in acc[k]) / N_SEED
            print(f"{tag:<14} {k:<4} {rms:11.3f} {mx:10.2f} {drift:9.3f}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
