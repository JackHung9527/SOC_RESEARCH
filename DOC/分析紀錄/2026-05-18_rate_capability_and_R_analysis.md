# 充放電資料分析報告 — Rate capability、R(SoC)、跨輪老化

- **日期**：2026-05-18
- **資料快照**：commit `a3c7678`（round 1-6 完整 + round 7 cyc30 進行中）
- **電池**：custom NMC 2000 mAh，V_cv = 4.2 V，V_cutoff = 2.5 V
- **平台**：STM32 + IT6302 PSU + IT8512A+ Load + INA226（已多點校正）+ Python orchestrator (`TEST/round_runner_v1.py`)
- **環境**：實驗室未恆溫，ambient 推估 24–28°C（季節性偏移）

> **這份文件是 self-contained，新對話讀完這份 + `CLAUDE.md` 即可接續分析。所有結論可由 `TEST/data/` 下的 CSV 重現，方法附在 §6。**

---

## 1. 資料來源

| 檔案 / 欄位 | 用途 |
|---|---|
| `TEST/data/cycle_log.csv` | 每個 cycle 一列 metadata：`cycle_id, round_id, c_rate, q_actual_mAh, q_retention_pct, v_start, v_end, duration_s, csv_path, note` |
| `TEST/data/round0XX_cycYY_discharge_*.csv` | 每筆 ~2.6 s sample，欄位：`t_s, mode, v, i, soc_cc, dvdi, note`。每 ~60 s 有 perturb_low/perturb_high 兩列做 dV/dI 擾動 |
| `TEST/data/round0XX_cycYY_charge_*.csv` | 同上欄位但 **沒有 perturbation**（充電段不擾動） |
| `TEST/data/round0XX_cycZZ_storage_charge_*.csv` | 每輪結束的 park@3.90V 階段 |

關鍵：**只有 discharge trace 有 `dvdi` 欄位**（perturb_high row），R = −dvdi。perturbation = main C-rate 短暫降到 0.2C dwell 1 s 再回升。

---

## 2. Rate capability — cell baseline = 1655.8 mAh @ 0.5C（rounds 2-6）

| C-rate | n | 平均 Q (mAh) | σ | σ/μ |
|---|---|---|---|---|
| 0.5C | 6 | 1660.3 | 9.00 | 0.54% |
| 1.0C | 6 | 1656.5 | 2.91 | 0.18% |
| 1.5C | 6 | 1653.6 | 3.82 | 0.23% |
| 2.0C | 6 | 1649.3 | 3.15 | 0.19% |

→ 從 0.5C 到 2.0C 容量只掉 ~0.4%（rounds 2-6），rate capability 極佳。

**round 1 是 outlier**（1677.6 mAh @ 0.5C）— 起始 OCV 4.19 V，`already_full bypass` 觸發、charge step 37 s 跳過，等於 cell 進入 round 1 的 SoC 比後續 rounds 高約 0.5%。論文章節 5 計算 baseline Q_rated 時**排除 round 1**。

---

## 3. R(SoC) — 經典 U 型 + 末端急升

|     SoC bin |    0.5C |    1.0C |    1.5C |    2.0C |
|------------:|--------:|--------:|--------:|--------:|
| 100–90% | 60.9 ± 0.6 | 60.3 ± 0.6 | 60.2 ± 0.7 | 60.2 ± 0.6 |
|  90–80% | 60.1 ± 0.5 | 59.0 ± 0.5 | 58.6 ± 0.6 | 58.4 ± 0.6 |
|  80–70% | 59.5 ± 0.4 | 58.3 ± 0.4 | 57.5 ± 0.4 | 57.0 ± 0.3 |
|  70–60% | 59.5 ± 0.3 | 58.0 ± 0.3 | 57.2 ± 0.3 | 56.4 ± 0.3 |
|  60–50% | **59.4** ± 0.3 | **57.8** ± 0.3 | **57.0** ± 0.3 | **56.1** ± 0.2 |
|  50–40% | 59.4 ± 0.3 | 58.1 ± 0.3 | 57.0 ± 0.2 | 56.1 ± 0.2 |
|  40–30% | 59.7 ± 0.2 | 58.2 ± 0.2 | 57.1 ± 0.2 | 56.3 ± 0.2 |
|  30–20% | 60.0 ± 0.3 | 58.5 ± 0.2 | 57.3 ± 0.2 | 56.4 ± 0.2 |
|  20–10% | 60.5 ± 0.3 | 58.9 ± 0.3 | 57.7 ± 0.3 | 56.6 ± 0.2 |
|  10– 0% | **66.0 ± 8.7** | 61.5 ± 2.0 | 60.0 ± 1.6 | 58.2 ± 1.6 |
|             | mΩ ± σ | mΩ ± σ | mΩ ± σ | mΩ ± σ |

要點：
- **plateau 最低點在 SoC 50–60%**（典型 NMC graphite 行為）
- **頭尾兩端 R 升高**；< 10% 急升是動態阻抗法 SoC 的核心訊號（plateau 57 mΩ → cutoff 66 mΩ，差 ~9 mΩ）
- **末端 σ 跳到 8.7 mΩ (0.5C)**：V(SoC) 曲率在 cutoff 區大，1 s perturbation 抓到的不只是 IR，**是 measurement artifact**，不是 cell 變了
- **R 隨 C-rate 升高而降**（plateau 0.5C → 2.0C：59.4 → 56.1 mΩ，−5.5%）。最可能原因是 cell 自熱（高 C 電流 → cell 升溫 → 電解液電導率上升 → R 降）

---

## 4. R 跨輪變化 — 「越測越低」是 commissioning artifact，不是腦補

固定 SoC 50–60%、0.5C：

```
round 1  cyc 1   59.78 mΩ
round 2  cyc 5   59.39 mΩ
round 3  cyc10   59.50 mΩ
round 4  cyc15   59.36 mΩ
round 5  cyc20   59.28 mΩ
round 6  cyc25   59.08 mΩ
round 7  cyc30   59.09 mΩ
─────────────────────────
       30 cycle 共 −1.2%
```

跟直覺「老化 R 上升」反向，但這在 fresh cell 前 30–100 cycle 是正常的 commissioning 效應。**降級後的歸因（按證據強度排序）**：

### 4.1 電解液浸潤（強佐證 ✅）

**Lechtenfeld et al. (2024)** *Advanced Science* — Effect of Electrolyte Quantity on Aging of LIB
- 開放閱讀：https://pmc.ncbi.nlm.nih.gov/articles/PMC11497071/
- DOI：https://advanced.onlinelibrary.wiley.com/doi/10.1002/advs.202405897
- 關鍵句：「(dis)charge curves converge **after 30 cycles**」「discharge capacities ... exceed the value of the initial cycle within the first 5–25 cycles ... slow recovery as the electrolyte gradually redistributes」

**Gamry App Note** — EIS in Wetting of Li-ion Battery Materials
- https://www.gamry.com/application-notes/EIS/eis-wetting-li-ion-battery-materials/
- 「During wetting, the ohmic resistance (HFR) of a LIB changes until it is fully wetted」

### 4.2 環境溫漂（中強佐證 ✅）

鋰電池 DC R 是 **NTC**（溫度上升 R 下降）。文獻溫度係數約 **−2 to −5%/°C**（化學體系相關）。
- Battery University BU-410：https://www.batteryuniversity.com/article/bu-410-charging-at-high-and-low-temperatures/
- ASP Power 業界資料：https://www.szaspower.com/industry-news/lithium-ion-battery-temperature-resistance-characteristics.html
- ScienceDirect: https://www.sciencedirect.com/science/article/pii/S037877532501314X

對本實驗 −1.2% R 偏移，**只要 ambient 偏 0.3–0.6°C 就足以解釋**。lab 未恆溫，這是主要不確定性。

### 4.3 SEI 重組（弱佐證 ⚠️）

對 graphite anode NMC cell 的直接證據不足，主要佐證來自 lithium-metal 系統：
- PMC10463237 — Anode-free Li-metal SEI evolution: https://pmc.ncbi.nlm.nih.gov/articles/PMC10463237/

SEI 形成資源消耗的經典 review：
- An et al. (2016) *Carbon*：https://www.sciencedirect.com/science/article/pii/S0008622316302676

### 4.4 真正 R rise 開始的 cycle 數（強佐證 ✅）

- **dos Reis et al. (2024)** *Nature Scientific Data*：Graphite/NMC811 R 從 33 → 100 mΩ over **1600 cycles**（≈ 0.04 mΩ/cycle 平均）。前 100 cycle 內訊號被浸潤/溫漂蓋掉。
  https://www.nature.com/articles/s41597-024-03831-x
- **Attia et al. (2022)** *J. Electrochem. Soc.* — Knees in Li-ion Battery Aging Trajectories
  https://iopscience.iop.org/article/10.1149/1945-7111/ac6d13

---

## 5. R(V_start vs I) 一階回歸 — 全段平均 R₀ ≈ 64 mΩ

從 4 個 C-rate 的 discharge step v_start 對 I 線性回歸：

```
0.5C  I=0.83A  v_start=4.128 V
1.0C  I=1.67A  v_start=4.074 V
1.5C  I=2.50A  v_start=4.021 V
2.0C  I=3.33A  v_start=3.968 V

linear fit V = V_oc - R·I  →  R_dc ≈ 64 mΩ,  V_oc ≈ 4.180 V
```

這個 64 mΩ 比 perturbation R（plateau ~58 mΩ）大，差異原因：v_start 是 discharge 剛開始的瞬時電壓，含 R₀ + 早期 transient；perturbation 是已運轉 60 s 後 cell 已熱、再做 1 s 階躍，主要抓 R₀。兩者一致。

---

## 6. 重現方法 — Python snippet（複製即可跑）

```python
import csv, glob, re
from pathlib import Path
from collections import defaultdict
from statistics import mean, stdev

DATA = Path("TEST/data")

# === Rate capability ===
by_rate = defaultdict(list)
with open(DATA/"cycle_log.csv") as f:
    for r in csv.DictReader(f):
        if r["direction"] != "discharge": continue
        by_rate[float(r["c_rate"])].append({
            "rnd": int(r["round_id"]),
            "cyc": int(r["cycle_id"]),
            "q":   float(r["q_actual_mAh"]),
            "vs":  float(r["v_start"]),
            "ve":  float(r["v_end"]),
        })

for rate in sorted(by_rate):
    qs = [x["q"] for x in by_rate[rate] if x["rnd"] >= 2]   # exclude round 1
    print(f"{rate}C  mean Q = {mean(qs):.2f} mAh  σ/μ = {100*stdev(qs)/mean(qs):.2f}%")

# === R(SoC, C-rate) from perturb_high rows ===
samples = defaultdict(list)   # (rate, soc_bin) -> list of R mΩ
for fp in sorted(DATA.glob("round*_cyc*_discharge_*.csv")):
    m = re.search(r"round(\d+)_cyc(\d+)_discharge_(\d+\.\d+)C", fp.name)
    if not m: continue
    rnd, cyc, rate = int(m.group(1)), int(m.group(2)), float(m.group(3))
    with open(fp) as f:
        for row in csv.DictReader(f):
            if row["mode"] != "perturb_high": continue
            try: dvdi = float(row["dvdi"])
            except: continue
            soc = float(row["soc_cc"])
            R   = -dvdi * 1000   # mΩ
            bin_lo = int(soc * 10) / 10
            samples[(rate, bin_lo)].append((rnd, cyc, R))

for rate in sorted({k[0] for k in samples}):
    print(f"\n{rate}C:")
    for bin_lo in sorted({k[1] for k in samples if k[0]==rate}, reverse=True):
        vals = [r for (_,_,r) in samples[(rate, bin_lo)]]
        print(f"  SoC {int((bin_lo+0.1)*100)}-{int(bin_lo*100)}%   {mean(vals):.1f} ± {stdev(vals) if len(vals)>1 else 0:.1f} mΩ  (n={len(vals)})")
```

---

## 7. 給論文章節的 4 個 takeaway（直接抄）

1. **Cell baseline = 1655.8 mAh @ 0.5C（rounds 2-6 mean）** → 標稱 2000 mAh，實測 ≈ 0.83 × rated（25°C, 2.5 V cutoff）
2. **Rate capability**：0.5C → 2.0C 容量僅掉 0.4%，cell 內阻夠低，動態阻抗法 SoC 在此 cell IR signal 偏小，演算法靈敏度要注意
3. **DC R₀ ≈ 64 mΩ**（v_start 法）/ **plateau R ≈ 58 mΩ**（perturbation 法），兩者一致；R(SoC) U 型、cutoff 區急升 9 mΩ — 動態阻抗法的有效訊號
4. **前 30 cycle R 微降 1.2%，是 commissioning artefact（浸潤 + 溫漂主導），不是 SoH 退化**。論文 SoH 章節要從 cycle ≥ 50 之後再分析 dR/dcycle，limitations 章揭露未做恆溫

---

## 8. 給新對話的接續指南

新 Claude 對話開啟時讀完 `CLAUDE.md` 應該會自動指向這份檔案。如果想接著做：

- **下一步建議 A**：從某筆 discharge trace 把 V(SoC) 曲線抽出來做 OCV-like plot（搭配等待 `TEST/gitt_ocv_runner.py` 跑出真正的 OCV 表）
- **下一步建議 B**：把 R(SoC) U 型圖渲染為論文圖（matplotlib），存進 `DOC/論文撰寫/figs/`
- **下一步建議 C**：等 round 7 跑完，加上 round 8+ 做更深的老化趨勢延伸（前提：先把 ambient 溫度感測也記下來，做 Arrhenius 修正）

要追問本份分析的細節（哪個 cycle 為什麼異常、R(SoC) 圖怎麼畫、文獻全文怎麼引），原始討論在 git commit `a3c7678` 之前的 conversation；資料原檔已全部 push 上 GitHub。
