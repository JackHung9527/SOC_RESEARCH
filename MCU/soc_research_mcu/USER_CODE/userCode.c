/*
 * 2024/09/03 by Jack
 * Encoding: UTF-8
 *
 * SOC_RESEARCH application glue.
 *   once() : boot banner, INA226 self-test (graceful warn if absent), arm
 *            battery_monitor module, register 1 Hz heartbeat schedule.
 *   loop() : drive each driver's handle(), then 1 Hz heartbeat dispatch
 *            via softWareTimTick_100us (Period = 10000 * 100µs = 1 s).
 *
 * The 100 µs base tick (TIM6 ISR) only increments g_softWareTimCnt; it does
 * NOT print or do work — printing on every tick would saturate UART.
 *
 * The INA226 hardware is not yet wired; the firmware must keep running and
 * heartbeat without it (see project.yaml::open_questions).
 */

#include "global_includes.h"
/* battery_monitor.h / ina226.h / soc_soh_calc.h are pulled in via the
 * USER_DRIVERS block in global_includes.h — no need to re-include here. */

/* ---- module state ---- */
static bool     s_ina226_present = false;
static uint32_t s_hb_cmd  = _timxTick_cmd_start;   /* heartbeat scheduler */
static uint32_t s_hb_cnt  = 0;
static uint32_t s_seconds = 0;                     /* monotonic seconds since boot */


/* 重新定向 printf() — 走 uart_debug driver 提供的 _write
 * uart_debug 模組已經自帶 _write retarget；本 PUTCHAR_PROTOTYPE 留 stub 保留
 * 與舊專案相容性，實際 stdout/printf 路徑由 uart_debug.c::_write 接管。 */
#ifdef __GNUC__
#define PUTCHAR_PROTOTYPE int __io_putchar(int ch)
#else
#define PUTCHAR_PROTOTYPE int fputc(int ch, FILE *f)
#endif

PUTCHAR_PROTOTYPE
{
	uint8_t b = (uint8_t)ch;
	(void)uart_debug_send(&b, 1);
	return ch;
}


/* add in int main() */
void once(void)
{
	HAL_TIM_Base_Start_IT(&SoftWareTim_peripheral);

	/* === USER_INIT_CALLS BEGIN === */
	/* driver_init() 由 stm32-*-scaffold skill 自動插入此區塊內。
	 * 規則：cb_aggregator_init() 會被插入到區塊開頭（必須最先呼叫），
	 *       其他 driver init 依 scaffold 順序追加。 */
	uart_debug_init();
	i2c_bus_init();
	/* === USER_INIT_CALLS END === */

	/* ---- one-shot boot banner (grep-able by SCRIPTS/flash_and_verify.py) ---- */
	uart_debug_printf("\r\n=== SOC_RESEARCH STM32G071RB boot ===\r\n");
	uart_debug_printf("Build: USER_CODE framework (uart_debug + i2c_bus)\r\n");
	uart_debug_printf("SYSCLK=64MHz  USART2=115200  I2C1=400kHz  TIM6=100us\r\n");

	/* ---- INA226 sniff (must NOT hard-fault when sensor absent) ---- */
	HAL_StatusTypeDef st = HAL_I2C_IsDeviceReady(&hi2c1,
	                                             (uint16_t)(INA226_I2C_ADDR_DEFAULT << 1),
	                                             1U, 5U);
	if (st == HAL_OK)
	{
		uart_debug_printf("[I2C1] device ACKed at 0x40\r\n");
	}
	else
	{
		uart_debug_printf("[I2C1] no ACK at 0x40 — bus idle, continuing\r\n");
	}

	if (battery_monitor_init(&hi2c1, APP_RSHUNT_OHM, APP_CURRENT_LSB_A))
	{
		uart_debug_printf("[INA226] CONFIG/CAL written, monitor armed.\r\n");
		s_ina226_present = true;
	}
	else
	{
		uart_debug_printf("[INA226] not detected (NACK 0x40) — expected, sensor not yet wired.\r\n");
		s_ina226_present = false;
	}

	uart_debug_printf("[main] entering loop\r\n");
}


/* add in int main() while(1) */
void loop(void)
{
	/* === USER_LOOP_CALLS BEGIN === */
	/* driver_handle() 由 stm32-*-scaffold skill 自動插入此區塊內。 */
	uart_debug_handle();
	i2c_bus_handle();
	/* === USER_LOOP_CALLS END === */

	/* ---- 1 Hz heartbeat scheduled on the 100µs base tick ---- */
	if (softWareTimTick_100us(&s_hb_cmd, &s_hb_cnt, 10000U) == _timxTick_TimUp)
	{
		HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);
		s_seconds++;

		if (s_ina226_present && battery_monitor_sample())
		{
			battery_sample_t snap;
			if (battery_monitor_get_latest(&snap))
			{
				uart_debug_printf("[%lus] alive V=%.1fmV I=%.1fmA P=%.1fmW i2c=ok ina=present\r\n",
				                  (unsigned long)s_seconds,
				                  (double)snap.bus_v_mv,
				                  (double)snap.current_ma,
				                  (double)snap.power_mw);
			}
			else
			{
				uart_debug_printf("[%lus] alive — i2c=ok ina=stale\r\n",
				                  (unsigned long)s_seconds);
			}
		}
		else
		{
			uart_debug_printf("[%lus] alive — i2c=idle ina=absent\r\n",
			                  (unsigned long)s_seconds);
		}

		s_hb_cmd = _timxTick_cmd_start;   /* re-arm */
	}
}
