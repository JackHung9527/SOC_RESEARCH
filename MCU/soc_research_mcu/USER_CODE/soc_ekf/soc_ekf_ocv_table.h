/*
 * soc_ekf_ocv_table.h — pseudo-OCV 對照表 V_OC(SOC)。
 *
 * ✔ GITT 實測表（2026-07-05 執行，TEST/gitt_ocv_runner.py，放電單向、
 *   5% 步進 × 30 min 鬆弛）。來源點：summary 之 v_eq（SoC 4.88%–100%，
 *   含滿電 CV 後 30 min 鬆弛之 100% 錨點）。
 *
 * 量測範圍注意：
 *   - SoC < 4.88% 無實測點（末步觸 2.5 V 化學下限中止），0% 節點為
 *     邊界外插（近似持平），該段雅可比偏小，低 SoC 收斂較慢屬預期。
 *   - 100% 節點因邊緣平滑略低於實測錨點（4.1630 vs 4.1752 V）。
 *
 * 重生方式（會整檔覆寫 OCV_TABLE marker 之間內容）：
 *     python3 SCRIPTS/gen_ocv_header.py TEST/data/ocv_table_20260705_215850.csv \
 *         --out MCU/soc_research_mcu/USER_CODE/soc_ekf/soc_ekf_ocv_table.h
 *
 * 表規格：SOC 等距 5% × 21 點、V 單位 V；MCU 端分段線性內插（4.2.2），
 * 雅可比 ∂V_OC/∂SOC 取該段斜率。離線產生時已可先做 1% 細化＋平滑再
 * 重取 5% 節點，使斜率連續性足夠（細節見論文 4.2.4）。
 */

#ifndef SOC_EKF_OCV_TABLE_H_
#define SOC_EKF_OCV_TABLE_H_

/* === OCV_TABLE BEGIN (auto-generated region; gen_ocv_header.py 覆寫) === */
/* source: ocv_table_20260705_215850.csv  col=v_pseudo_ocv  step=5%  smooth=5 */
#define SOC_EKF_OCV_N  21U

/* SOC 節點（0..1 分數，等距 5%） */
static const float SOC_EKF_OCV_SOC[SOC_EKF_OCV_N] =
{
    0.0000f, 0.0500f, 0.1000f, 0.1500f, 0.2000f, 0.2500f, 0.3000f, 0.3500f, 0.4000f, 0.4500f,
    0.5000f, 0.5500f, 0.6000f, 0.6500f, 0.7000f, 0.7500f, 0.8000f, 0.8500f, 0.9000f, 0.9500f,
    1.0000f
};

/* V_OC（V）— GITT 實測（ocv_table_20260705_215850.csv） */
static const float SOC_EKF_OCV_V[SOC_EKF_OCV_N] =
{
    3.2206f, 3.2535f, 3.4422f, 3.4917f, 3.5156f, 3.5556f, 3.5884f, 3.6146f, 3.6355f, 3.6549f,
    3.6777f, 3.7057f, 3.7398f, 3.7815f, 3.8381f, 3.9029f, 3.9550f, 4.0056f, 4.0586f, 4.1149f,
    4.1630f
};
/* === OCV_TABLE END === */

#endif /* SOC_EKF_OCV_TABLE_H_ */
