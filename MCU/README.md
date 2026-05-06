# MCU 韌體 — STM32G071 + INA226 電池量測平台

本資料夾為論文「Implementation of SOC and SOH Estimation for Lithium-ion
Batteries」(Lin et al., 2016) MCU 驗證實驗的韌體骨架。

- 目標 MCU：**STM32G071RBTx**（NUCLEO-G071RB 板載即可）
- 量測前端：**TI INA226**（高精度 16-bit 雙向電流／電壓監測 IC）
- 量測對象：18650 Li-ion 單顆電池或 LFP 單體
- 外部設備：IT6302 DC source（充電）、IT8512A+ DC load（放電）
- 演算法：動態阻抗法 (SOC) + 投影法 (SOH)

> **注意**：校正流程（INA226 Current_LSB 微調、ADC 線性化、
> 動態阻抗模型擬合）目前 pending，本骨架僅保留可組態欄位與 TODO。

---

## 1. 資料夾結構

```
MCU/
├── README.md                  本檔
├── docs/
│   └── wiring.md              詳細接線清單與訊號定義
├── Core/
│   ├── Inc/main.h             應用主標頭、腳位定義
│   └── Src/main.c             應用主程式骨架
├── App/
│   ├── battery_monitor.h/.c   電池取樣排程與資料快取
│   └── soc_soh_calc.h/.c      SOC/SOH 演算法骨架（待補）
└── Drivers/
    └── INA226/
        ├── ina226.h           暫存器、列舉、API 宣告
        └── ina226.c           HAL I2C 實作
```

CubeMX 自動生成的 HAL Drivers/、startup_*.s、linker script、
`stm32g0xx_hal_conf.h`、`Makefile` 仍需由 STM32CubeIDE 建立 — 詳第 4 節。

---

## 2. 接線圖

### 2.1 系統概觀

```
        +5V                                                    +5V
        ──┐                                                    ┌──
          │                                                    │
   ┌──────┴──────┐                                      ┌──────┴──────┐
   │             │       VBUS+      VBUS+               │             │
   │  IT6302     │──────────●──────────●────────────────│  IT8512A+   │
   │  DC Source  │                     │                │  DC Load    │
   │  (充電)      │                     │                │  (放電)      │
   │             │                     │                │             │
   │             │                ┌────┴────┐           │             │
   │             │                │         │           │             │
   │             │                │  Cell   │           │             │
   │             │                │  DUT    │           │             │
   │             │                │ (Li-ion)│           │             │
   │             │                │         │           │             │
   │             │                └────┬────┘           │             │
   │             │                     │                │             │
   │             │       VBUS-         │   VBUS-        │             │
   │             │──────────●──────────┤──────●─────────│             │
   └─────────────┘          │          │      │         └─────────────┘
                            │          │      │
                            │   ┌──────┴──────┴──────┐
                            │   │  Rshunt = 10 mΩ     │
                            │   │   (1 % 精密電阻)     │
                            │   └──────┬──────┬──────┘
                            │          │      │
                          IN+         IN-     │
                            │          │      │
                       ┌────┴──────────┴──────┴────┐
                       │         INA226             │
                       │    VS ─ 3.3V               │
                       │   GND ─ GND                │
                       │   SDA ──────► PB9          │
                       │   SCL ──────► PB8          │
                       │   ALERT ────► PA10 (option)│
                       │    A0 ─ GND   A1 ─ GND     │
                       │    (slave addr = 0x40)     │
                       └────────────────────────────┘
                                  │
                                  │ I2C1
                                  ▼
                       ┌────────────────────────────┐
                       │   STM32G071RB (Nucleo)     │
                       │                            │
                       │   PB8 ◄── I2C1_SCL         │
                       │   PB9 ◄── I2C1_SDA         │
                       │   PA2 ──► USART2_TX (log)  │
                       │   PA3 ◄── USART2_RX        │
                       │   PA5 ──► LD2 LED          │
                       │   PA10 ◄── INA226 ALERT    │
                       └────────────────────────────┘
```

### 2.2 連線清單

| 訊號     | INA226 腳位 | STM32G071 腳位 | 備註                  |
|----------|-------------|----------------|-----------------------|
| VS       | VS          | 3.3V           | INA226 邏輯供電       |
| GND      | GND         | GND            | 共地                  |
| I2C SCL  | SCL         | PB8 (I2C1_SCL) | 4.7 kΩ pull-up → 3.3V |
| I2C SDA  | SDA         | PB9 (I2C1_SDA) | 4.7 kΩ pull-up → 3.3V |
| ALERT    | ALERT       | PA10 (EXTI10)  | 開汲極，需 pull-up    |
| Addr A0  | A0          | GND            | 7-bit addr = 0x40     |
| Addr A1  | A1          | GND            |                       |
| Shunt+   | IN+         | (Rshunt 高側)  | 直接接電池正端側      |
| Shunt-   | IN-         | (Rshunt 低側)  | 直接接負載／DC source |
| VBUS     | VBUS        | (Cell+)        | 量測電池端點電壓      |

### 2.3 元件選型

- **Rshunt = 10 mΩ ± 1 %** Kelvin 4-wire（推薦 Vishay WSL2512 系列）
  - 滿標電流 ±5 A → V_shunt = ±50 mV（INA226 滿標 ±81.92 mV，留 60 % headroom）
- **I2C pull-up = 4.7 kΩ × 2**（SDA, SCL）拉至 3.3V
- **去耦電容**：INA226 VS 對 GND 0.1 μF 陶瓷
- **ALERT 線**：10 kΩ pull-up 至 3.3V

---

## 3. INA226 設定摘要

| 項目              | 預設值        | 暫存器位元    |
|-------------------|---------------|---------------|
| Averaging         | 16 次         | AVG[2:0]=010  |
| Bus V conv. time  | 1.1 ms        | VBUSCT=100    |
| Shunt V conv. time| 1.1 ms        | VSHCT=100     |
| Mode              | 連續 shunt+bus| MODE=111      |
| Calibration       | TBD（pending）| CAL register  |

> **校正計算公式（待校正流程啟動後再代入）：**
> - Current_LSB = Max_Expected_Current / 2^15
> - CAL = 0.00512 / (Current_LSB * Rshunt)
>
> 預設假設 Max_Expected_Current = 5 A、Rshunt = 0.01 Ω →
> Current_LSB ≈ 152.6 µA、CAL ≈ 3355。
> 實際數值需以 Keithley 高精度電源做點對點校正後再寫入。

---

## 4. 編譯與燒錄

本骨架不含 CubeMX 自動產生檔，使用前需先在 STM32CubeIDE：

1. 建立 STM32G071RB 專案 (Empty Makefile project)
2. 啟用以下周邊：
   - **I2C1**：PB8/PB9，速度 Fast Mode 400 kHz
   - **USART2**：PA2/PA3，115200 baud（debug log）
   - **GPIO**：PA5 輸出（LED）、PA10 輸入（INA226 ALERT, EXTI）
3. 將本資料夾 `Drivers/INA226/`、`App/` 加入 `Makefile` 的 C_SOURCES 與 INC_DIRS
4. 把 `Core/Src/main.c` 內的 `INA226_Init()`、`BatteryMonitor_Init()` 等
   呼叫貼到 CubeMX 生成的 main.c 對應 USER CODE 區塊

編譯與燒錄指令（搭配本工作站既有 stm32-build-flash skill）：

```bash
make -j4
STM32_Programmer_CLI -c port=SWD -d build/SOC_RESEARCH.hex -rst
```

---

## 5. 後續工作（依優先序）

- [ ] CubeMX 生成 HAL skeleton 並併入此資料夾
- [ ] INA226 上電自檢與 Manufacturer ID 驗證在 main loop 跑通
- [ ] UART 周期 log 量測值（電壓、電流、功率）
- [ ] **Pending**：INA226 Current_LSB 點對點校正（搭配 IT6302 + 標準電流表）
- [ ] **Pending**：動態阻抗法電流脈衝注入（IT8512A+ List Mode 控制）
- [ ] **Pending**：投影法 SOH 容量積分追蹤
