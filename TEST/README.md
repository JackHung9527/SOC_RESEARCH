# TEST/ — 鋰電池 SOC/SOH 動態阻抗法 驗證腳本

樹梅派端的測試腳本，依照 meeting_0416 規劃的四階段流程組織。
低階儀器類別在 `drivers/`，共用工具（CSV 紀錄、安全防護、庫侖計數）在 `core/`。

## 目錄結構

```
TEST/
├── config.py                 # 電池規格、儀器 port、實驗參數（單一事實來源）
├── drivers/
│   ├── scpi_serial.py        # SCPI over RS-232 共用底層
│   ├── it6302.py             # IT6302 三通道電源 (CH1/CH2 30V3A, CH3 5V3A)
│   └── it8512.py             # IT8512A+ 電子負載 (CC/CV/CR/CW)
├── core/
│   ├── safety.py             # SafetyGuard：硬性 V/I 包絡，連續 2 樣本越界才觸發
│   ├── logger.py             # 統一 CSV 格式：t_s,mode,v,i,soc_cc,dvdi,note
│   └── coulomb.py            # 庫侖計數器：放電為正，充電為負
├── charge.py                 # CC-CV 充飽（Phase 2 之前必跑）
├── phase1_sensor_cal.py      # 感測器校準（INA226 上線後再實作）
├── phase2_baseline.py        # 新電池基線 CC 放電 + 週期擾動，主要實驗
├── phase3_multirate.py       # 多倍率/脈衝放電（骨架）
├── phase4_aging.py           # 老化循環（骨架）
└── data/                     # CSV 輸出目錄（自動建）
```

## 儀器接線

| 儀器 | Port | 說明 |
|---|---|---|
| IT8512A+ 電子負載 | `/dev/ttyACM0` | 拉電流（放電） |
| IT6302 電源 | `/dev/ttyACM1` | 充電（CH1） |

電池接線：
- **充電時**：IT6302 CH1 紅 → 電池正、黑 → 電池負。
- **放電時**：IT8512A+ 紅 → 電池正、黑 → 電池負。
- **建議**：之後加 4-wire Kelvin sense 線到電池端子，避免線阻吃掉動態阻抗訊號（先前實測線阻 ~166 mΩ，比鋰電池內阻還大）。

## 電池 profile（必選）

**沒有 BMS！** 任何 phase 腳本啟動前必須先選一顆電池 profile，
否則 `require_battery()` 會立刻 `SystemExit` 退出。

```bash
# 互動式挑選 + 可選自訂容量 / 充放電 cutoff / CC 電流
python3 TEST/select_battery.py

# 或直接指定 catalogue key
python3 TEST/select_battery.py 18650-NMC-2150

# 列出 catalogue
python3 TEST/select_battery.py --list

# 顯示目前選擇
python3 TEST/select_battery.py --show
```

選擇結果寫到 `data/active_profile.json`，所有腳本自動讀取。
內建 catalogue：`18650-NMC-2150`、`18650-NMC-3500`、`26650-LFP-3000`、
`14500-NMC-800`，外加「custom」自由輸入（仍受化學體系絕對極限把關）。

化學體系絕對極限（在 `profiles.CHEMISTRIES`）：

| 化學體系 | V_abs_max | V_abs_min | 標準充電上限 | 標準放電下限 |
|---|---|---|---|---|
| Li-ion NMC/NCA | 4.25 V | 2.50 V | 4.20 V | 2.75 V |
| LiFePO4 | 3.70 V | 2.00 V | 3.65 V | 2.50 V |
| LTO | 2.85 V | 1.50 V | 2.80 V | 1.80 V |

任何 profile 的充電 cutoff 不能超過 `V_abs_max`、放電 cutoff 不能低於 `V_abs_min`。
`save_active_profile()` 在落盤前會驗證，違規直接拒寫。

## 執行順序（單顆電池）

```bash
# 0) 選電池
python3 TEST/select_battery.py

# 1) 充滿電（CC-CV → I_term 自動停）
python3 TEST/charge.py
#    腳本結束會強制 dead-time 5 s，**期間 PSU 已 OFF**，
#    這時可以拔線、接上 Load 線、靜置 OCV。

# 2) Phase 2 基線放電（含每 60 s 一次的 dV/dI 擾動採樣）
#    BenchInterlock 會先驗證 PSU 確實 OFF 才允許 Load 啟用。
python3 TEST/phase2_baseline.py

# 3) 後續 phase 3/4 依需要再跑
```

## Bench 互鎖（BenchInterlock）

無 BMS 環境必須由軟體把關以下三條：

1. **PSU 與 Load 不能同時啟動。**
   `start_charge()` 啟動 PSU 前一定先 `_load_off_verified()`（讀回 INP? 確認）。
   `start_discharge()` 啟動 Load 前一定先 `_psu_off_verified()`。
2. **充放電切換必須有間隔。**
   每次 `stop_charge()` / `stop_discharge()` 後進入 `COOLDOWN` 狀態，
   至少 `SAFETY.deadtime_s = 5 秒` 內不允許啟動另一邊。
   下一個 `start_*()` 自動 `time.sleep` 補滿剩餘秒數。
3. **狀態機強制串行。**
   `CHARGING → start_discharge` 直接 `BenchInterlockError`，
   要求使用者顯式呼叫 `stop_charge()`，避免 race。
   `emergency_stop()` 從任何狀態都能呼叫，先砍 Load INP、再砍 PSU OUTP，
   `__exit__` 自動觸發。

## 安全包絡（雙層 SafetyGuard）

`SafetyGuard.from_profile(battery)` 自動建構：

- **絕對層（無 debounce，單樣本即跳）**：化學體系硬極限
  （NMC: 4.25/2.50 V；LFP: 3.70/2.00 V）。
- **軟層（連續 2 樣本越界才跳）**：使用者 cutoff ± 50 mV。
- **電流層**：`SAFETY.i_hard_high = 4.30 A`（接線安全上限）。

軟層用來吸收量測雜訊，絕對層保證即便雜訊命中也不過化學極限。

## 緊急中止

- **Ctrl+C** — 觸發 phase 腳本 `finally`，呼叫 `bench.emergency_stop()`，
  PSU CHAN:OUTP OFF + 全部 OUTP OFF + Load INP OFF。
- 另開 terminal：`python3 INST/scripts/all_off.py`（直接砍兩台儀器）。

## CSV 格式

每個 phase 都產出 `data/<tag>_YYYYMMDD_HHMMSS.csv`，欄位固定：

| 欄位 | 意義 |
|---|---|
| `t_s` | 時間戳（秒，從該 phase 開始計） |
| `mode` | 階段標籤：`rest`, `discharge`, `charge`, `perturb_low`, `perturb_high`, `cutoff` |
| `v` | 量測電壓（V） |
| `i` | 量測電流（A，放電為正） |
| `soc_cc` | 庫侖計數法估算的 SoC（0~1） |
| `dvdi` | 動態阻抗（Ω），只在 `perturb_high` 那一行有值 |
| `note` | 自由文字註記 |
