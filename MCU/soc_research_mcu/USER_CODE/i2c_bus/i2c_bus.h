/*
 * i2c_bus.h
 * 由 stm32-i2c-scaffold 自動產生
 *
 * 周邊：I2C1（HAL handle = hi2c1）
 * Bus speed：400000 Hz（informational）
 *
 * I2C master bus 抽象層：
 *   - 7-bit 位址介面（內部自動 << 1 轉 HAL 8-bit）
 *   - 同步阻塞版 read/write/read_reg/write_reg
 *   - 可選 async (IT / DMA)、queue / single-slot、raw / register 變體
 *   - 可選 bus scanner
 */

#ifndef I2C_BUS_H_
#define I2C_BUS_H_


/*
 * Task Select — 大項
 */
typedef enum
{
    I2c_bus_TaskSel_TaskAwait        = 0,
    I2c_bus_TaskSel_Service_Routine  = 1
} I2c_bus_TaskSel;


/*
 * Flow Select — 小項
 */
typedef enum
{
    I2c_bus_FlowSel_FlowAwait        = 0,
    I2c_bus_FlowSel_FirstFlow        = 1,
    I2c_bus_FlowSel_AsyncDispatch    = 1,
    I2c_bus_FlowSel_finish           = 2
} I2c_bus_FlowSel;


/* globals */
extern I2c_bus_TaskSel
    g_i2c_bus_taskSel;
extern I2c_bus_FlowSel
    g_i2c_bus_flowSel;

extern uint32_t
    g_i2c_bus_cmd,
    g_i2c_bus_cnt;


/* ===== Lifecycle ===== */
void i2c_bus_init(void);                                  /* once() */
void i2c_bus_handle(void);                                /* loop() */
void i2c_bus_TASK(I2c_bus_TaskSel *task,
                          I2c_bus_FlowSel *flow);


/* ===== Sync (blocking) API — timeout = I2C_BUS_TIMEOUT_MS ===== */
HAL_StatusTypeDef i2c_bus_read     (uint8_t addr7, uint8_t       *buf, uint16_t len);
HAL_StatusTypeDef i2c_bus_write    (uint8_t addr7, const uint8_t *buf, uint16_t len);
HAL_StatusTypeDef i2c_bus_read_reg (uint8_t addr7, uint8_t reg, uint8_t       *buf, uint16_t len);
HAL_StatusTypeDef i2c_bus_write_reg(uint8_t addr7, uint8_t reg, const uint8_t *buf, uint16_t len);
HAL_StatusTypeDef i2c_bus_is_device_ready(uint8_t addr7);


#endif /* I2C_BUS_H_ */
