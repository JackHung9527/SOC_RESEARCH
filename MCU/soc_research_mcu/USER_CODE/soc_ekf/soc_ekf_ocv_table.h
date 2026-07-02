/*
 * soc_ekf_ocv_table.h — pseudo-OCV 對照表 V_OC(SOC)。
 *
 * ⚠ 目前為 **佔位表（PLACEHOLDER）**：GITT 量測（TEST/gitt_ocv_runner.py）
 *   尚未執行，下表為一般 NMC 化學之典型 OCV 形狀，僅供韌體開發與
 *   footprint 量測；**論文 4.2.5 精度數據不得以此表產生**。
 *
 * GITT 完成後用產生器回填（會整檔覆寫 OCV_TABLE marker 之間內容）：
 *     python3 SCRIPTS/gen_ocv_header.py <ocv_table_*.csv> \
 *         --out MCU/soc_research_mcu/USER_CODE/soc_ekf/soc_ekf_ocv_table.h
 *
 * 表規格：SOC 等距 5% × 21 點、V 單位 V；MCU 端分段線性內插（4.2.2），
 * 雅可比 ∂V_OC/∂SOC 取該段斜率。離線產生時已可先做 1% 細化＋平滑再
 * 重取 5% 節點，使斜率連續性足夠（細節見論文 4.2.4）。
 */

#ifndef SOC_EKF_OCV_TABLE_H_
#define SOC_EKF_OCV_TABLE_H_

/* === OCV_TABLE BEGIN (auto-generated region; gen_ocv_header.py 覆寫) === */
/* source: PLACEHOLDER (generic NMC shape) — awaiting GITT run */
#define SOC_EKF_OCV_N  21U

/* SOC 節點（0..1 分數，等距 5%） */
static const float SOC_EKF_OCV_SOC[SOC_EKF_OCV_N] =
{
    0.00f, 0.05f, 0.10f, 0.15f, 0.20f, 0.25f, 0.30f, 0.35f, 0.40f, 0.45f,
    0.50f, 0.55f, 0.60f, 0.65f, 0.70f, 0.75f, 0.80f, 0.85f, 0.90f, 0.95f,
    1.00f
};

/* V_OC（V）— PLACEHOLDER，待 GITT 實測回填 */
static const float SOC_EKF_OCV_V[SOC_EKF_OCV_N] =
{
    3.20f, 3.45f, 3.55f, 3.62f, 3.66f, 3.69f, 3.72f, 3.74f, 3.76f, 3.78f,
    3.80f, 3.83f, 3.86f, 3.90f, 3.94f, 3.98f, 4.02f, 4.06f, 4.10f, 4.15f,
    4.19f
};
/* === OCV_TABLE END === */

#endif /* SOC_EKF_OCV_TABLE_H_ */
