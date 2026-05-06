/*
 * @brief  Application main header.
 *         Declares peripheral handles (defined in main.c) and the GPIO labels
 *         driven from the .ioc.  Application-layer modules include this file
 *         instead of pulling stm32g0xx_hal.h directly.
 */

#ifndef MAIN_H
#define MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32g0xx_hal.h"

/* ---------------- Peripheral handles (defined in main.c) ---------------- */
extern I2C_HandleTypeDef  hi2c1;
extern UART_HandleTypeDef huart2;
extern TIM_HandleTypeDef  htim6;

/* ---------------- Application defaults (used by App layer) ---------------- */
#define APP_RSHUNT_OHM            (0.01F)
#define APP_CURRENT_LSB_A         (0.0001525F)
#define APP_SAMPLE_PERIOD_MS      (200U)

/* ---------------- Pin labels (must match .ioc) ---------------- */
#define LED_GPIO_Port             GPIOA
#define LED_Pin                   GPIO_PIN_5

#define INA226_ALERT_GPIO_Port    GPIOA
#define INA226_ALERT_Pin          GPIO_PIN_10

#define USER_BTN_GPIO_Port        GPIOC
#define USER_BTN_Pin              GPIO_PIN_13

/* ---------------- Public functions ---------------- */
void Error_Handler(void);

#ifdef __cplusplus
}
#endif

#endif /* MAIN_H */
