/*
 * @brief  電池監測應用層。
 *         職責：
 *           1. 封裝 INA226 驅動之初始化與週期取樣
 *           2. 將最新一筆量測快取於模組內部，供 SOC/SOH 演算法讀取
 *           3. 提供 tick/timer-driven 的取樣排程介面
 *         欄位說明（樣本結構）：
 *           - timestamp_ms : 取樣時刻，單位 ms (HAL_GetTick)
 *           - bus_v_mv     : 電池端點電壓，單位 mV
 *           - shunt_v_uv   : Shunt 兩端壓降，單位 µV，帶正負號
 *           - current_ma   : 流經電池的電流，單位 mA，正值=放電
 *           - power_mw     : 瞬時功率，單位 mW
 *           - is_valid     : 取樣是否成功
 */

#ifndef BATTERY_MONITOR_H
#define BATTERY_MONITOR_H

#include <stdint.h>
#include <stdbool.h>
#include "ina226.h"

typedef struct
{
    uint32_t timestamp_ms;
    float    bus_v_mv;
    float    shunt_v_uv;
    float    current_ma;
    float    power_mw;
    bool     is_valid;
} battery_sample_t;

/*
 * @brief  初始化電池監測模組。
 *         呼叫前須完成 I2C 周邊初始化。
 *         參數說明：
 *           - hi2c           : 已初始化之 STM32 HAL I2C handle
 *           - shunt_ohm      : Rshunt 電阻值，單位 Ω，預設 0.01F
 *           - current_lsb_a  : 校正後 Current_LSB，單位 A／LSB
 *                              （校正未完成時可暫填 0.0001525F）
 *         回傳 true 表示 INA226 自檢與組態寫入成功。
 */
bool battery_monitor_init(I2C_HandleTypeDef *hi2c,
                          float shunt_ohm,
                          float current_lsb_a);

/*
 * @brief  執行單次 INA226 取樣，將結果寫入內部快取。
 *         無參數；可由 SysTick handler、timer ISR 或主迴圈定期呼叫。
 *         回傳 true 表示四個量測欄位皆讀取成功。
 */
bool battery_monitor_sample(void);

/*
 * @brief  讀出最近一筆取樣結果（深拷貝，呼叫端可任意修改）。
 *         參數說明：
 *           - out : 輸出指標，呼叫端配置之 battery_sample_t
 */
bool battery_monitor_get_latest(battery_sample_t *out);

#endif /* BATTERY_MONITOR_H */
