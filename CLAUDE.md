# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SOC_RESEARCH is a research project focused on **battery State-of-Charge (SOC) and State-of-Health (SOH) estimation methods**. The research covers lead-acid batteries, lithium-ion batteries, Kalman filtering, neural network approaches, and LFP battery hysteresis modeling.

The project is transitioning from a pure documentation/literature review phase into MCU firmware implementation.

## Repository Structure

- **DOC/** — All research documentation, organized into:
  - `參考論文/` — Original reference papers (PDF), 3 papers covering lead-acid SoH/SoC, lithium-ion SOC/SOH, and multilayer neural network methods
  - `論文簡報/` — Chinese and English summaries of the reference papers (DOCX)
  - `會議紀錄/` — Meeting presentations (PPTX) named as `meeting_MMDD_洪大甲`, plus related materials
  - `主題簡報/` — Topic-specific presentations on SOC/Kalman filter concepts and LFP hysteresis modeling
  - `校正紀錄/` — Instrument calibration logs (INA226 multi-point LUT etc.)
  - `論文撰寫/` — Thesis outline + official templates (`論文大綱.md` is source of truth)
  - `分析紀錄/` — **Self-contained analysis reports on test data**. Each report is dated and points to source CSVs; new conversations should read these to resume context. Currently: `2026-05-18_rate_capability_and_R_analysis.md`
- **TEST/** — Bench automation: round_runner, GITT runner, drivers (IT6302/IT8512/INA226), and `data/` containing per-cycle CSV traces + `cycle_log.csv` aggregate metadata
- **MCU/** — Reserved for embedded firmware code (currently empty, pending implementation)

## Research Topics

- Lead-acid battery SoH/SoC measurement design and implementation
- Lithium-ion battery SOC/SOH estimation techniques
- Multilayer neural network-based SOC estimation and SOH diagnosis
- Kalman filter for SOC estimation
- LFP battery hysteresis modeling and SOC compensation

## Conventions

- File naming for meetings: `meeting_MMDD_洪大甲` format
- All documentation and communication in **Traditional Chinese (繁體中文)**
- When MCU code is added, follow MISRA C standards (see global CLAUDE.md for detailed C coding rules)

---

## 今日總結

### 2026/06/11（下午　論文全面修訂）

#### ✅ 完成項目
- 第四章演算法／實作改用正式圖檔（matplotlib 產生，存 `論文撰寫/figures/`）：圖4-1 庫倫流程、圖4-2 EKF 預測-更新遞迴、圖4-3 動態阻抗離線建表+即時估測流程、圖4-4 動態阻抗實測擬合；移除含實作術語（64-bit 累加器等）的資料流圖
- 戴維寧等三種等效電路畫成圖2-1（電路示意圖：內阻／一階RC／二階RC）
- **動態阻抗係數實測算出**（fresh rounds 1–3 擾動段）：合併 a=20.2、b=−21.6、c=63.6 mΩ，最低點 SOC≈53%（符合理論50%），高倍率擬合殘差低至0.5mΩ、低倍率3.5mΩ（印證SNR說法），填入表4-3
- 庫倫積分公式取消庫倫效率 η（Ch2 2.2.1、Ch4 4.1.1／4.2.1）
- 移除資料驅動法／神經網路（Ch2 2.2.5＋分類改兩類＋2.4表；Ch1 分類／未來工作）
- 「Lin」不以人名表示，全部改文獻編號 [n]
- 取消 Ch3 3.5 BenchInterlock、3.7 GITT，章節重新編號（3.6→3.5），表3-4 改成易懂的「一組四步驟、只差放電倍率」排版
- 3.2 韌體骨架、4.1.3／4.2.4／4.3.4 實作節改寫成淺顯白話、不放程式變數名（面向非程式背景讀者）
- 參考文獻：移除 Lee(NN)，重新編號，補入 Plett(EKF)／He(ECM)／Weppner(GITT) 真實出處（卷期頁碼標待核對）
- 建置腳本升級支援圖片嵌入＋docx 參考文獻區塊更新，重建 `_20260611.docx`（5 圖、5 參考文獻、14 表）

#### 🐛 問題與踩坑
- matplotlib 中文用 Microsoft JhengHei；缺字（≈、−、ᵀ）需改寫或以線段繪製；數學式用 mathtext(stix) 排版乾淨
- 本機 `python`(Desktop/.venv) 無 python-docx，需用 `C:\...\Python312\python.exe` 跑

#### ✅ 補完成（傍晚續工）
- **docx 第一章已同步**：`build_thesis.py` 升級為「Ch1 也從 `第一章_緒論.md` 重建」（移除 pristine 舊正文、保留其後參考文獻區塊再更新）；驗證 Ch1–4 已無 NN／資料驅動／Lin 等人／庫倫效率／round_runner／heartbeat／soc_soh_calc，內文引用編號 [1]–[5] 一致
- 圖3-1 系統架構改成正式圖檔（`figures/fig3-1.png`），docx 共 6 張圖（圖2-1、3-1、4-1～4-4）
- Ch4 4.0、4.1.4、Ch3 3.1 殘留術語淺顯化（去 soc_soh_calc／100µs／heartbeat／round_runner／cycle_log 等）
- 踩坑：python-docx `doc.paragraphs` 每次回傳新 wrapper，段落比對要用 `p._p is x._p`（XML 元素身分），不能用 `p is x`
- **動態阻抗「反推 SOC」逐點精度實測算出**：用表4-3 係數把阻抗反解成 SOC、與庫倫真值比（oracle 分枝），各倍率 RMSE 約 6～10%（0.5C 9.7%、2.0C 6.3%）；SOC 中段40-60% 較差（9-13%）、兩端較小（5-9%），印證拋物線中段平緩→反推病態；rounds1-2擬合/round3留出驗證 RMSE 7-10% 相當（非過擬合）。填入表4-3 末欄、表4-4 動態阻抗列，並補進 4.3.4／4.5 內文

- 中文摘要＋英文 Abstract＋雙語關鍵詞已撰寫並填入 docx 前置頁（誠實版：只陳述已完成實測，EKF/footprint 不報數字）；建置腳本加 `fill_placeholder()` 取代佔位

#### 📋 還沒做完（明日待辦）
- EKF（4.2.5）精度、三方法 footprint（4.4）仍為 [待測]（需先建 GITT OCV 表、做 EKF 原型與移植）
- 誌謝（個人內容）、封面三項（研究生姓名／系所全名／指導教授，需使用者提供）、第五六章內文
- docx 待 Word 視覺確認；數學式仍線性近似，待方程式編輯器重排
- 動態阻抗「以擬合反推 SOC」的逐點精度尚未計算（目前只算了擬合係數本身）
- docx 尚未經 Word 視覺確認（本機無 PDF 轉檔工具）；數學式仍為線性近似，待 Word 方程式編輯器重排
- 摘要／Abstract／誌謝／封面三項、第五六章內容仍待寫

### 2026/06/11（上午　第四章初稿）

#### ✅ 完成項目
- 撰寫第四章完整草稿 `第四章_SOC估測方法之實作與比較.md`：4.0 共同前提（SOC 真值界定、比較指標符號）、4.1 庫倫計數（兼 ground truth）、4.2 EKF（一階 RC、狀態 2 維、增益免矩陣求逆、GITT OCV 表觀測方程）、4.3 動態阻抗（複用 dV/dI 擾動、二次擬合＋分枝選根）、4.4 三軸比較框架、4.5 小結
- 嚴格區分實測與待測：rate-capability 真實數據入文（rounds 1–23，0.5C→2.0C 容量僅降約 1%、跨輪再現性佳）；EKF／動態阻抗／footprint 數值一律標 `[待測]` 紅字佔位，不虛構任何 RMSE
- 第二、三、四章全部併入論文主檔，產出 `鋰電池SOC估測方法之比較與嵌入式實作_20260611.docx`（549 段、15 表），格式逐項比照第一章（節標題粗體 14pt 靠左、內文標楷體 12pt 首行縮排兩端對齊、表頭淺藍底）；原主檔未動
- 建立 md→docx 轉換管線（python-docx）：markdown 解析（標題／內文／表格／公式／程式碼／註記／表標題）＋ LaTeX→unicode 線性近似 ＋ 表格自動配寬與框線
- 依使用者要求把內文行距 18pt → 24pt（181 段），標題／表格／註記／程式碼維持原樣

#### 🐛 問題與踩坑
- LaTeX 轉換器 `\in` 規則先吃掉 `\int` 產生「∈t」亂碼；`\dfrac` 未涵蓋——改用整字 regex（`\\([a-zA-Z]+)` 查表）＋ dfrac 正規化 ＋ 殘留花括號清除解決
- docx skill 的 `soffice.py` 在 Windows 用 `socket.AF_UNIX` 直接 AttributeError，PDF 視覺驗證不可行；`validate.py` 缺 `defusedxml`——改用 python-docx 做結構驗證（章界、樣式、表格 shape 抽查）
- python-docx 對混排插入要用 `cursor.addnext(element)` 逐塊推進，表格（`w:tbl`）與段落（`w:p`）才能保持原文順序

#### 📋 明日待辦
- 撰寫摘要／Abstract／誌謝內容、補封面三項（研究生姓名、系所全名、指導教授）
- 第五、六章內容撰寫（主檔仍為佔位）
- 第四章 `[待測]` 實驗排程：GITT OCV 表建立、EKF PC 原型、動態阻抗離線擬合
- Word 內數學式改方程式編輯器重排；圖 3-1／3-2 ASCII 圖改繪正式向量圖

### 2026/06/03

#### ✅ 完成項目
- 確立碩論主題銳化方向：以「嵌入式資源約束下的 SOC 演算法精度-成本權衡」為論文記憶點，三方法（庫倫計數／EKF／動態阻抗）退為實驗載體，避開「純比較缺乏新穎性」的口試攻擊
- 撰寫第一章緒論完整內文：1.1 研究背景、1.2 研究動機（兩個 research gap：評估環境失真、benchmark 不公平）、1.3 研究目的與貢獻（三點）、1.4 論文架構，含三篇參考文獻（Lin 2016／Bressanini 2017／Lee et al.）
- 基於中原官方 Word 範本產出論文主檔：封面（中英題目、碩士學位論文、民國 115 年）＋ 摘要／Abstract／誌謝佔位框架 ＋ 第一～六章框架
- 緒論內文併入主檔第一章，套正式論文格式（節標題粗體靠左、內文標楷體 12pt 首行縮排兩端對齊、貢獻編號、參考文獻懸掛縮排）
- 改為單一 Word 檔持續更新模式（`鋰電池SOC估測方法之比較與嵌入式實作.docx`），刪除日期版本快照（原 `_YYMMDDnn` 命名）
- 清除範本殘留：TOC／TOF 教學快取、9 張孤兒教學截圖（742 KB → 31 KB）、格式說明表

#### 🐛 問題與踩坑
- Windows cp950 codec 在 docx `validate.py` 誤判合法 UTF-8 XML 為非法多位元組，用 `PYTHONUTF8=1` 解決
- python-docx 刪段落（`w:p`）不會刪表格（`w:tbl`），範本「格式說明表」漏刪，改用 `d.tables` 定位刪除
- 範本章標題實際是 Normal＋手動格式（非 Heading 1 樣式），定位正文教學區要用文字比對而非樣式名
- 開檔跳「功能變數可能參考其他檔案」警語，根因是 TOC field 被標記 `dirty="true"`，移除 dirty 即不再跳（並把目錄快取填回六章避免空白）
- pandoc／pdftoppm 未安裝，改用 python-docx ＋ pypdf 處理 docx／pdf

#### 📋 明日待辦
- 將第二章、第三章草稿併入主檔
- 補封面三項（研究生姓名、系所全名、指導教授）
- 撰寫摘要／Abstract／誌謝內容

### 2026/05/12

#### ✅ 完成項目
- 重寫 `round_runner.py` charge step 充飽判斷：條件 `V≥V_cv−100mV` 且 `I≤0.1C` 須**連續滿足 3 秒** + 總 elapsed ≥ 30s，避免 t=0 單點誤觸發
- 新增 already-full bypass：cell 起步 5 秒視窗內若 `V≥V_cv−30mV` 且 `I<50mA` 且未進過 CC，整個 charge step 跳過（log `note=already_full`），免去隔夜飽電 cell 又跑無意義 CV taper
- 把所有充飽 knob 集中到 `run_charge_step` 開頭（`v_term_margin` / `i_term` / `t_term_min` / `term_hold_s` / `full_v_margin` / `full_i_max` / `full_window_s`），附 comment block 解釋兩條路徑
- bypass 視窗期間每秒印一行狀態，避免 30s `_live_print` 間距讓操作者誤判程式卡住
- 修 BenchInterlock 的 `_psu_off_verified`：從「sleep 100ms 後 hard check」改為「**polling 最多 2 秒、提早通過就走**」，每 150ms 量一次 `MEAS:CURR?`

#### 🐛 問題與踩坑
- 第一次 round_runner 跑 step 1 (charge 0.5C) 在 t=0 就 `term` 結束：cell 隔夜 OCV≈4.19V，距 V_cv 只剩 10 mV，I=0（PSU 還沒 ramp）→ 條件瞬間成立，整個 charge step 跳過、ah_in=0
- bypass 第一版 window=3s 在 1 Hz sampling 下只看 3 筆 sample，PSU output 短暫尖峰會打成 `full_seen_break=True`，bypass 被否決且 `cc_entered` 又永遠到不了 → loop 卡死。修法：延 window 到 5s + normal term 解除 `cc_entered` 依賴，改用 30s settle time
- term 觸發後立刻下 `CHAN:OUTP OFF`，100ms 後 `MEAS:CURR?` 仍回 0.1021A（term 時是 0.1041A，僅掉 2 mA），BenchInterlock 50 mA 門檻誤判 PSU 沒關 → emergency stop。根因：IT6302 內部 A/D 約 1-2 Hz，頭幾筆 MEAS 還在回 OFF 前的 cache

#### 📋 明日待辦
- 重跑 round 1 確認 charge step 能正常 term + interlock 通過
- 觀察 cycle_log.csv 的 0.5C cycle `q_retention_pct`（cell baseline 是否 95-100%）
- 若 polling 2s 仍過不了，補上 `VOLT 0` + `CURR 0` 再 OFF 的激進手段，並考慮把 OFF 後第一次 MEAS 結果直接丟掉（強制 flush stale cache）

---

### 2026/05/11

#### ✅ 完成項目
- 完成 INA226 多點線性內插校正：充放電各 7 點（0/0.05/0.1/0.5/1.0/1.5/2.0 A），全範圍誤差 < 0.21 mA（< 1‰）
- 把 14 點 LUT 經 UART CLI 燒進 STM32 flash page 63（0x0801_F800），開機自動載入，heartbeat 多吐 `cal=on` 與 `Ical=`
- 撰寫校正紀錄文件：`DOC/校正紀錄/2026-05-07_ina226_calibration.md` + `2026-05-07_ina226_validation.json`（4 點內插驗證資料）
- 設計並實作跨輪測試協定 `TEST/round_runner.py`：一輪 = 充 0.5C →休30m →放 {0.5/1.0/1.5/2.0}C →休30m，共 4 個放電 cycle
- 加入持久化 `cycle_log.csv`：記錄 cycle_id、round_id、q_retention_pct、cumulative_ah；跨次執行自動續接 round_id
- 為所有 4 個放電 rate 加入 dV/dI 擾動（每 60s 步進到 0.2C dwell 1s），庫倫計數涵蓋擾動秒數避免 ~3% undercount
- 設定當前電池 profile：custom NMC 2000 mAh，V_cv=4.2V，V_cutoff=2.5V，max discharge 4A

#### 🐛 問題與踩坑
- IT6302 `APPL V,I` 對連續寫入不可靠更新 CURR，round_runner 首次充電灌出 2A 而非 1A（校正腳本曾踩過同坑卻沒套用紀律），修法：分開 `set_voltage`+`set_current` + `CURR?` readback 驗證
- 第一版 round_runner 為求 V(SoC) 純淨度移除擾動，使用者反映「動態內阻沒被記錄」後補上；對所有 4 rate 採是因為高 C 的 ΔI 反而給更好 dV/dI SNR

#### 📋 明日待辦
- 今晚 22:00 啟動第一輪 rate-capability round（預估 ~18h），明日下午結束
- 觀察 cycle_log.csv 中 0.5C cycle 的 q_retention 是否落在 95-100%（驗證電池實際容量 vs 標稱）
- 累積 3 輪 fresh-cell baseline 後計算輪間 a_origin 變異性，數據過了才進 Phase 4 老化測試

---

### 2026/04/14 (updated)

#### ✅ 完成項目
- 初始化 git repository 並推送至 GitHub (JackHung9527/SOC_RESEARCH)
- 安裝 PPTX Skill（從 anthropics/skills 下載完整 scripts、schemas、validators）
- 安裝相依套件：markitdown[pptx]、Pillow、defusedxml、pptxgenjs、react-icons、sharp
- 研讀論文「Implementation of SOC and SOH Estimation for Li-ion Batteries」(Lin et al., 2016)
- 規劃 MCU 驗證方案：動態阻抗法 SOC + 投影法 SOH，搭配 IT6302 / IT8512A+ / STM32 / INA226
- 產生 10 頁驗證計畫簡報 meeting_0416_洪大甲.pptx（PptxGenJS）並推送至 GitHub

#### 🐛 問題與踩坑
- markitdown 預設不含 PDF 支援，需額外安裝 markitdown[pdf]
- npm 全域安裝的 pptxgenjs 需設定 NODE_PATH 才能在 node 中 require
- bash heredoc 含中文單引號時產生 EOF 錯誤，改用 Write 工具寫入 .js 檔再執行

#### 📋 明日待辦
- 開始 MCU 韌體架構設計（STM32 + INA226 I2C 驅動）
- 準備硬體接線與 INA226 校準實驗

---

### 2026/04/14 (initial)

#### ✅ 完成項目
- 盤點 SOC_RESEARCH 資料夾內所有檔案，整理檔案清單與分類
- 刪除重複的 3 篇參考論文 PDF（根目錄與 meeting_0326 參考資料夾各一份）
- 建立 DOC / MCU 兩個主要資料夾
- 將所有文件依性質分類搬入 DOC 子資料夾（參考論文、論文簡報、會議紀錄、主題簡報）
- 建立專案 CLAUDE.md，記錄專案概述、資料夾結構、研究主題與慣例

#### 📋 明日待辦
- 開始規劃 MCU 資料夾內的韌體架構與程式碼開發
