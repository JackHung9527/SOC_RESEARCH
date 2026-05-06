/*
 * @brief  Interrupt service routine declarations.
 *         All ISRs are weakly defined in startup_stm32g071xx.s and overridden
 *         in stm32g0xx_it.c. This header is only consumed by main.c so the
 *         IRQ enable code can resolve the names.
 */
#ifndef STM32G0xx_IT_H
#define STM32G0xx_IT_H

#ifdef __cplusplus
extern "C" {
#endif

void NMI_Handler(void);
void HardFault_Handler(void);
void SVC_Handler(void);
void PendSV_Handler(void);
void SysTick_Handler(void);

void EXTI4_15_IRQHandler(void);
void TIM6_DAC_LPTIM1_IRQHandler(void);
void USART2_IRQHandler(void);

#ifdef __cplusplus
}
#endif

#endif /* STM32G0xx_IT_H */
