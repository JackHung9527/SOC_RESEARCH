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

### 2026/04/14

#### ✅ 完成項目
- 盤點 SOC_RESEARCH 資料夾內所有檔案，整理檔案清單與分類
- 刪除重複的 3 篇參考論文 PDF（根目錄與 meeting_0326 參考資料夾各一份）
- 建立 DOC / MCU 兩個主要資料夾
- 將所有文件依性質分類搬入 DOC 子資料夾（參考論文、論文簡報、會議紀錄、主題簡報）
- 建立專案 CLAUDE.md，記錄專案概述、資料夾結構、研究主題與慣例

#### 📋 明日待辦
- 開始規劃 MCU 資料夾內的韌體架構與程式碼開發
