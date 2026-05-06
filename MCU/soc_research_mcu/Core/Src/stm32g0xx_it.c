/*
 * @brief  Interrupt service routines.
 *         - SysTick_Handler() drives HAL_GetTick() / HAL_Delay().
 *         - TIM6_DAC_LPTIM1_IRQHandler() services the 100 µs base tick used
 *           by USER_CODE/softwareTim. The HAL routes via
 *           HAL_TIM_PeriodElapsedCallback() in softwareTim.c.
 *         - USART2_IRQHandler() forwards into HAL_UART_IRQHandler() so the
 *           uart_debug driver's TX/RX-Cplt callbacks fire.
 *         - EXTI4_15_IRQHandler() handles INA226 ALERT (PA10) and the user
 *           button (PC13). Both are stubbed — only EXTI line clearing is done.
 */

#include "main.h"
#include "stm32g0xx_it.h"

extern TIM_HandleTypeDef  htim6;
extern UART_HandleTypeDef huart2;

/* ---------------- Cortex-M0+ system handlers ---------------- */

void NMI_Handler(void)
{
    while (1) {}
}

void HardFault_Handler(void)
{
    while (1) {}
}

void SVC_Handler(void)
{
}

void PendSV_Handler(void)
{
}

void SysTick_Handler(void)
{
    HAL_IncTick();
}

/* ---------------- Peripheral IRQs ---------------- */

void EXTI4_15_IRQHandler(void)
{
    /* INA226 ALERT (PA10) and USER_BTN (PC13) are routed here.
     * Sensor not wired yet; just clear pending flags so we do not loop. */
    HAL_GPIO_EXTI_IRQHandler(INA226_ALERT_Pin);
    HAL_GPIO_EXTI_IRQHandler(USER_BTN_Pin);
}

void TIM6_DAC_LPTIM1_IRQHandler(void)
{
    HAL_TIM_IRQHandler(&htim6);
}

void USART2_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart2);
}
