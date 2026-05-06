/*
 * @brief  INA226 驅動實作。
 *         以 HAL I2C blocking API 完成 16-bit 暫存器讀寫
 *         (大端序：高位在前)，並提供量測值換算到 SI 單位的封裝函式。
 */

#include "ina226.h"
#include <stddef.h>

#define INA226_I2C_TIMEOUT_MS  (100U)

/*
 * @brief  寫入 INA226 16-bit 暫存器（內部使用）。
 *         參數說明：
 *           - h     : 驅動 handle
 *           - reg   : 暫存器位址 (0x00 ~ 0xFF)
 *           - value : 欲寫入的 16-bit 值，內部會轉成大端序
 */
static bool ina226_write_reg(ina226_handle_t *h, uint8_t reg, uint16_t value)
{
    if ((h == NULL) || (h->hi2c == NULL))
    {
        return false;
    }

    uint8_t buf[3] = {reg,
                      (uint8_t)((value >> 8) & 0xFFU),
                      (uint8_t)(value & 0xFFU)};

    HAL_StatusTypeDef st = HAL_I2C_Master_Transmit(h->hi2c,
                                                   (uint16_t)((uint16_t)h->i2c_addr_7b << 1),
                                                   buf, 3U, INA226_I2C_TIMEOUT_MS);
    return (st == HAL_OK);
}

/*
 * @brief  讀取 INA226 16-bit 暫存器（內部使用）。
 *         參數說明：
 *           - h     : 驅動 handle
 *           - reg   : 暫存器位址 (0x00 ~ 0xFF)
 *           - value : 輸出指標，存回 16-bit 值（大端序已轉換為主機序）
 */
static bool ina226_read_reg(ina226_handle_t *h, uint8_t reg, uint16_t *value)
{
    if ((h == NULL) || (h->hi2c == NULL) || (value == NULL))
    {
        return false;
    }

    uint16_t addr_8b = (uint16_t)((uint16_t)h->i2c_addr_7b << 1);
    uint8_t  reg_addr = reg;

    if (HAL_I2C_Master_Transmit(h->hi2c, addr_8b, &reg_addr, 1U,
                                INA226_I2C_TIMEOUT_MS) != HAL_OK)
    {
        return false;
    }

    uint8_t rx[2] = {0U, 0U};
    if (HAL_I2C_Master_Receive(h->hi2c, addr_8b, rx, 2U,
                               INA226_I2C_TIMEOUT_MS) != HAL_OK)
    {
        return false;
    }

    *value = (uint16_t)(((uint16_t)rx[0] << 8) | (uint16_t)rx[1]);
    return true;
}

bool ina226_verify_id(ina226_handle_t *h)
{
    uint16_t mfg_id = 0U;
    uint16_t die_id = 0U;

    if (!ina226_read_reg(h, INA226_REG_MANUFACTURER_ID, &mfg_id))
    {
        return false;
    }
    if (!ina226_read_reg(h, INA226_REG_DIE_ID, &die_id))
    {
        return false;
    }

    return ((mfg_id == INA226_MANUFACTURER_ID_VAL) &&
            (die_id == INA226_DIE_ID_VAL));
}

bool ina226_write_calibration(ina226_handle_t *h)
{
    if ((h == NULL) || (h->shunt_ohm <= 0.0F) || (h->current_lsb_a <= 0.0F))
    {
        return false;
    }

    // CAL = 0.00512 / (Current_LSB * Rshunt)，datasheet 7.5.2
    float cal_f = 0.00512F / (h->current_lsb_a * h->shunt_ohm);
    if ((cal_f < 1.0F) || (cal_f > 65535.0F))
    {
        return false;
    }

    uint16_t cal = (uint16_t)cal_f;
    return ina226_write_reg(h, INA226_REG_CALIBRATION, cal);
}

bool ina226_init(ina226_handle_t *h, ina226_avg_t avg, ina226_ct_t bus_ct,
                 ina226_ct_t shunt_ct, ina226_mode_t mode)
{
    if ((h == NULL) || (h->hi2c == NULL))
    {
        return false;
    }

    if (!ina226_verify_id(h))
    {
        return false;
    }

    // 組合 CONFIG 暫存器；保留位元 14 維持 1 (reset value)
    uint16_t cfg = INA226_CONFIG_RESERVED_BIT
                 | (uint16_t)(((uint16_t)avg & 0x7U) << 9)
                 | (uint16_t)(((uint16_t)bus_ct & 0x7U) << 6)
                 | (uint16_t)(((uint16_t)shunt_ct & 0x7U) << 3)
                 | (uint16_t)((uint16_t)mode & 0x7U);

    if (!ina226_write_reg(h, INA226_REG_CONFIG, cfg))
    {
        return false;
    }

    return ina226_write_calibration(h);
}

bool ina226_read_bus_voltage_mv(ina226_handle_t *h, float *bus_v_mv)
{
    if (bus_v_mv == NULL)
    {
        return false;
    }

    uint16_t raw = 0U;
    if (!ina226_read_reg(h, INA226_REG_BUS_V, &raw))
    {
        return false;
    }

    // Bus V LSB = 1.25 mV → mV = raw * 1.25
    *bus_v_mv = (float)raw * 1.25F;
    return true;
}

bool ina226_read_shunt_voltage_uv(ina226_handle_t *h, float *shunt_v_uv)
{
    if (shunt_v_uv == NULL)
    {
        return false;
    }

    uint16_t raw_u = 0U;
    if (!ina226_read_reg(h, INA226_REG_SHUNT_V, &raw_u))
    {
        return false;
    }

    int16_t raw_s = (int16_t)raw_u;
    // Shunt V LSB = 2.5 µV → µV = raw_s * 2.5
    *shunt_v_uv = (float)raw_s * 2.5F;
    return true;
}

bool ina226_read_current_ma(ina226_handle_t *h, float *current_ma)
{
    if ((h == NULL) || (current_ma == NULL))
    {
        return false;
    }

    uint16_t raw_u = 0U;
    if (!ina226_read_reg(h, INA226_REG_CURRENT, &raw_u))
    {
        return false;
    }

    int16_t raw_s = (int16_t)raw_u;
    // I (A) = raw * Current_LSB → 轉 mA 乘 1000
    *current_ma = (float)raw_s * h->current_lsb_a * 1000.0F;
    return true;
}

bool ina226_read_power_mw(ina226_handle_t *h, float *power_mw)
{
    if ((h == NULL) || (power_mw == NULL))
    {
        return false;
    }

    uint16_t raw = 0U;
    if (!ina226_read_reg(h, INA226_REG_POWER, &raw))
    {
        return false;
    }

    // Power_LSB = 25 * Current_LSB (W) → 轉 mW 乘 1000
    *power_mw = (float)raw * 25.0F * h->current_lsb_a * 1000.0F;
    return true;
}
