/*
 * soc_ekf.h — 擴展卡爾曼濾波器 SOC 估測（論文 4.2；圖 4-2 預測—更新遞迴）。
 *
 * 模型：一階 RC（戴維寧），狀態 x = [SOC, V1]ᵀ、輸入 I（放電為正）、觀測 V_t：
 *     SOC_{k+1} = SOC_k − (Δt/C_rated)·I_k
 *     V1_{k+1}  = e^{−Δt/τ1}·V1_k + R1(1−e^{−Δt/τ1})·I_k      （ZOH 精確離散化）
 *     V_t,k     = V_OC(SOC_k) − I_k·R0 − V1_k
 *
 * 嵌入式實作重點（4.2.4）：
 *   - 狀態 2 維、觀測 1 維 → 增益只需一次純量除法、免矩陣求逆。
 *   - 協方差更新採 Joseph 形式（數值穩定，長時間運行不發散）。
 *   - V_OC(SOC) 以分段線性 OCV 表內插（soc_ekf_ocv_table.h），
 *     雅可比 ∂V_OC/∂SOC 取該段斜率。
 *   - G071 無 FPU：全程軟浮點，為三法中每次更新運算量最高者（4.4.3 待量測）。
 *
 * 參數（R0/R1/τ1、Q/R）目前為 model_set.h 佔位值，標 [待測]；
 * 待 PC 端原型以擾動段最小平方辨識後回填。
 */

#ifndef SOC_EKF_H_
#define SOC_EKF_H_

#include <stdint.h>

void  soc_ekf_init(void);                       /* 以 model_set 預設初值/協方差起步 */
void  soc_ekf_seed_from_voltage(float v_mv);    /* 開機近似靜置時，以 OCV 反查播種初始 SOC */
void  soc_ekf_set_soc(float soc_pct);           /* 強制設初值（強健性測試用，0..100） */
void  soc_ekf_update_1s(float i_ma, float v_mv);/* 每秒一次預測—更新（放電為正） */

/* 靈敏度加權融合（§3）：以動態阻抗法之閘控 SOC 觀測做額外一次量測更新。
 * 觀測方程 z = SOC（C = [1, 0]），r_var 為該觀測之量測變異數（SOC-frac²，
 * 由 soc_zdyn 依局部靈敏度導出）；純量增益、Joseph form 更新協方差。
 * 只在有通過閘控之擾動事件的 tick 呼叫（見 soc_zdyn_take_gated_event）。 */
void  soc_ekf_correct_soc(float soc_frac, float r_var);

float soc_ekf_get_soc_pct(void);                /* 目前估測 SOC（0..100） */
float soc_ekf_get_v1_mv(void);                  /* 極化電壓狀態 V1（mV，診斷用） */

#endif /* SOC_EKF_H_ */
