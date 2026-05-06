/*
 * @brief  SOC/SOH 演算法骨架實作。
 *         目前僅做基本算式（ΔV / ΔI、Coulomb 比值），
 *         查表與溫度補償係數需待校正流程後再代入。
 *         本檔內所有 TODO 標記皆對應「校正先 pending」決議。
 */

#include "soc_soh_calc.h"
#include <math.h>

bool soc_calc_dynamic_impedance(const battery_sample_t *sample_before,
                                const battery_sample_t *sample_after,
                                soc_soh_result_t *result)
{
    if ((sample_before == NULL) || (sample_after == NULL) || (result == NULL))
    {
        return false;
    }
    if (!sample_before->is_valid || !sample_after->is_valid)
    {
        return false;
    }

    float delta_v_mv = sample_after->bus_v_mv  - sample_before->bus_v_mv;
    float delta_i_ma = sample_after->current_ma - sample_before->current_ma;

    if (fabsf(delta_i_ma) < 1.0F) // 注入電流變化過小，放棄本次量測
    {
        return false;
    }

    // Z (mΩ) = (ΔV mV) / (ΔI A) = (ΔV mV) / (ΔI mA / 1000) = ΔV / ΔI * 1000
    result->z_mohm = (delta_v_mv / delta_i_ma) * 1000.0F;

    // TODO[校正 pending]：以實機 Z-SOC 對應表 (LUT) 反查 SOC
    //                  目前回傳 -1 代表尚未校正
    result->soc_percent = -1.0F;
    result->confidence  = 0.0F;
    return true;
}

bool soh_calc_projection(float cumulative_charge_mah,
                         float nominal_capacity_mah,
                         float temperature_c,
                         soc_soh_result_t *result)
{
    if ((result == NULL) || (nominal_capacity_mah <= 0.0F))
    {
        return false;
    }

    (void)temperature_c; // TODO[校正 pending]：溫度補償係數待擬合

    float ratio = cumulative_charge_mah / nominal_capacity_mah;
    if (ratio < 0.0F)
    {
        ratio = 0.0F;
    }
    if (ratio > 1.0F)
    {
        ratio = 1.0F;
    }

    result->soh_percent = ratio * 100.0F;
    result->confidence  = 0.0F; // TODO[校正 pending]：信心度模型待補
    return true;
}
