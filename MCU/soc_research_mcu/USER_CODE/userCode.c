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


/* ---- SOC 三法掛載點（論文 4.0：同量測路徑、同節拍，每秒餵一次） ----
 * 各方法由 model_set.h 的 SOC_*_ENABLE 個別開關；footprint 量測腳本
 * (SCRIPTS/footprint_report.py) 據此產生「只有骨架」與「骨架＋單一方法」
 * 變體相減取淨佔用（4.4.3）。每次更新以 perf_cyc 計 CPU cycles。 */
#if SOC_COULOMB_ENABLE || SOC_EKF_ENABLE || SOC_ZDYN_ENABLE

#if SOC_COULOMB_ENABLE
static uint32_t s_cyc_cc;
#endif
#if SOC_EKF_ENABLE
static uint32_t s_cyc_ekf;
#endif
#if SOC_ZDYN_ENABLE
static uint32_t s_cyc_z;
#endif

static void soc_estimators_feed_1s(float i_ma, float v_mv)
{
	perf_cyc_t t;

#if SOC_EKF_ENABLE
	/* 開機後首筆有效樣本近似靜置 → 以 OCV 反查播種 EKF 初始 SOC */
	static bool s_ekf_seeded = false;
	if (!s_ekf_seeded)
	{
		soc_ekf_seed_from_voltage(v_mv);
		s_ekf_seeded = true;
	}
#endif

#if SOC_COULOMB_ENABLE
	perf_cyc_begin(&t);
	soc_coulomb_update_1s((int32_t)(i_ma * 1000.0f));   /* mA → µA */
	s_cyc_cc = perf_cyc_end(&t);
#endif
#if SOC_EKF_ENABLE
	perf_cyc_begin(&t);
	soc_ekf_update_1s(i_ma, v_mv);
	s_cyc_ekf = perf_cyc_end(&t);
#endif
#if SOC_ZDYN_ENABLE
	perf_cyc_begin(&t);
	soc_zdyn_update_1s(i_ma, v_mv);
	s_cyc_z = perf_cyc_end(&t);
#endif
	(void)t;
}

static void soc_estimators_print(uint32_t seconds)
{
	uart_debug_printf("[%lus] soc", (unsigned long)seconds);
#if SOC_COULOMB_ENABLE
	uart_debug_printf(" cc=%.2f%%(%lucyc)",
	                  (double)soc_coulomb_get_pct_x100() / 100.0,
	                  (unsigned long)s_cyc_cc);
#endif
#if SOC_EKF_ENABLE
	uart_debug_printf(" ekf=%.2f%%(%lucyc)",
	                  (double)soc_ekf_get_soc_pct(),
	                  (unsigned long)s_cyc_ekf);
#endif
#if SOC_ZDYN_ENABLE
	if (soc_zdyn_has_estimate())
	{
		uart_debug_printf(" z=%.2f%%(n=%lu,%.1fmohm,%lucyc)",
		                  (double)soc_zdyn_get_soc_pct(),
		                  (unsigned long)soc_zdyn_get_event_count(),
		                  (double)soc_zdyn_get_last_z_mohm(),
		                  (unsigned long)s_cyc_z);
	}
	else
	{
		uart_debug_printf(" z=--(no event yet)");
	}
#endif
	uart_debug_printf("\r\n");
}

#endif /* any SOC method enabled */


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
	ina_cal_init();
	ina_cal_uart_attach();
#if SOC_COULOMB_ENABLE
	soc_coulomb_init();
#endif
#if SOC_EKF_ENABLE
	soc_ekf_init();
#endif
#if SOC_ZDYN_ENABLE
	soc_zdyn_init();
#endif
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
				float i_cal = ina_cal_apply(snap.current_ma);
				if (ina_cal_is_valid())
				{
					uart_debug_printf("[%lus] alive V=%.1fmV I=%.1fmA Ical=%.1fmA P=%.1fmW i2c=ok ina=present cal=on\r\n",
					                  (unsigned long)s_seconds,
					                  (double)snap.bus_v_mv,
					                  (double)snap.current_ma,
					                  (double)i_cal,
					                  (double)snap.power_mw);
				}
				else
				{
					uart_debug_printf("[%lus] alive V=%.1fmV I=%.1fmA P=%.1fmW i2c=ok ina=present cal=off\r\n",
					                  (unsigned long)s_seconds,
					                  (double)snap.bus_v_mv,
					                  (double)snap.current_ma,
					                  (double)snap.power_mw);
				}

#if SOC_COULOMB_ENABLE || SOC_EKF_ENABLE || SOC_ZDYN_ENABLE
				/* cal 未載入時 ina_cal_apply() 為 identity，仍照餵（見 ina_cal.h） */
				soc_estimators_feed_1s(i_cal, snap.bus_v_mv);
				soc_estimators_print(s_seconds);
#endif
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
