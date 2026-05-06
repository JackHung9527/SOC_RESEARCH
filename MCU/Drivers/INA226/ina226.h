/*
 * @brief  INA226 高精度雙向電流／電壓監測 IC 驅動。
 *         本驅動以 STM32 HAL I2C API 與 INA226 通訊，
 *         提供初始化、組態設定、量測讀取與校正暫存器寫入介面。
 *         使用前須由上層完成 I2C 周邊初始化並把 handle 指向有效的
 *         I2C_HandleTypeDef，再以 ina226_init 呼叫本驅動。
 */

#ifndef INA226_H
#define INA226_H

#include <stdint.h>
#include <stdbool.h>
#include "stm32g0xx_hal.h"

/* I2C 7-bit slave address (A0=GND, A1=GND) */
#define INA226_I2C_ADDR_DEFAULT     (0x40U)

/* 暫存器位址（datasheet Table 6） */
#define INA226_REG_CONFIG           (0x00U)
#define INA226_REG_SHUNT_V          (0x01U)
#define INA226_REG_BUS_V            (0x02U)
#define INA226_REG_POWER            (0x03U)
#define INA226_REG_CURRENT          (0x04U)
#define INA226_REG_CALIBRATION      (0x05U)
#define INA226_REG_MASK_ENABLE      (0x06U)
#define INA226_REG_ALERT_LIMIT      (0x07U)
#define INA226_REG_MANUFACTURER_ID  (0xFEU)
#define INA226_REG_DIE_ID           (0xFFU)

/* ID 預期值 */
#define INA226_MANUFACTURER_ID_VAL  (0x5449U)
#define INA226_DIE_ID_VAL           (0x2260U)

/* LSB 常數（datasheet 7.5.1） */
#define INA226_BUS_V_LSB_UV         (1250U)    // 1.25 mV per LSB
#define INA226_SHUNT_V_LSB_NV       (2500U)    // 2.5 uV per LSB

/* CONFIG 暫存器 reset value 中保留位元 */
#define INA226_CONFIG_RESERVED_BIT  ((uint16_t)0x4000U)

/* 平均次數（AVG[2:0]） */
typedef enum
{
    INA226_AVG_1     = 0x0U,
    INA226_AVG_4     = 0x1U,
    INA226_AVG_16    = 0x2U,
    INA226_AVG_64    = 0x3U,
    INA226_AVG_128   = 0x4U,
    INA226_AVG_256   = 0x5U,
    INA226_AVG_512   = 0x6U,
    INA226_AVG_1024  = 0x7U
} ina226_avg_t;

/* Bus／Shunt 轉換時間（VBUSCT/VSHCT[2:0]） */
typedef enum
{
    INA226_CT_140US   = 0x0U,
    INA226_CT_204US   = 0x1U,
    INA226_CT_332US   = 0x2U,
    INA226_CT_588US   = 0x3U,
    INA226_CT_1100US  = 0x4U,
    INA226_CT_2116US  = 0x5U,
    INA226_CT_4156US  = 0x6U,
    INA226_CT_8244US  = 0x7U
} ina226_ct_t;

/* 工作模式（MODE[2:0]） */
typedef enum
{
    INA226_MODE_POWERDOWN          = 0x0U,
    INA226_MODE_SHUNT_TRIG         = 0x1U,
    INA226_MODE_BUS_TRIG           = 0x2U,
    INA226_MODE_SHUNT_BUS_TRIG     = 0x3U,
    INA226_MODE_SHUNT_CONT         = 0x5U,
    INA226_MODE_BUS_CONT           = 0x6U,
    INA226_MODE_SHUNT_BUS_CONT     = 0x7U
} ina226_mode_t;

/*
 * @brief  INA226 驅動 handle。
 *         由上層配置並填入 hi2c、i2c_addr_7b、shunt_ohm、current_lsb_a，
 *         再交給本驅動進行 I/O。
 *         欄位說明：
 *           - hi2c           : 已初始化之 STM32 HAL I2C handle
 *           - i2c_addr_7b    : 7-bit slave address (A0/A1 決定，預設 0x40)
 *           - shunt_ohm      : Rshunt 電阻值，單位 Ω，預設 0.01F
 *           - current_lsb_a  : 電流 LSB，單位 A／LSB，由校正流程決定
 */
typedef struct
{
    I2C_HandleTypeDef *hi2c;
    uint8_t            i2c_addr_7b;
    float              shunt_ohm;
    float              current_lsb_a;
} ina226_handle_t;

/*
 * @brief  初始化 INA226，依參數寫入 CONFIG 與 CALIBRATION 暫存器。
 *         呼叫前須完成 I2C 周邊與 handle 欄位設定。
 *         參數說明：
 *           - h         : 驅動 handle，須已填入 hi2c/i2c_addr_7b/shunt_ohm/current_lsb_a
 *           - avg       : 平均次數，建議 INA226_AVG_16
 *           - bus_ct    : Bus 電壓轉換時間，建議 INA226_CT_1100US
 *           - shunt_ct  : Shunt 電壓轉換時間，建議 INA226_CT_1100US
 *           - mode      : 工作模式，建議 INA226_MODE_SHUNT_BUS_CONT
 *         回傳 true 表示組態與校正寫入成功。
 */
bool ina226_init(ina226_handle_t *h, ina226_avg_t avg, ina226_ct_t bus_ct,
                 ina226_ct_t shunt_ct, ina226_mode_t mode);

/*
 * @brief  讀取 INA226 Manufacturer ID 與 Die ID 並比對預期值，
 *         作為通訊與晶片身分驗證。
 *         參數說明：
 *           - h : 已填入 hi2c 與 i2c_addr_7b 之 handle
 *         回傳 true 表示兩個 ID 都正確。
 */
bool ina226_verify_id(ina226_handle_t *h);

/*
 * @brief  依 handle 中的 shunt_ohm 與 current_lsb_a 計算 CAL 暫存器值
 *         (CAL = 0.00512 / (Current_LSB * Rshunt)) 並寫入 INA226。
 *         若計算結果超出 1 ~ 65535 範圍會回傳 false。
 *         參數說明：
 *           - h : 已填入 shunt_ohm 與 current_lsb_a 之 handle
 */
bool ina226_write_calibration(ina226_handle_t *h);

/*
 * @brief  讀取 Bus 電壓暫存器並換算為 mV。
 *         參數說明：
 *           - h         : 驅動 handle
 *           - bus_v_mv  : 輸出指標，單位 mV，範圍 0 ~ 40960 mV
 */
bool ina226_read_bus_voltage_mv(ina226_handle_t *h, float *bus_v_mv);

/*
 * @brief  讀取 Shunt 電壓暫存器並換算為 µV（帶正負號）。
 *         參數說明：
 *           - h            : 驅動 handle
 *           - shunt_v_uv   : 輸出指標，單位 µV，範圍 -81920 ~ +81920 µV
 */
bool ina226_read_shunt_voltage_uv(ina226_handle_t *h, float *shunt_v_uv);

/*
 * @brief  讀取 Current 暫存器並依 current_lsb_a 換算為 mA（帶正負號）。
 *         僅在已成功寫入 CAL 暫存器後讀值才有效。
 *         參數說明：
 *           - h          : 驅動 handle
 *           - current_ma : 輸出指標，單位 mA
 */
bool ina226_read_current_ma(ina226_handle_t *h, float *current_ma);

/*
 * @brief  讀取 Power 暫存器並換算為 mW（恆正）。
 *         Power_LSB = 25 * Current_LSB（datasheet 7.5.2）。
 *         參數說明：
 *           - h        : 驅動 handle
 *           - power_mw : 輸出指標，單位 mW
 */
bool ina226_read_power_mw(ina226_handle_t *h, float *power_mw);

#endif /* INA226_H */
