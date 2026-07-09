# 2026-07-05 三種 SOC 估測法實測 CPU cycle 數（表 4-6 依據）

## 量測環境

- 平台：STM32G071RB（Cortex-M0+、SYSCLK = 64 MHz），韌體 `MCU/soc_research_mcu`（三法全開預設編譯，-Og）
- 量測法：`perf_cyc` SysTick 夾擠讀法，於 `soc_estimators_feed_1s()` 內對每法 update 各自計 cycle，經 UART（/dev/ttyACM2, 115200）每秒回報
- 電池：custom NMC（實測 1665 mAh），量測時 V ≈ 3.85 V
- 動態阻抗事件觸發：IT8512 電子負載（/dev/ttyACM0）CC 1.0 A 脈衝 ×3（ON 6 s / OFF 8 s），每個邊緣 ΔI ≈ ±1008 mA（落於 300–4500 mA 事件窗），6 個邊緣全數觸發（n=1→6）
- 觸發腳本：session scratchpad `zdyn_pulse_capture.py`（一次性，未入 repo；邏輯＝IT8512 CC 脈衝＋UART 解析）

## 實測結果（每次 update 的 CPU cycles）

| 方法 | cycles / update | 換算時間 @64 MHz | 備註 |
|---|---|---|---|
| 庫倫計數 `soc_coulomb` | **301**（典型；有電流時 305，最大 367） | ≈ 4.7 µs | 幾乎恆定，純整數路徑 |
| EKF `soc_ekf` | **平均 16,076**（範圍 15,849–16,317，n=61） | ≈ 251 µs | 含 OCV 查表＋float 矩陣運算；OCV 表仍為佔位，但 cycle 數與表值無關 |
| 動態阻抗 `soc_zdyn` 事件更新 | **≈ 2,873–3,169**（6 個事件） | ≈ 47 µs | ΔV/ΔI 二次式反解＋三層選根，僅事件當秒 |
| 動態阻抗 非事件秒 | ≈ 409–550（偶見 ~1,100–1,240） | ≈ 7 µs | 內建 float 庫倫內插＋事件窗檢查；~1.1k 為事件候選檢查路徑 |

三法相對成本：EKF ≈ 庫倫的 53 倍、≈ 動態阻抗事件更新的 5 倍；動態阻抗平時只花 ~7 µs，僅在電流階躍當秒付 ~47 µs。1 Hz 節拍下三法全開合計 < 0.03% CPU 佔用。

## 附帶觀察

- 脈衝期間量得動態阻抗 Z ≈ 39.7 mΩ、靜置 38.4 mΩ；zdyn 反解 SOC ≈ 53.4%（用表 4-3 實測係數 a=20.2/b=−21.6/c=63.6 mΩ）
- EKF 以佔位 OCV 表回報 ≈ 60%（vs 庫倫 99.8%）——**印證佔位表不可用於精度評估**，待 GITT 建真表後重測（4.2.5）
- 心跳 1 Hz 抖動 ±5.4 ms、計數單調；INA226 present、cal=on
- `SCRIPTS/flash_and_verify.py` 的 heartbeat regex 已修正（韌體新增 `Ical=` 欄位造成 V/I/P 檢核誤判 FAIL），修後對實測行驗證通過

## 資料來源

- UART 原始輸出：本次 session 現場擷取（脈衝段完整記錄於對話 log；如需 CSV 級 trace 可重跑觸發腳本）
- 韌體 commit：`7ee1ec4` 之後的工作樹（三法模組已入 USER_CODE）
