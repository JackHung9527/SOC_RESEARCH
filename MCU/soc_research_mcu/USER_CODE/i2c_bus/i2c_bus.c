/*
 * i2c_bus.c
 * 由 stm32-i2c-scaffold 自動產生
 *
 * 周邊：I2C1（HAL handle = hi2c1）
 * Async transport：IT
 */

#include "global_includes.h"
#include <string.h>

extern I2C_HandleTypeDef hi2c1;

#define I2C_ADDR_SHIFT(a7)   ((uint16_t)((uint16_t)(a7) << 1))


/* ===== globals (state machine) ===== */
I2c_bus_TaskSel
    g_i2c_bus_taskSel = I2c_bus_TaskSel_TaskAwait;
I2c_bus_FlowSel
    g_i2c_bus_flowSel = I2c_bus_FlowSel_FlowAwait;

uint32_t
    g_i2c_bus_cmd     = _timxTick_cmd_start,
    g_i2c_bus_cnt     = 0;


/* ===========================================================================
 *  Lifecycle
 * ========================================================================= */
void i2c_bus_init(void)
{
}


void i2c_bus_handle(void)
{

    i2c_bus_TASK(&g_i2c_bus_taskSel, &g_i2c_bus_flowSel);
}


void i2c_bus_TASK(I2c_bus_TaskSel *task,
                          I2c_bus_FlowSel *flow)
{
    switch ((int)*task)
    {
        case I2c_bus_TaskSel_Service_Routine:
        {
            switch ((int)*flow)
            {
                case I2c_bus_FlowSel_finish:
                {
                    *task = I2c_bus_TaskSel_TaskAwait;
                    *flow = I2c_bus_FlowSel_FlowAwait;
                    break;
                }
                default:
                    *task = I2c_bus_TaskSel_TaskAwait;
                    *flow = I2c_bus_FlowSel_FlowAwait;
                    break;
            }
            break;
        }
        default:
            break;
    }
}


/* ===========================================================================
 *  Sync (blocking) API
 * ========================================================================= */
HAL_StatusTypeDef i2c_bus_read(uint8_t addr7, uint8_t *buf, uint16_t len)
{
    return HAL_I2C_Master_Receive(&hi2c1, I2C_ADDR_SHIFT(addr7),
                                  buf, len, I2C_BUS_TIMEOUT_MS);
}


HAL_StatusTypeDef i2c_bus_write(uint8_t addr7, const uint8_t *buf, uint16_t len)
{
    return HAL_I2C_Master_Transmit(&hi2c1, I2C_ADDR_SHIFT(addr7),
                                   (uint8_t *)buf, len, I2C_BUS_TIMEOUT_MS);
}


HAL_StatusTypeDef i2c_bus_read_reg(uint8_t addr7, uint8_t reg,
                                           uint8_t *buf, uint16_t len)
{
    return HAL_I2C_Mem_Read(&hi2c1, I2C_ADDR_SHIFT(addr7), reg,
                            I2C_MEMADD_SIZE_8BIT, buf, len, I2C_BUS_TIMEOUT_MS);
}


HAL_StatusTypeDef i2c_bus_write_reg(uint8_t addr7, uint8_t reg,
                                            const uint8_t *buf, uint16_t len)
{
    return HAL_I2C_Mem_Write(&hi2c1, I2C_ADDR_SHIFT(addr7), reg,
                             I2C_MEMADD_SIZE_8BIT, (uint8_t *)buf, len,
                             I2C_BUS_TIMEOUT_MS);
}


HAL_StatusTypeDef i2c_bus_is_device_ready(uint8_t addr7)
{
    return HAL_I2C_IsDeviceReady(&hi2c1, I2C_ADDR_SHIFT(addr7),
                                 1, I2C_BUS_TIMEOUT_MS);
}
