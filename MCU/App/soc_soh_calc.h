/*
 * @brief  SOC/SOH 演算法骨架（待補實作）。
 *         本模組對應論文 Lin et al. 2016「Implementation of SOC and SOH
 *         Estimation for Lithium-ion Batteries」中的兩個方法：
 *           - 動態阻抗法 (Dynamic Impedance Method) → SOC
 *           - 投影法 (Projection Method)            → SOH
 *         目前僅提供 API 與資料結構占位；
 *         實際係數、查表、擬合公式皆待校正流程啟動後填入。
 *         欄位說明：
 *           - soc_percent  : State of Charge，單位 %，範圍 0.0 ~ 100.0
 *           - soh_percent  : State of Health，單位 %，範圍 0.0 ~ 100.0
 *           - z_mohm       : 電池內阻動態量測值，單位 mΩ
 *           - confidence   : 估計信心度，範圍 0.0 ~ 1.0
 */

#ifndef SOC_SOH_CALC_H
#define SOC_SOH_CALC_H

#include <stdint.h>
#include <stdbool.h>
#include "battery_monitor.h"

typedef struct
{
    float soc_percent;
    float soh_percent;
    float z_mohm;
    float confidence;
} soc_soh_result_t;

/*
 * @brief  動態阻抗法估計 SOC。
 *         需先以外部 DC load 注入已知電流脈衝（典型 0.5C，250 ms），
 *         前後分別取樣，計算 ΔV / ΔI 得到動態阻抗 Z，再以
 *         Z-SOC 查表（待校正）反推 SOC。
 *         參數說明：
 *           - sample_before : 脈衝前樣本（穩態）
 *           - sample_after  : 脈衝後樣本（注入後 t = 250 ms）
 *           - result        : 輸出指標，soc_percent 與 z_mohm 會被填寫
 */
bool soc_calc_dynamic_impedance(const battery_sample_t *sample_before,
                                const battery_sample_t *sample_after,
                                soc_soh_result_t *result);

/*
 * @brief  投影法估計 SOH。
 *         以累積放電容量 (Coulomb counting) 對比出廠標稱容量，
 *         加上溫度補償後得到健康度。
 *         參數說明：
 *           - cumulative_charge_mah  : 此次放電累積電量，單位 mAh
 *           - nominal_capacity_mah   : 出廠標稱容量，單位 mAh
 *           - temperature_c          : 量測時平均溫度，單位 °C
 *           - result                 : 輸出指標，soh_percent 會被填寫
 */
bool soh_calc_projection(float cumulative_charge_mah,
                         float nominal_capacity_mah,
                         float temperature_c,
                         soc_soh_result_t *result);

#endif /* SOC_SOH_CALC_H */
