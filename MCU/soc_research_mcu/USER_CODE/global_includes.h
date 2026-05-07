/*
 * global_includes.h
 * 統一 include 入口。
 *   - main.c 只 include 此檔，不再個別 include 其他 USER_CODE 內的 header
 *   - driver 子資料夾的 header 一律從這裡集中匯入
 *   - extern handle 宣告在這裡（CubeMX 產生的 hxxx），driver 內部就不用各自 extern
 *
 * include 順序：
 *   1. CubeMX HAL（main.h 已經帶完整 HAL 套件）
 *   2. 標準 C 函式庫
 *   3. 全專案參數（model_set.h）
 *   4. USER_CODE 共用模組（softwareTim / userCode）
 *   5. Driver 模組（由 stm32-driver-scaffold 系列 skill 自動插入到 USER_DRIVERS marker 之間）
 */

#ifndef GLOBAL_INCLUDES_H_
#define GLOBAL_INCLUDES_H_

/* 1. HAL */
#include "main.h"

/* 2. 標準 C */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

/* 3. 全專案參數 */
#include "model_set.h"

/* 4. USER_CODE 共用模組 */
#include "userCode.h"
#include "softwareTim.h"

/* 5. Driver 模組（auto-managed by stm32-driver-scaffold 系列 skill）
 *    新增 driver 時，scaffold skill 會自動在下面 marker 之間插入 #include。
 *    不要手動加 driver include 在 marker 之外，會被下次 scaffold 覆寫。
 */
/* === USER_DRIVERS BEGIN === */
#include "uart_debug/uart_debug.h"
#include "i2c_bus/i2c_bus.h"
#include "ina226/ina226.h"
#include "battery_monitor/battery_monitor.h"
#include "ina_cal/ina_cal.h"
#include "soc_soh_calc/soc_soh_calc.h"
/* === USER_DRIVERS END === */


/*
 * extern handle
 * ex. extern ADC_HandleTypeDef hadc1;
 *     extern UART_HandleTypeDef huart1;
 */


#endif /* GLOBAL_INCLUDES_H_ */
