# INA226 電流量測校正紀錄

| 項目 | 內容 |
|---|---|
| 日期 | 2026-05-07 |
| 執行 | jackhung |
| 韌體 commit | `1498155`（SCRIPTS/flash_and_verify.py 跑 60 s heartbeat PASS） |
| MCU | STM32G071RBTx (Nucleo-G071RB)，板載 ST-Link V2.1 |
| INA226 | I²C addr 0x40，Rshunt 標稱 10 mΩ（datasheet）|
| Source | ITECH IT6302（/dev/ttyACM1，SCPI v1.05-1.04）|
| Load | ITECH IT8512A+（/dev/ttyACM0，SCPI v1.57）|
| DUT 電池 | NMC 18650/21700 級，2000 mAh，校正期間 SoC ≈ 65 %（OCV ≈ 3.94 V）|
| 韌體 Current_LSB 預設 | 152.5879 µA / LSB（datasheet Eq. for I_max=5 A, R=10 mΩ）|

---

## 1. 校正前的量測 baseline（pre-calibration 觀察）

### 1.1 第一次靜態比對（200 mA 動態測試）

| 量項 | Load (truth) | MCU INA226 (raw) | 差 |
|---|---|---|---|
| V @ idle | 3.9421 V | 3.9422 V | < 1 mV |
| V @ 200 mA pull | 3.9270 V | 3.9317 V | **+4.7 mV**（INA226 sense 點靠近電池端，差值是 INA226→Load 端子的線路 IR drop）|
| I @ pull | 198.88 mA | 230.40 mA | **+31.5 mA = +15.8 %** |

→ 確認 INA226 量測電流系統性偏高約 **15 %**，需要校正。

### 1.2 60 秒 2 A 線路熱測試

| 項目 | 值 |
|---|---|
| Load setpoint | 2.000 A（readback 驗證後才 INP ON）|
| 實際拉流 | 1.999 A 整 60 秒 |
| Battery V（idle → loaded）| 3.94 V → 3.71 V（壓降 230 mV）|
| Loop 總阻抗 | ≈ 114 mΩ（含電池內阻 + 線阻 + 接點 + 10 mΩ shunt）|
| Wire-only heat power | ≈ 0.46 W（扣掉電池內阻估算）|
| 結論 | 線完全不燙（每接點 < 50 mW），4 A 上限有充足餘量 |

線阻拆解（從 V 差倒推）：
- INA226 sense → Load 端子：~24 mΩ（INA226 那邊線比較短/粗）
- Load → 電池：剩下部分

---

## 2. 校正流程

### 2.1 設備配置

- **充電路徑**：IT6302 CH1 (+) → 電池 (+) → Shunt → 電池 (-) → IT6302 CH1 (-)
- **放電路徑**：IT8512A+ (+) → 電池 (+) → Shunt → 電池 (-) → IT8512A+ (-)
- INA226 跨 Shunt 量測，I²C 走到 MCU，MCU 透過 USART2 把 1 Hz heartbeat 印到 ST-Link VCP
- 充放電互鎖：PSU 與 Load 不會同時 ON（流程上由腳本確保）

### 2.2 校正點

七個 setpoint（充電與放電各取一次）：

```
0.000, 0.050, 0.100, 0.500, 1.000, 1.500, 2.000 A
```

選點理由：
- 0.000 A → 量 INA226 零點偏移
- 0.050、0.100 A → 低電流區的 offset-dominated 行為
- 0.500、1.000、1.500、2.000 A → 高電流區，shunt 線性度 + 純 scale offset
- 2.000 A = 1C @ 2000 mAh，超過此電流的校正之後再加

### 2.3 每點時序

```
↓ setpoint 寫入儀器，readback 驗證（容差 max(5 mA, 5% target)）
3.0 s settle  ←  等 PSU/Load 與量測電路穩態
5.0 s sample  ←  並行採樣：
                  - PSU.MEAS:CURR? 或 LOAD.MEAS:CURR?（每 0.4 s 一次）
                  - MCU heartbeat（每秒一次，從 VCP 解析）
平均得到該點的 (ref_I, mcu_I)
↓
0.8 s 過渡（輸入/輸出 OFF 後 bus 放鬆）
```

腳本：[`SCRIPTS/ina226_calibrate.py`](../../SCRIPTS/ina226_calibrate.py)

---

## 3. 校正原始數據

### 3.1 放電方向（Load active, PSU OFF）

| target (A) | Load.I (ref, mA) | MCU.I (raw, mA) | Δ (mA) | ratio (ref/mcu) |
|---:|---:|---:|---:|---:|
| 0.000 | 0.00 | **+1.10** | +1.10 | — |
| 0.050 | 48.69 | 57.40 | +8.71 | 0.8483 |
| 0.100 | 98.54 | 113.82 | +15.28 | 0.8658 |
| 0.500 | 498.60 | 567.65 | +69.05 | 0.8784 |
| 1.000 | 998.89 | 1135.40 | +136.51 | 0.8798 |
| 1.500 | 1498.67 | 1702.75 | +204.08 | 0.8801 |
| 2.000 | 1998.87 | 2270.60 | +271.73 | 0.8803 |

### 3.2 充電方向（PSU CH1 active, Load OFF）

| target (A) | PSU.I (ref, mA) | MCU.I (raw, mA) | Δ (mA) | ratio (ref/mcu) |
|---:|---:|---:|---:|---:|
| 0.000 | 0.00 | **+1.10** | +1.10 | — |
| 0.050 | 49.86 | −58.55 | −108.41 | −0.8516 |
| 0.100 | 99.88 | −115.30 | −215.18 | −0.8663 |
| 0.500 | 499.80 | −569.10 | −1068.90 | −0.8782 |
| 1.000 | 999.78 | −1136.77 | −2136.55 | −0.8795 |
| 1.500 | 1499.81 | −1704.70 | −3204.51 | −0.8798 |
| 2.000 | 1999.81 | −2272.85 | −4272.66 | −0.8799 |

> **MCU 充電時 I 為負值**：INA226 將 IN+ → IN- 的電流定義為正向，充電方向相反 → 韌體吐出負數，符號學上正確。

### 3.3 觀察

1. **充放電完全對稱**：兩個方向同 target 的 |ratio| 一致到第三位小數。INA226 shunt 量測對方向無偏。
2. **0 A 零點偏移 = +1.10 mA**（兩個方向都一樣，正號）。這是 INA226 ADC 在無電流時的 quantization + offset。
3. **高電流區 ratio 收斂到 0.880**（>500 mA 後 ratio 穩定）。等價於：
   - Rshunt 實際值 ≈ 10 / 0.880 = **11.36 mΩ**（標稱 10 mΩ，+13.6% 偏離；可能是 0805/1206 shunt 的 ±5% 容差加上 PCB 走線串聯阻抗）
   - 或等價：Current_LSB 該改成 152.5879 × 0.880 = **134.3 µA / LSB**
4. **低電流區 ratio 下降**（50 mA → 0.85）：offset 1.10 mA 在 50 mA 上佔比 2.2 %，被 scale 0.88 一乘變成 ratio 從 0.88 降到 0.85，符合純 offset 主導模型。

---

## 4. LUT 內插驗證

### 4.1 方法

用**校正表沒列入**的 4 個點（0.300、0.750、1.250、1.750 A）拉 Load，比較 LUT piecewise-linear 內插預測 vs Load 真值。

LUT 載入：[`TEST/core/ina226_cal.py`](../../TEST/core/ina226_cal.py)、`load_cal()` → `disc.correct(mcu_A)`。

### 4.2 結果

| target (A) | Load 真值 (mA) | MCU 原始 (mA) | LUT 預測 (mA) | 預測誤差 (mA) |
|---:|---:|---:|---:|---:|
| 0.300 | 298.31 | 340.20 | 298.10 | **−0.21** |
| 0.750 | 748.78 | 851.32 | 748.56 | **−0.21** |
| 1.250 | 1248.46 | 1418.52 | 1248.29 | **−0.17** |
| 1.750 | 1748.61 | 1986.30 | 1748.44 | **−0.16** |

### 4.3 結論

- 全範圍誤差 **< 0.21 mA**，相當於 1.75 A 的 **0.012 %**
- 校正前：raw 偏差 +41 mA ~ +238 mA（+13 % 系統性偏高）
- 校正後：誤差 < 0.21 mA（< 1 ‰）
- **比 INA226 datasheet ±0.1 % spec 還準**（datasheet 不含 shunt 容差，本校正連 shunt 一起校到 < 1 ‰）

---

## 5. 產物

| 檔案 | 用途 |
|---|---|
| [`TEST/data/calibration_ina226.json`](../../TEST/data/calibration_ina226.json) | 14 點原始校正資料（schema `ina226-cal/v1`）|
| [`DOC/校正紀錄/2026-05-07_ina226_validation.json`](2026-05-07_ina226_validation.json) | 4 點 LUT 內插驗證資料 |
| [`SCRIPTS/ina226_calibrate.py`](../../SCRIPTS/ina226_calibrate.py) | 校正流程腳本（recal 重跑用）|
| [`TEST/core/ina226_cal.py`](../../TEST/core/ina226_cal.py) | piecewise-linear LUT helper |

---

## 6. 後續工作

### 已 ready 的選項

- [ ] 把 `disc.correct()` / `chg.correct()` 接到 phase 腳本 logger，CSV 同時記 raw I 與 cal I
- [ ] 把 LUT 7 點寫進 INA226 driver 的後處理（C 陣列 + 線性內插），MCU 直接吐校正後值
- [ ] 跑 Phase 2 baseline 短測試（5 分鐘 1 A 放電 + 1 次擾動）驗證 dV/dI 採樣路徑

### 待補（pending hardware/setup）

- 重做校正當 (a) 換不同 Rshunt 板、(b) 環境溫度顯著不同、(c) 跨多顆 INA226 板做產品化
- 高於 2 A 的校正點（如果之後要做 ≥1C 的放電測試）
- 溫度補償：INA226 與 shunt 對溫度都有 ppm/°C 漂移，目前室溫 ~25 °C 下校的，極端溫度可能要重做

---

## 7. 訊息流摘要

```
電池 ── shunt 10 mΩ ── Load / PSU
            │
            ▼
        INA226（V+, V-, VBUS）
            │ I²C @ 400 kHz
            ▼
        STM32G071 ── USART2 115200 ──→ /dev/ttyACM2 ──→ Pi
                                                          │
                                            校正腳本 在這裡解析 heartbeat
                                                          │
                                            另一個 USB-serial ──→ IT8512A (truth)
                                                          │
                                            又一個 USB-serial ──→ IT6302 (truth)
```
