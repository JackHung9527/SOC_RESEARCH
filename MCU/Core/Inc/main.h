/*
 * @brief  應用主標頭。
 *         僅集中宣告全域腳位巨集與 CubeMX peripheral handle 之 extern，
 *         不放任何函式實作。實際 HAL handle 由 CubeMX 自動產生於
 *         CubeMX 版本的 main.c 中。
 */

#ifndef MAIN_H
#define MAIN_H

#include "stm32g0xx_hal.h"

/* CubeMX 生成之外部 handle（在 CubeMX 版本 main.c 中定義） */
extern I2C_HandleTypeDef   hi2c1;
extern UART_HandleTypeDef  huart2;

/* 系統預設值 */
#define APP_RSHUNT_OHM            (0.01F)        // 10 mΩ Kelvin shunt
#define APP_CURRENT_LSB_A         (0.0001525F)   // 152.5 µA／LSB（5 A 滿標時的初值）
#define APP_SAMPLE_PERIOD_MS      (200U)         // 5 Hz 取樣

/* 腳位定義（與 CubeMX 設定保持一致） */
#define LED_GPIO_Port             GPIOA
#define LED_Pin                   GPIO_PIN_5
#define INA226_ALERT_GPIO_Port    GPIOA
#define INA226_ALERT_Pin          GPIO_PIN_10
#define USER_BTN_GPIO_Port        GPIOC
#define USER_BTN_Pin              GPIO_PIN_13

void Error_Handler(void);

#endif /* MAIN_H */
