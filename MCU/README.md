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

`SOC_RESEARCH/` 是 firmware-project root；CubeIDE 專案（`.ioc` + Makefile +
sources）依 firmware-project-builder 規約放在 `MCU/soc_research_mcu/` —
**CubeIDE 專案資料夾名稱必須跟 .ioc 檔案的 basename 完全相同**，所以這裡多
一層 `soc_research_mcu/`。`MCU/` 本身只是「韌體相關東西」的分類資料夾。
`project.yaml` / `BUILD/` / `scripts/` 一律放在 root 層。

每一個 driver 都各自有一個 `USER_CODE/<driver_name>/` 子資料夾（Phase 3 規約），
不再走以前那種「app 層放 App/、IC 層放 Drivers/」的舊樹。INA226 / battery_monitor /
soc_soh_calc 三個 pre-existing 模組已遷入 USER_CODE/ 對應子層，**source 內容完全沒動**，
只動位置、Makefile 路徑、global_includes.h / model_set.h 的黏合。

```
SOC_RESEARCH/                              ← firmware-project root
├── project.yaml                           firmware-project-builder 單一事實來源
├── project.yaml.bak                       (agent 寫入前自動備份)
├── BUILD/                                 發佈用 .elf / .bin / .hex（由 make publish 投放）
├── scripts/
│   └── flash_and_verify.py                openocd flash + UART 60 s 驗證
├── DOC/  INST/  TEST/  CLAUDE.md          研究文件 / 量測紀錄 / 專案說明
└── MCU/                                   ← 分類資料夾（裝韌體相關東西）
    ├── README.md                          本檔
    ├── docs/
    │   └── wiring.md                      詳細接線清單與訊號定義
    └── soc_research_mcu/                  ★ CubeIDE 專案根目錄 (cubeide.project_dir)
        ├── soc_research_mcu.ioc           CubeMX-compatible 腳位/周邊配置（手寫）
        ├── Makefile                       PUBLISH_DIR = ../../BUILD（多一層）
        ├── STM32G071RBTX_FLASH.ld         linker script
        ├── Core/
        │   ├── Inc/main.h                 HAL handle extern + 腳位 label
        │   └── Src/
        │       ├── main.c                 HAL_Init + SystemClock + MX_*_Init + once() + while(loop())
        │       ├── stm32g0xx_it.c         ISR：SysTick / TIM6 / USART2 / EXTI
        │       └── syscalls.c             newlib stub（_write 已交給 uart_debug）
        ├── USER_CODE/                     stm32-proj-init 框架（手動等效）
        │   ├── global_includes.h          統一 include 入口；USER_DRIVERS marker 內列出所有 driver header
        │   ├── model_set.h                全專案參數（per-driver MODEL_SET_<NAME> 區塊）
        │   ├── softwareTim.[ch]           100 µs base tick 計數器（TIM6 ISR 唯一寫入者）
        │   ├── userCode.[ch]              once() / loop() — 含 boot banner + 1Hz heartbeat
        │   ├── uart_debug/                stm32-uart-scaffold 產出（USART2, IT-driven, printf retarget）
        │   ├── i2c_bus/                   stm32-i2c-scaffold 產出（I2C1, sync HAL_I2C_Mem 抽象）
        │   ├── ina226/                    ★ pre-existing IC driver，遷入 USER_CODE/，內容未動
        │   ├── battery_monitor/           ★ pre-existing app 層，遷入 USER_CODE/，內容未動
        │   └── soc_soh_calc/              ★ pre-existing 演算法 stub，遷入 USER_CODE/，內容未動
        ├── Drivers/
        │   ├── CMSIS/                     vendored from STM32CubeG0 v1.6.2
        │   └── STM32G0xx_HAL_Driver/      同上 — 只剩 HAL/CMSIS（INA226 已搬到 USER_CODE/ina226/）
        └── build/                         arm-none-eabi-gcc 中間物 (.o/.d/.lst/.elf/.map) — gitignored
```

整體靠 `firmware-project-builder` agent 編排，狀態寫在 root 層的
`SOC_RESEARCH/project.yaml`。INA226 driver、battery_monitor、soc_soh_calc 三者
原始碼維持原樣，由 USER_CODE/userCode.c 的 once()/loop() 呼叫進來；不再由
main.c 直接呼叫。

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

本專案在 Linux/Raspberry Pi host 上以 `arm-none-eabi-gcc` + `openocd` 操作，
不需要 STM32CubeIDE GUI；`.ioc` 為手寫但與 CubeMX 6.10+ 相容。

```bash
# 編譯 / 燒錄在 CubeIDE 工作區裡跑（也可從 root 用 make -C MCU/soc_research_mcu）：
cd SOC_RESEARCH/MCU/soc_research_mcu
make                    # arm-none-eabi-gcc 12.2 → build/soc_research_mcu.{elf,bin,hex}
                        # + 自動 publish 到 ../../BUILD/（= SOC_RESEARCH/BUILD/）
make flash              # openocd via on-board ST-LINK/V2.1

# 驗證腳本在 firmware-project root 跑（會自動 cwd 到 MCU/soc_research_mcu/ 跑 make flash）：
cd SOC_RESEARCH
python3 scripts/flash_and_verify.py   # flash + 驗 boot banner + 60 s heartbeat 計時
```

韌體運作：
- `main()` 只做 HAL_Init / SystemClock / MX_GPIO/USART2/I2C1/TIM6 init，然後 `once()` + `while(loop())`。
- 100 µs 基底由 **TIM6** 提供，`HAL_TIM_PeriodElapsedCallback` 在 `USER_CODE/softwareTim.c`
  唯一定義，只把 `g_softWareTimCnt` 加一（不做 UART、不做應用工作）。
- 1 Hz 心跳走 `softWareTimTick_100us(Period=10000)` 在 `userCode.c::loop()` 排程，
  印 alive 行 + 翻 LED；INA226 在線時順便取樣印 V/I/P。
- 開機 banner 由 `once()` 印一次（`uart_debug_printf`），sensor 不在不會卡死。

---

## 5. 後續工作（依優先序）

- [x] HAL skeleton 從 STM32CubeG0 v1.6.2 vendored 進 Drivers/
- [x] USER_CODE 框架 + uart_debug + i2c_bus driver 透過 firmware-project-builder skill 鏈導入
- [x] UART 1 Hz 周期 log 量測值（i2c idle / ina absent 路徑已驗證 60 s monotonic）
- [ ] INA226 sensor 接上後，驗證 `[Ns] alive V=...mV I=...mA P=...mW i2c=ok ina=present` 路徑
- [ ] **Pending**：INA226 Current_LSB 點對點校正（搭配 IT6302 + 標準電流表）
- [ ] **Pending**：動態阻抗法電流脈衝注入（IT8512A+ List Mode 控制）
- [ ] **Pending**：投影法 SOH 容量積分追蹤
