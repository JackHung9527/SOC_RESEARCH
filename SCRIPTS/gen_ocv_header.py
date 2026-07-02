#!/usr/bin/env python3
"""gen_ocv_header.py — GITT ocv_table_*.csv → 韌體 OCV 表頭檔回填。

讀 TEST/gitt_ocv_runner.py 產出的 ocv_table_*.csv
（欄位：soc_pct, v_discharge, v_charge, v_pseudo_ocv），
依論文 4.2.2／4.2.4 之處理：先內插至 1% 細網格、移動平均平滑
（使分段線性斜率／雅可比連續性足夠），再重取等距節點，
覆寫 soc_ekf_ocv_table.h 的 OCV_TABLE marker 區間。

用法：
    python3 SCRIPTS/gen_ocv_header.py TEST/data/ocv_table_YYYYMMDD_HHMMSS.csv \
        [--col v_pseudo_ocv] [--step 5] [--smooth 5] \
        [--out MCU/soc_research_mcu/USER_CODE/soc_ekf/soc_ekf_ocv_table.h]
"""

import argparse
import csv
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_OUT = os.path.join(ROOT, "MCU", "soc_research_mcu",
                           "USER_CODE", "soc_ekf", "soc_ekf_ocv_table.h")

MARK_BEGIN = "/* === OCV_TABLE BEGIN"
MARK_END = "/* === OCV_TABLE END === */"


def lerp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", help="ocv_table_*.csv（GITT 產出）")
    ap.add_argument("--col", default="v_pseudo_ocv",
                    choices=["v_pseudo_ocv", "v_discharge", "v_charge"])
    ap.add_argument("--step", type=int, default=5, help="輸出節點間距（%%SOC）")
    ap.add_argument("--smooth", type=int, default=5,
                    help="1%% 細網格上的移動平均窗（點數，奇數；0=不平滑）")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    with open(args.csv_path, newline="", encoding="utf-8") as f:
        rows = sorted(
            ((float(r["soc_pct"]), float(r[args.col])) for r in csv.DictReader(f)),
            key=lambda p: p[0])
    if len(rows) < 3:
        sys.exit("csv 內有效點不足（<3）")
    soc_raw = [p[0] for p in rows]
    v_raw = [p[1] for p in rows]

    # 1% 細網格內插 + 移動平均平滑（4.2.2：使雅可比連續）
    fine_x = list(range(0, 101))
    fine_v = [lerp(soc_raw, v_raw, x) for x in fine_x]
    if args.smooth >= 3:
        h = args.smooth // 2
        fine_v = [
            sum(fine_v[max(0, i - h):min(len(fine_v), i + h + 1)])
            / len(fine_v[max(0, i - h):min(len(fine_v), i + h + 1)])
            for i in range(len(fine_v))
        ]

    # 重取等距節點
    nodes = list(range(0, 101, args.step))
    if nodes[-1] != 100:
        nodes.append(100)
    node_v = [fine_v[n] for n in nodes]

    n = len(nodes)
    soc_lines = _fmt_array([x / 100.0 for x in nodes])
    v_lines = _fmt_array(node_v)
    src = os.path.basename(args.csv_path)
    block = (
        f"{MARK_BEGIN} (auto-generated region; gen_ocv_header.py 覆寫) === */\n"
        f"/* source: {src}  col={args.col}  step={args.step}%  smooth={args.smooth} */\n"
        f"#define SOC_EKF_OCV_N  {n}U\n"
        "\n"
        f"/* SOC 節點（0..1 分數，等距 {args.step}%） */\n"
        f"static const float SOC_EKF_OCV_SOC[SOC_EKF_OCV_N] =\n"
        "{\n" + soc_lines + "\n};\n"
        "\n"
        f"/* V_OC（V）— GITT 實測（{src}） */\n"
        f"static const float SOC_EKF_OCV_V[SOC_EKF_OCV_N] =\n"
        "{\n" + v_lines + "\n};\n"
        f"{MARK_END}"
    )

    with open(args.out, encoding="utf-8") as f:
        content = f.read()
    b = content.find(MARK_BEGIN)
    e = content.find(MARK_END)
    if b < 0 or e < 0:
        sys.exit(f"{args.out} 找不到 OCV_TABLE marker")
    content = content[:b] + block + content[e + len(MARK_END):]
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[done] {n} 點 OCV 表已寫入 {args.out}（source={src}）")
    print("[next] 重新編譯並重跑 SCRIPTS/footprint_report.py 以更新 EKF footprint。")
    return 0


def _fmt_array(vals, per_line=10):
    out = []
    for i in range(0, len(vals), per_line):
        chunk = ", ".join(f"{v:.4f}f" for v in vals[i:i + per_line])
        tail = "," if i + per_line < len(vals) else ""
        out.append("    " + chunk + tail)
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
