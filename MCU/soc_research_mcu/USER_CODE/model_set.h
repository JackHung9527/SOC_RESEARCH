/*
 * model_set.h
 * 全專案可調參數集中區。修改這裡不需要改 driver 程式碼，也不需要動 main。
 *
 * 使用原則：
 *   - 所有 #define 形式的常數，集中在此檔
 *   - 同一份韌體支援多機種時，用 #ifdef MODEL_XXX 切換
 *   - driver / 應用層的程式碼一律從這裡讀參數，不要寫死數值
 *   - 修改後需 rebuild，不會有 runtime 開銷
 */

#ifndef MODEL_SET_H_
#define MODEL_SET_H_

/* ====================================================================
 * 機種選擇（同一專案多機種共用韌體時用 #ifdef 切換）
 * ==================================================================== */
#define MODEL_DEFAULT
// #define MODEL_VARIANT_A
// #define MODEL_VARIANT_B


/* ====================================================================
 * 系統時序
 * ==================================================================== */
#define MS_LOOP_TICK_PERIOD_US              100U      /* softwareTim tick = 100µs */


/* ====================================================================
 * Driver 參數（依使用到的 driver 分區塊填入）
 *
 * 各 driver scaffold skill 會在此檔對應位置插入參數區塊。
 * 區塊用以下 marker 包起來，方便日後維護：
 *
 *   /* === MODEL_SET_<DRIVER> BEGIN === * /
 *   ... 參數 ...
 *   /* === MODEL_SET_<DRIVER> END === * /
 * ==================================================================== */


/* === MODEL_SET_UART_DEBUG BEGIN === */
#define UART_DEBUG_TX_BUF_SIZE     512U   /* TX ring buffer */
#define UART_DEBUG_RX_LINE_SIZE    128U   /* RX line buffer */
#define UART_DEBUG_BAUD            115200UL   /* informational */
/* === MODEL_SET_UART_DEBUG END === */


/* === MODEL_SET_I2C_BUS BEGIN === */
#define I2C_BUS_TIMEOUT_MS      100U
#define I2C_BUS_BUS_SPEED       400000UL   /* informational */
/* === MODEL_SET_I2C_BUS END === */


/* === MODEL_SET_INA226 BEGIN === */
/* Pre-existing INA226 driver — no compile-time tunables exposed yet.
 * Runtime config (avg / conv-time / mode / shunt-ohm / Current_LSB) is set
 * via ina226_init() arguments; see USER_CODE/userCode.c::once() and
 * Core/Inc/main.h (APP_RSHUNT_OHM, APP_CURRENT_LSB_A) for the values used
 * at boot. */
/* === MODEL_SET_INA226 END === */


/* === MODEL_SET_BATTERY_MONITOR BEGIN === */
/* Pre-existing battery_monitor app layer — wraps the INA226 driver, samples
 * once per heartbeat (1 Hz). Tunables live for now in Core/Inc/main.h:
 *   APP_RSHUNT_OHM        Rshunt resistor (ohm)
 *   APP_CURRENT_LSB_A     Current LSB (A/LSB), per INA226 calibration eqn.
 * Migration of these into MODEL_SET_BATTERY_MONITOR is a follow-up. */
/* === MODEL_SET_BATTERY_MONITOR END === */


/* === MODEL_SET_SOC_SOH_CALC BEGIN === */
/* Pre-existing SOC/SOH algorithm stub — empirical Z-SOC LUT and temperature
 * compensation coefficients are not yet defined; algorithm is pending the
 * INA226 hardware connection and bench calibration run. Macros will land
 * here once calibration produces values. */
/* === MODEL_SET_SOC_SOH_CALC END === */


/* === MODEL_SET_USER BEGIN === */
/* 使用者自訂參數放這裡 */

/* === MODEL_SET_USER END === */


#endif /* MODEL_SET_H_ */
