/*
 * @brief  應用主程式骨架（節錄）。
 *         本檔節錄上層應用迴圈，實際的 SystemClock_Config()、
 *         MX_GPIO_Init()、MX_I2C1_Init()、MX_USART2_UART_Init() 由
 *         STM32CubeMX 在另一份 main.c 中自動產生。
 *         整合方式：把以下三段貼進 CubeMX 版本 main.c 的對應 USER CODE 區塊：
 *           - USER CODE BEGIN Includes / PV
 *           - USER CODE BEGIN 2 (init 之後)
 *           - USER CODE BEGIN WHILE / 3 (主迴圈)
 *
 *         應用流程：
 *           1. 初始化 BatteryMonitor（內含 INA226 自檢、CONFIG、CALIBRATION）
 *           2. 主迴圈每 APP_SAMPLE_PERIOD_MS 取樣一次
 *           3. 透過 USART2 以 CSV 格式輸出量測值
 *           4. PA5 LED 以取樣節拍閃爍作為運行指示
 */

#include "main.h"
#include "battery_monitor.h"
#include "soc_soh_calc.h"
#include <stdio.h>
#include <string.h>

/* CubeMX 生成的 peripheral handle，宣告於 CubeMX 版本 main.c */
I2C_HandleTypeDef  hi2c1;
UART_HandleTypeDef huart2;

static void app_log_csv_header(void)
{
    const char *hdr = "ts_ms,bus_v_mv,current_ma,power_mw,shunt_v_uv\r\n";
    (void)HAL_UART_Transmit(&huart2, (uint8_t *)hdr,
                            (uint16_t)strlen(hdr), 100U);
}

static void app_log_sample(const battery_sample_t *s)
{
    if ((s == NULL) || (!s->is_valid))
    {
        return;
    }

    char    line[96] = {0};
    int32_t n = snprintf(line, sizeof(line),
                         "%lu,%.2f,%.2f,%.2f,%.2f\r\n",
                         (unsigned long)s->timestamp_ms,
                         s->bus_v_mv,
                         s->current_ma,
                         s->power_mw,
                         s->shunt_v_uv);
    if ((n > 0) && (n < (int32_t)sizeof(line)))
    {
        (void)HAL_UART_Transmit(&huart2, (uint8_t *)line,
                                (uint16_t)n, 100U);
    }
}

/*
 * @brief  應用主入口（由 CubeMX 版本 main 在周邊初始化完成後呼叫）。
 *         無參數，永不返回。
 */
void app_main(void)
{
    if (!battery_monitor_init(&hi2c1, APP_RSHUNT_OHM, APP_CURRENT_LSB_A))
    {
        // INA226 自檢失敗：閃爍 LED 並停在這裡，方便 SWD 觀察
        while (1)
        {
            HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);
            HAL_Delay(100U);
        }
    }

    app_log_csv_header();

    uint32_t next_tick = HAL_GetTick();
    battery_sample_t snapshot = {0};

    while (1)
    {
        uint32_t now = HAL_GetTick();
        if ((int32_t)(now - next_tick) >= 0)
        {
            next_tick = now + APP_SAMPLE_PERIOD_MS;

            if (battery_monitor_sample())
            {
                if (battery_monitor_get_latest(&snapshot))
                {
                    app_log_sample(&snapshot);
                    HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);
                }
            }
        }

        // 預留：未來在此插入 SOC/SOH 計算與 ALERT pin 處理
        // 目前演算法骨架見 soc_soh_calc.h／.c（校正 pending）
    }
}

void Error_Handler(void)
{
    __disable_irq();
    while (1)
    {
        HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);
        for (volatile uint32_t i = 0U; i < 100000U; i++)
        {
            __NOP();
        }
    }
}
