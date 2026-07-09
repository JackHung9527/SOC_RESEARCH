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
#include <stdlib.h>    /* strtof（SOC CLI） */
#include <strings.h>   /* strncasecmp（SOC CLI） */
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

#if SOC_COULOMB_ENABLE && SOC_COULOMB_ANCHOR_EN
/* 充飽自動重錨：V > 門檻且 |I| 近零連續 HOLD_S 秒 → cc 錨 100%。
 * 一次重錨後解除武裝，看到放電電流 > REARM 門檻才再武裝。 */
static void soc_coulomb_anchor_poll(float i_ma, float v_mv)
{
	static bool     s_armed  = true;
	static uint32_t s_hold_s = 0U;

	if (!s_armed)
	{
		if (i_ma > SOC_COULOMB_ANCHOR_REARM_MA)
		{
			s_armed = true;
		}
		return;
	}

	if ((v_mv > SOC_COULOMB_ANCHOR_V_MV) &&
	    (i_ma < SOC_COULOMB_ANCHOR_I_MA) &&
	    (i_ma > -SOC_COULOMB_ANCHOR_I_MA))
	{
		s_hold_s++;
		if (s_hold_s >= SOC_COULOMB_ANCHOR_HOLD_S)
		{
			soc_coulomb_set_soc(10000);
			s_armed  = false;
			s_hold_s = 0U;
			uart_debug_printf("[soc] cc anchored to 100.00%% "
			                  "(full-charge detect)\r\n");
		}
	}
	else
	{
		s_hold_s = 0U;
	}
}
#endif /* SOC_COULOMB_ENABLE && SOC_COULOMB_ANCHOR_EN */

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

#if SOC_COULOMB_ENABLE && SOC_COULOMB_ANCHOR_EN
	/* 在 perf 計時之外輪詢，不污染 4.4.3 的 update cycle 數 */
	soc_coulomb_anchor_poll(i_ma, v_mv);
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

/* ---- SOC UART CLI（鏈式 dispatcher：SOC 命令在此處理，其餘轉發校正 CLI）
 *   SOC_ANCHOR          cc 錨定 100.00%（充飽後手動重錨）
 *   SOC_SET <pct>       cc 錨定至 <pct>%（0..100，測試用）
 *   SOC_EKF_SET <pct>   EKF 強制設 SOC（4.4.2 強健性測試用） */
static bool soc_cli_parse_pct(const char *s, uint16_t len, float *out)
{
	char buf[12];
	uint16_t n = 0U;

	while ((n < len) && (s[n] == ' '))
	{
		s++;
		len--;
	}
	if ((len == 0U) || (len >= sizeof(buf)))
	{
		return false;
	}
	for (n = 0U; n < len; n++)
	{
		buf[n] = s[n];
	}
	buf[len] = '\0';

	float v = strtof(buf, NULL);
	if ((v < 0.0f) || (v > 100.0f))
	{
		return false;
	}
	*out = v;
	return true;
}

static void soc_cli_dispatch(const char *line, uint16_t len)
{
	while ((len > 0U) && ((line[len - 1U] == '\r') || (line[len - 1U] == '\n')))
	{
		len--;
	}

	float pct;

#if SOC_COULOMB_ENABLE
	if ((len == 10U) && (strncasecmp(line, "SOC_ANCHOR", 10U) == 0))
	{
		soc_coulomb_set_soc(10000);
		uart_debug_printf("[soc] cc anchored to 100.00%% (cli)\r\n");
		return;
	}
	if ((len > 8U) && (strncasecmp(line, "SOC_SET ", 8U) == 0))
	{
		if (soc_cli_parse_pct(&line[8], (uint16_t)(len - 8U), &pct))
		{
			soc_coulomb_set_soc((int32_t)(pct * 100.0f));
			uart_debug_printf("[soc] cc set to %.2f%% (cli)\r\n", (double)pct);
		}
		else
		{
			uart_debug_printf("ERR SOC_SET: pct 需在 0..100\r\n");
		}
		return;
	}
#endif
#if SOC_EKF_ENABLE
	if ((len > 12U) && (strncasecmp(line, "SOC_EKF_SET ", 12U) == 0))
	{
		if (soc_cli_parse_pct(&line[12], (uint16_t)(len - 12U), &pct))
		{
			soc_ekf_set_soc(pct);
			uart_debug_printf("[soc] ekf set to %.2f%% (cli)\r\n", (double)pct);
		}
		else
		{
			uart_debug_printf("ERR SOC_EKF_SET: pct 需在 0..100\r\n");
		}
		return;
	}
#endif
	(void)pct;
	ina_cal_dispatch_line(line, len);   /* 非 SOC 命令 → 校正 CLI */
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
#if SOC_COULOMB_ENABLE || SOC_EKF_ENABLE || SOC_ZDYN_ENABLE
	/* SOC CLI 覆蓋 rx callback；非 SOC 命令由 soc_cli_dispatch 轉發回校正 CLI */
	uart_debug_set_rx_line_cb(soc_cli_dispatch);
#endif
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
