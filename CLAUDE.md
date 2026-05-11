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
