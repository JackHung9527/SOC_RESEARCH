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

## 執行順序（單顆電池）

```bash
# 1) 充滿電（CC-CV → I_term=50 mA 自動停）
python3 TEST/charge.py

# 2) 拔掉 PSU 線，接上 Load 線。靜置 30 分鐘（OCV 平衡）
#    — phase2 內建 60 s pre-rest，不夠就改 config 或外部等

# 3) Phase 2 基線放電（含每 60 s 一次的 dV/dI 擾動採樣）
python3 TEST/phase2_baseline.py

# 4) 後續 phase 3/4 依需要再跑
```

## 緊急中止

任何 phase 腳本執行中：
- **Ctrl+C** — 觸發 `finally` 區段，自動關閉 Load INPut / PSU OUTPut。
- 或另開 terminal 跑 `python3 INST/scripts/all_off.py`（直接砍兩台儀器）。

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

## 安全包絡

`config.SAFETY` 預設：
- `v_hard_high = 4.25 V`（電池過壓）
- `v_hard_low = 2.70 V`（電池過放，比 cutoff 2.75 V 多 50 mV 緩衝）
- `i_hard_high = 4.30 A`（避免接線冒煙）

連續 2 個取樣越界才會 `SafetyAbort`，避免單次量測雜訊誤觸發。
