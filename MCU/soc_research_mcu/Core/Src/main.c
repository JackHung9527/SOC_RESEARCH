/*
 * @brief  SOC_RESEARCH STM32G071RB application entry point.
 *
 *         This file now follows the stm32-proj-init / firmware-project-builder
 *         convention: main() is reduced to peripheral init + once() + loop().
 *         The application body (boot banner, INA226 self-test, 1 Hz heartbeat,
 *         per-second sampling) lives in USER_CODE/userCode.c.
 *
 *         Hardware brought up here:
 *           - SYSCLK = 64 MHz from HSI16 + PLL.
 *           - GPIO    : LD2 PA5 out, INA226_ALERT PA10 EXTI in pull-up,
 *                       USER_BTN PC13 EXTI in.
 *           - USART2  : PA2/PA3, 115200 8N1 — owned by USER_CODE/uart_debug.
 *           - I2C1    : PB8/PB9, 400 kHz — shared by USER_CODE/i2c_bus and the
 *                       pre-existing Drivers/INA226 driver.
 *           - TIM6    : 100 µs base tick for USER_CODE/softwareTim. The IRQ
 *                       only increments g_softWareTimCnt (no UART, no app
 *                       work — printing on the 100 µs tick would saturate
 *                       the bus).
 *
 *         INA226 hardware is NOT required for boot to succeed: if the sensor
 *         NACKs, USER_CODE/userCode.c::once() prints a graceful warning and
 *         the heartbeat continues without sampling.
 */

#include "main.h"
#include "stm32g0xx_it.h"
#include "global_includes.h"

/* ---------------- Peripheral handles (declared in main.h) ---------------- */
I2C_HandleTypeDef  hi2c1;
UART_HandleTypeDef huart2;
TIM_HandleTypeDef  htim6;

/* ---------------- Forward declarations ---------------- */
static void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_I2C1_Init(void);
static void MX_TIM6_Init(void);


/* ---------------- main ---------------- */
int main(void)
{
    HAL_Init();
    SystemClock_Config();

    MX_GPIO_Init();
    MX_USART2_UART_Init();
    MX_I2C1_Init();
    MX_TIM6_Init();

    once();

    while (1)
    {
        loop();
    }
}


/* ---------------- CubeMX-equivalent peripheral init ---------------- */

/*
 * @brief  Configure SYSCLK = 64 MHz from HSI16 + PLL.
 *         PLL: HSI16 / M=1 → 16 MHz / N=8 → 128 MHz / R=2 → 64 MHz.
 *         APB1 = AHB = 64 MHz (G0 has a single APB).
 *         FLASH latency = 2 wait states for SYSCLK > 48 MHz @ Vdd 3.3 V.
 */
static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef       osc = {0};
    RCC_ClkInitTypeDef       clk = {0};

    /* Voltage scaling Range 1 already default after reset on G0; no-op via PWR. */
    HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1);

    osc.OscillatorType      = RCC_OSCILLATORTYPE_HSI;
    osc.HSIState            = RCC_HSI_ON;
    osc.HSIDiv              = RCC_HSI_DIV1;
    osc.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    osc.PLL.PLLState        = RCC_PLL_ON;
    osc.PLL.PLLSource       = RCC_PLLSOURCE_HSI;
    osc.PLL.PLLM            = RCC_PLLM_DIV1;
    osc.PLL.PLLN            = 8;
    osc.PLL.PLLP            = RCC_PLLP_DIV2;
    osc.PLL.PLLQ            = RCC_PLLQ_DIV2;
    osc.PLL.PLLR            = RCC_PLLR_DIV2;
    if (HAL_RCC_OscConfig(&osc) != HAL_OK)
    {
        Error_Handler();
    }

    clk.ClockType      = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                       | RCC_CLOCKTYPE_PCLK1;
    clk.SYSCLKSource   = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider  = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_2) != HAL_OK)
    {
        Error_Handler();
    }
}

/*
 * @brief  GPIO init.
 *         - PA5 (LD2): output push-pull, low speed, no pull.
 *         - PA10 (INA226 ALERT): input, falling EXTI, pull-up.
 *         - PC13 (USER_BTN): input, falling EXTI, no pull (Nucleo has external).
 *         AF GPIOs (PA2/PA3 USART2, PB8/PB9 I2C1) configured by their MX_*_Init.
 */
static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef gp = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* LD2 default state */
    HAL_GPIO_WritePin(LED_GPIO_Port, LED_Pin, GPIO_PIN_RESET);

    gp.Pin   = LED_Pin;
    gp.Mode  = GPIO_MODE_OUTPUT_PP;
    gp.Pull  = GPIO_NOPULL;
    gp.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(LED_GPIO_Port, &gp);

    gp.Pin  = INA226_ALERT_Pin;
    gp.Mode = GPIO_MODE_IT_FALLING;
    gp.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(INA226_ALERT_GPIO_Port, &gp);

    gp.Pin  = USER_BTN_Pin;
    gp.Mode = GPIO_MODE_IT_FALLING;
    gp.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(USER_BTN_GPIO_Port, &gp);

    HAL_NVIC_SetPriority(EXTI4_15_IRQn, 2, 0);
    HAL_NVIC_EnableIRQ(EXTI4_15_IRQn);
}

/*
 * @brief  USART2 init: 115200 8N1, async, oversample 16.
 *         Routed PA2 (TX) / PA3 (RX) on AF1 per STM32G071 datasheet.
 */
static void MX_USART2_UART_Init(void)
{
    huart2.Instance                    = USART2;
    huart2.Init.BaudRate               = 115200;
    huart2.Init.WordLength             = UART_WORDLENGTH_8B;
    huart2.Init.StopBits               = UART_STOPBITS_1;
    huart2.Init.Parity                 = UART_PARITY_NONE;
    huart2.Init.Mode                   = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl              = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling           = UART_OVERSAMPLING_16;
    huart2.Init.OneBitSampling         = UART_ONE_BIT_SAMPLE_DISABLE;
    huart2.Init.ClockPrescaler         = UART_PRESCALER_DIV1;
    huart2.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
    if (HAL_UART_Init(&huart2) != HAL_OK)
    {
        Error_Handler();
    }
    if (HAL_UARTEx_SetTxFifoThreshold(&huart2, UART_TXFIFO_THRESHOLD_1_8) != HAL_OK)
    {
        Error_Handler();
    }
    if (HAL_UARTEx_SetRxFifoThreshold(&huart2, UART_RXFIFO_THRESHOLD_1_8) != HAL_OK)
    {
        Error_Handler();
    }
    if (HAL_UARTEx_DisableFifoMode(&huart2) != HAL_OK)
    {
        Error_Handler();
    }
}

/*
 * @brief  I2C1 init: Fast Mode 400 kHz on PB8 (SCL) / PB9 (SDA), AF6.
 *         Timing computed for I2CCLK = 64 MHz (PCLK1) using STM32CubeMX
 *         Fast Mode 400 kHz preset:
 *           PRESC=0x6, SCLDEL=0x3, SDADEL=0x1, SCLH=0x3, SCLL=0x9
 *           TIMINGR = 0x00300619.
 */
static void MX_I2C1_Init(void)
{
    hi2c1.Instance              = I2C1;
    hi2c1.Init.Timing           = 0x00300619U;
    hi2c1.Init.OwnAddress1      = 0;
    hi2c1.Init.AddressingMode   = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode  = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.OwnAddress2      = 0;
    hi2c1.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
    hi2c1.Init.GeneralCallMode  = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode    = I2C_NOSTRETCH_DISABLE;
    if (HAL_I2C_Init(&hi2c1) != HAL_OK)
    {
        Error_Handler();
    }
    if (HAL_I2CEx_ConfigAnalogFilter(&hi2c1, I2C_ANALOGFILTER_ENABLE) != HAL_OK)
    {
        Error_Handler();
    }
    if (HAL_I2CEx_ConfigDigitalFilter(&hi2c1, 0) != HAL_OK)
    {
        Error_Handler();
    }
}

/*
 * @brief  TIM6 base tick at 100 µs.
 *         Prescaler  = APBTimClk_MHz - 1  = 64 - 1 = 63
 *         Period     = 99   ⇒  64 MHz / 64 / 100 = 10 kHz = 100 µs reload
 *         The ISR (in stm32g0xx_it.c) calls HAL_TIM_IRQHandler which routes to
 *         the canonical HAL_TIM_PeriodElapsedCallback in
 *         USER_CODE/softwareTim.c, which does nothing other than increment
 *         g_softWareTimCnt. This keeps the 100 µs tick path bounded — no UART
 *         I/O on the tick.
 */
static void MX_TIM6_Init(void)
{
    htim6.Instance               = TIM6;
    htim6.Init.Prescaler         = 63;
    htim6.Init.CounterMode       = TIM_COUNTERMODE_UP;
    htim6.Init.Period            = 99;
    htim6.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    if (HAL_TIM_Base_Init(&htim6) != HAL_OK)
    {
        Error_Handler();
    }

    HAL_NVIC_SetPriority(TIM6_DAC_LPTIM1_IRQn, 2, 0);
    HAL_NVIC_EnableIRQ(TIM6_DAC_LPTIM1_IRQn);
}

/* ---------------- HAL_MspInit hooks ---------------- */

/*
 * @brief  Low-level init for USART2.  Called from HAL_UART_Init().
 *         AF route: PA2 = USART2_TX (AF1), PA3 = USART2_RX (AF1).
 */
void HAL_UART_MspInit(UART_HandleTypeDef *huart)
{
    if (huart->Instance != USART2) return;

    GPIO_InitTypeDef gp = {0};
    RCC_PeriphCLKInitTypeDef clk = {0};

    /* USART2 source clock = PCLK1 (default).  Explicitly select to be safe. */
    clk.PeriphClockSelection = RCC_PERIPHCLK_USART2;
    clk.Usart2ClockSelection = RCC_USART2CLKSOURCE_PCLK1;
    if (HAL_RCCEx_PeriphCLKConfig(&clk) != HAL_OK)
    {
        Error_Handler();
    }

    __HAL_RCC_USART2_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();

    gp.Pin       = GPIO_PIN_2 | GPIO_PIN_3;
    gp.Mode      = GPIO_MODE_AF_PP;
    gp.Pull      = GPIO_NOPULL;
    gp.Speed     = GPIO_SPEED_FREQ_VERY_HIGH;
    gp.Alternate = GPIO_AF1_USART2;
    HAL_GPIO_Init(GPIOA, &gp);

    HAL_NVIC_SetPriority(USART2_IRQn, 2, 0);
    HAL_NVIC_EnableIRQ(USART2_IRQn);
}

void HAL_UART_MspDeInit(UART_HandleTypeDef *huart)
{
    if (huart->Instance != USART2) return;
    __HAL_RCC_USART2_CLK_DISABLE();
    HAL_GPIO_DeInit(GPIOA, GPIO_PIN_2 | GPIO_PIN_3);
    HAL_NVIC_DisableIRQ(USART2_IRQn);
}

/*
 * @brief  Low-level init for I2C1.  Called from HAL_I2C_Init().
 *         AF route: PB8 = I2C1_SCL (AF6), PB9 = I2C1_SDA (AF6).
 *         Clock source = PCLK1 (64 MHz) per .ioc.
 */
void HAL_I2C_MspInit(I2C_HandleTypeDef *hi2c)
{
    if (hi2c->Instance != I2C1) return;

    GPIO_InitTypeDef gp = {0};
    RCC_PeriphCLKInitTypeDef clk = {0};

    clk.PeriphClockSelection = RCC_PERIPHCLK_I2C1;
    clk.I2c1ClockSelection   = RCC_I2C1CLKSOURCE_PCLK1;
    if (HAL_RCCEx_PeriphCLKConfig(&clk) != HAL_OK)
    {
        Error_Handler();
    }

    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_I2C1_CLK_ENABLE();

    gp.Pin       = GPIO_PIN_8 | GPIO_PIN_9;
    gp.Mode      = GPIO_MODE_AF_OD;     /* I2C is open-drain */
    gp.Pull      = GPIO_PULLUP;
    gp.Speed     = GPIO_SPEED_FREQ_VERY_HIGH;
    gp.Alternate = GPIO_AF6_I2C1;
    HAL_GPIO_Init(GPIOB, &gp);
}

void HAL_I2C_MspDeInit(I2C_HandleTypeDef *hi2c)
{
    if (hi2c->Instance != I2C1) return;
    __HAL_RCC_I2C1_CLK_DISABLE();
    HAL_GPIO_DeInit(GPIOB, GPIO_PIN_8 | GPIO_PIN_9);
}

/*
 * @brief  Low-level init for TIM6.  Called from HAL_TIM_Base_Init().
 */
void HAL_TIM_Base_MspInit(TIM_HandleTypeDef *htim)
{
    if (htim->Instance != TIM6) return;
    __HAL_RCC_TIM6_CLK_ENABLE();
}

void HAL_TIM_Base_MspDeInit(TIM_HandleTypeDef *htim)
{
    if (htim->Instance != TIM6) return;
    __HAL_RCC_TIM6_CLK_DISABLE();
    HAL_NVIC_DisableIRQ(TIM6_DAC_LPTIM1_IRQn);
}

/* ---------------- Error handler ---------------- */
void Error_Handler(void)
{
    __disable_irq();
    /* Frantic LED flicker so an attached SWD/eyeball can spot a fatal init. */
    while (1)
    {
        HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);
        for (volatile uint32_t i = 0U; i < 100000U; i++)
        {
            __NOP();
        }
    }
}

/* ---------------- assert_param sink ---------------- */
#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
    (void)file; (void)line;
    while (1) {}
}
#endif
