/*
 * @brief  電池監測應用層實作。
 *         以 static handle 集中管理 INA226 狀態與最近一筆樣本，
 *         避免上層需要傳遞狀態結構，簡化整合到 main loop 的步驟。
 */

#include "battery_monitor.h"
#include <string.h>

static ina226_handle_t  s_ina226 = {0};
static battery_sample_t s_latest = {0};
static bool             s_initialized = false;

bool battery_monitor_init(I2C_HandleTypeDef *hi2c,
                          float shunt_ohm,
                          float current_lsb_a)
{
    if ((hi2c == NULL) || (shunt_ohm <= 0.0F) || (current_lsb_a <= 0.0F))
    {
        return false;
    }

    s_ina226.hi2c          = hi2c;
    s_ina226.i2c_addr_7b   = INA226_I2C_ADDR_DEFAULT;
    s_ina226.shunt_ohm     = shunt_ohm;
    s_ina226.current_lsb_a = current_lsb_a;

    bool ok = ina226_init(&s_ina226,
                          INA226_AVG_16,
                          INA226_CT_1100US,
                          INA226_CT_1100US,
                          INA226_MODE_SHUNT_BUS_CONT);

    s_initialized = ok;
    (void)memset(&s_latest, 0, sizeof(s_latest));
    return ok;
}

bool battery_monitor_sample(void)
{
    if (!s_initialized)
    {
        return false;
    }

    battery_sample_t tmp = {0};
    tmp.timestamp_ms = HAL_GetTick();

    bool ok = true;
    ok &= ina226_read_bus_voltage_mv(&s_ina226, &tmp.bus_v_mv);
    ok &= ina226_read_shunt_voltage_uv(&s_ina226, &tmp.shunt_v_uv);
    ok &= ina226_read_current_ma(&s_ina226, &tmp.current_ma);
    ok &= ina226_read_power_mw(&s_ina226, &tmp.power_mw);

    tmp.is_valid = ok;
    s_latest = tmp;
    return ok;
}

bool battery_monitor_get_latest(battery_sample_t *out)
{
    if (out == NULL)
    {
        return false;
    }

    *out = s_latest;
    return s_latest.is_valid;
}
