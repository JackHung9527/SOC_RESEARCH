#!/usr/bin/env python3
"""footprint_report.py — 論文 4.4.3 三法嵌入式資源佔用量測（Flash / RAM）。

量測方式（與論文 4.4.3 敘述一致）：比較「只有共用骨架」與「骨架＋單一方法」
兩種建置的容量差。方法開關走 model_set.h 的 SOC_*_ENABLE（#ifndef 包裝），
由 make EXTRA_CFLAGS=-D... 覆寫，不動任何原始碼。

變體：
    base     三法全關（共用骨架，含 perf_cyc 量測儀器）
    coulomb  骨架＋庫倫計數
    ekf      骨架＋EKF（含 OCV 表）
    zdyn     骨架＋動態阻抗
    full     三法全開（最後建置，順便還原 BUILD/ 發佈物）

Flash = text + data（載入映像）；RAM = data + bss。
「每次更新 CPU cycles」不在本腳本範圍——由韌體 1 Hz soc 狀態行的
(NNNcyc) 欄位實測（perf_cyc 模組，SysTick 換算）。

用法（在 firmware-project root 或任意處執行）：
    python3 SCRIPTS/footprint_report.py [--out MCU/docs/footprint_YYYYMMDD.md]
"""

import argparse
import datetime
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
PROJ = os.path.join(ROOT, "MCU", "soc_research_mcu")
ELF = os.path.join(PROJ, "build", "soc_research_mcu.elf")

FLAGS = ("SOC_COULOMB_ENABLE", "SOC_EKF_ENABLE", "SOC_ZDYN_ENABLE")

# (變體名, (coulomb, ekf, zdyn))
VARIANTS = [
    ("base",    (0, 0, 0)),
    ("coulomb", (1, 0, 0)),
    ("ekf",     (0, 1, 0)),
    ("zdyn",    (0, 0, 1)),
    ("full",    (1, 1, 1)),   # 最後跑：還原 BUILD/ 發佈物為全功能版
]


def build_variant(enables):
    extra = " ".join(f"-D{f}={v}" for f, v in zip(FLAGS, enables))
    subprocess.run(["make", "clean"], cwd=PROJ, check=True,
                   stdout=subprocess.DEVNULL)
    jobs = str(max(1, (os.cpu_count() or 2) - 1))
    subprocess.run(["make", f"-j{jobs}", f"EXTRA_CFLAGS={extra}"],
                   cwd=PROJ, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    out = subprocess.run(["arm-none-eabi-size", ELF], check=True,
                         capture_output=True, text=True).stdout
    m = re.search(r"^\s*(\d+)\s+(\d+)\s+(\d+)", out, re.M)
    text, data, bss = (int(x) for x in m.groups())
    return {"text": text, "data": data, "bss": bss,
            "flash": text + data, "ram": data + bss}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="輸出 markdown 路徑")
    args = ap.parse_args()

    today = datetime.date.today().isoformat()
    out_path = args.out or os.path.join(
        ROOT, "MCU", "docs", f"footprint_{today.replace('-', '')}.md")

    results = {}
    for name, enables in VARIANTS:
        print(f"[build] {name:8s} "
              + " ".join(f"{f.split('_')[1].lower()}={v}"
                         for f, v in zip(FLAGS, enables)))
        results[name] = build_variant(enables)
        r = results[name]
        print(f"        text={r['text']} data={r['data']} bss={r['bss']} "
              f"→ flash={r['flash']} ram={r['ram']}")

    base = results["base"]
    lines = [
        f"# 三法嵌入式 footprint 量測（{today}）",
        "",
        "量測方式：`make EXTRA_CFLAGS=-DSOC_*_ENABLE=…` 產生骨架／骨架＋單一方法變體，",
        "以 `arm-none-eabi-size` 取 text/data/bss；淨佔用 = 變體 − base。",
        "工具鏈與最佳化同 project.yaml（arm-none-eabi-gcc, -Og）。",
        "每次更新 CPU cycles 由韌體 1 Hz soc 狀態行 `(NNNcyc)` 實測（perf_cyc）。",
        "",
        "| 變體 | text | data | bss | Flash (text+data) | RAM (data+bss) | ΔFlash | ΔRAM |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, _ in VARIANTS:
        r = results[name]
        dflash = r["flash"] - base["flash"]
        dram = r["ram"] - base["ram"]
        lines.append(
            f"| {name} | {r['text']} | {r['data']} | {r['bss']} "
            f"| {r['flash']} | {r['ram']} "
            f"| {'—' if name == 'base' else f'+{dflash}'} "
            f"| {'—' if name == 'base' else f'+{dram}'} |")
    lines += [
        "",
        "> 註：EKF 之 ΔFlash 含 OCV 對照表；EKF/動態阻抗牽入之軟浮點程式庫",
        "> （__aeabi_f*）若骨架其他處已使用則不重複計入——此即「同編譯設定、",
        "> 同骨架」相減法的量測語意（論文 4.4.3）。",
    ]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print()
    print("\n".join(lines))
    print(f"\n[done] 報告已寫入 {out_path}")
    print("[note] 最後一個變體為 full，BUILD/ 發佈物已還原為三法全開版。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
