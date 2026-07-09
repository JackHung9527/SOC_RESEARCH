/*
 * model_set.h
 * 全專案可調參數集中區。修改這裡不需要改 driver 程式碼，也不需要動 main。
 *
 * 使用原則：
 *   - 所有 #define 形式的常數，集中在此檔
 *   - 同一份韌體支援多機種時，用 #ifdef MODEL_XXX 切換
 *   - driver / 應用層的程式碼一律從這裡讀參數，不要寫死數值
 *   - 修改後需 rebuild，不會有 runtime 開銷
 */

#ifndef MODEL_SET_H_
#define MODEL_SET_H_

/* ====================================================================
 * 機種選擇（同一專案多機種共用韌體時用 #ifdef 切換）
 * ==================================================================== */
#define MODEL_DEFAULT
// #define MODEL_VARIANT_A
// #define MODEL_VARIANT_B


/* ====================================================================
 * 系統時序
 * ==================================================================== */
#define MS_LOOP_TICK_PERIOD_US              100U      /* softwareTim tick = 100µs */


/* ====================================================================
 * Driver 參數（依使用到的 driver 分區塊填入）
 *
 * 各 driver scaffold skill 會在此檔對應位置插入參數區塊。
 * 區塊用以下 marker 包起來，方便日後維護：
 *
 *   /* === MODEL_SET_<DRIVER> BEGIN === * /
 *   ... 參數 ...
 *   /* === MODEL_SET_<DRIVER> END === * /
 * ==================================================================== */


/* === MODEL_SET_UART_DEBUG BEGIN === */
#define UART_DEBUG_TX_BUF_SIZE     512U   /* TX ring buffer */
#define UART_DEBUG_RX_LINE_SIZE    128U   /* RX line buffer */
#define UART_DEBUG_BAUD            115200UL   /* informational */
/* === MODEL_SET_UART_DEBUG END === */


/* === MODEL_SET_I2C_BUS BEGIN === */
#define I2C_BUS_TIMEOUT_MS      100U
#define I2C_BUS_BUS_SPEED       400000UL   /* informational */
/* === MODEL_SET_I2C_BUS END === */


/* === MODEL_SET_INA226 BEGIN === */
/* Pre-existing INA226 driver — no compile-time tunables exposed yet.
 * Runtime config (avg / conv-time / mode / shunt-ohm / Current_LSB) is set
 * via ina226_init() arguments; see USER_CODE/userCode.c::once() and
 * Core/Inc/main.h (APP_RSHUNT_OHM, APP_CURRENT_LSB_A) for the values used
 * at boot. */
/* === MODEL_SET_INA226 END === */


/* === MODEL_SET_BATTERY_MONITOR BEGIN === */
/* Pre-existing battery_monitor app layer — wraps the INA226 driver, samples
 * once per heartbeat (1 Hz). Tunables live for now in Core/Inc/main.h:
 *   APP_RSHUNT_OHM        Rshunt resistor (ohm)
 *   APP_CURRENT_LSB_A     Current LSB (A/LSB), per INA226 calibration eqn.
 * Migration of these into MODEL_SET_BATTERY_MONITOR is a follow-up. */
/* === MODEL_SET_BATTERY_MONITOR END === */


/* === MODEL_SET_INA_CAL BEGIN === */
/* INA226 N-point linear-interp current calibration storage.
 *   - Storage: last flash page (G071RB page 63 @ 0x0801F800, 2 KB).
 *   - Up to INA_CAL_MAX_POINTS = 16 calibration points.
 *   - Record protected by 'INAC' magic + version + CRC32.
 *   - apply() is identity passthrough until a valid record is loaded.
 * Knobs are compile-time (INA_CAL_MAX_POINTS in ina_cal.h); no runtime
 * tunables exposed here yet. */
/* === MODEL_SET_INA_CAL END === */


/* === MODEL_SET_SOC_SOH_CALC BEGIN === */
/* Pre-existing SOC/SOH algorithm stub — empirical Z-SOC LUT and temperature
 * compensation coefficients are not yet defined; algorithm is pending the
 * INA226 hardware connection and bench calibration run. Macros will land
 * here once calibration produces values. */
/* === MODEL_SET_SOC_SOH_CALC END === */


/* === MODEL_SET_PERF_CYC BEGIN === */
/* SysTick cycle 計時（4.4.3 每次更新運算量之量測儀器）。
 * footprint 變體比較時所有變體一律保持 =1，使其成本相減抵銷。 */
#ifndef SOC_PERF_ENABLE
#define SOC_PERF_ENABLE            1
#endif
/* === MODEL_SET_PERF_CYC END === */


/* === MODEL_SET_SOC_COULOMB BEGIN === */
/* 庫倫計數法（4.1）。enable 用 #ifndef 包裝，footprint 量測腳本
 * (SCRIPTS/footprint_report.py) 以 -DSOC_COULOMB_ENABLE=0 產生剔除變體。 */
#ifndef SOC_COULOMB_ENABLE
#define SOC_COULOMB_ENABLE         1
#endif
#define SOC_COULOMB_CAPACITY_MAH   1665      /* C_ref：Round 1 baseline 實測容量
                                              * （標稱 2000，derate 見
                                              * TEST/data/active_profile.json；
                                              * 與台架真值同一容量基準） */
#define SOC_COULOMB_SOC0_PCT_X100  10000     /* 開機初值 100.00%（協定自滿電起放） */

/* 充飽自動重錨（標準 BMS 做法）：V 高於門檻且 |I| 近零連續 N 秒
 * → cc 錨定 100%。解決「開機時電池非滿電」的錨定偏移（2026-07-07）。
 * 重錨後須先看到放電電流 > REARM 門檻才允許下一次重錨。 */
#define SOC_COULOMB_ANCHOR_EN       1        /* 0 = 關閉自動重錨 */
#define SOC_COULOMB_ANCHOR_V_MV     4150.0f  /* 門檻 = V_cv(4.20V) − 50mV */
#define SOC_COULOMB_ANCHOR_I_MA     20.0f    /* |I| 門檻（< CV 截止 50mA） */
#define SOC_COULOMB_ANCHOR_HOLD_S   60U      /* 連續滿足秒數 */
#define SOC_COULOMB_ANCHOR_REARM_MA 200.0f   /* 放電電流超過此值後重新武裝 */
/* === MODEL_SET_SOC_COULOMB END === */


/* === MODEL_SET_SOC_EKF BEGIN === */
/* 一階 RC EKF（4.2）。R0/R1/τ1 為 GITT 2026-07-05 鬆弛段最小平方辨識
 * （SCRIPTS/identify_rc_params.py，SOC 20–90% 中段平均，n=15；
 * 逐步值見 TEST/data/rc_params_20260705_215850.csv）。
 * OCV 表（GITT 實測）見 soc_ekf/soc_ekf_ocv_table.h。 */
#ifndef SOC_EKF_ENABLE
#define SOC_EKF_ENABLE             1
#endif
#define SOC_EKF_CAPACITY_MAH       1665.0f   /* 同 SOC_COULOMB_CAPACITY_MAH（實測容量） */
#define SOC_EKF_DT_S               1.0f
#define SOC_EKF_SOC0_PCT           100.0f
#define SOC_EKF_R0_OHM             0.0519f   /* 歐姆內阻（含快速極化，1RC 簡化）。
                                              * GITT 辨識值 75.9 mΩ 屬台架域（V 取自
                                              * IT8512 負載端、含 harness），扣除
                                              * Round 40 板端/台架域差 24.0 mΩ 換算
                                              * 至 INA226 電池端域（2026-07-07）；
                                              * R1/τ1 由零電流鬆弛段辨識，不受
                                              * 量測域影響。 */
#define SOC_EKF_R1_OHM             0.0213f   /* 極化電阻 */
#define SOC_EKF_TAU1_S             177.5f    /* 極化時間常數 R1·C1 */
#define SOC_EKF_Q_SOC              1.0e-8f   /* [待測] 過程雜訊（SOC 分量） */
#define SOC_EKF_Q_V1               1.0e-6f   /* [待測] 過程雜訊（V1 分量，V²） */
#define SOC_EKF_R_MEAS_V2          1.0e-4f   /* [待測] 量測雜訊 (10 mV)²（V²） */
#define SOC_EKF_P0_SOC             0.04f     /* 初始不確定度 (±20%)²（強健性測試設定） */
#define SOC_EKF_P0_V1              1.0e-4f
/* === MODEL_SET_SOC_EKF END === */


/* === MODEL_SET_SOC_ZDYN BEGIN === */
/* 動態阻抗法（4.3）。二次擬合係數為 fresh-cell rounds 1–3 合併實測（表 4-3）。
 * 事件偵測窗對應協定：每 60 s 由基礎倍率步降至 0.2C dwell 1 s；
 * 0.5C 基礎時 |ΔI| ≈ 600 mA（下限 300 保留裕度）、2.0C 時 ≈ 3.6 A。 */
#ifndef SOC_ZDYN_ENABLE
#define SOC_ZDYN_ENABLE            1
#endif
/* 係數以「INA226 電池端」量測域擬合（Round 40 板端 447 事件對台架真值
 * 重擬合，2026-07-07，擬合 RMSE 2.5 mΩ）。台架版（表 4-3：a=20.2/
 * b=−21.6/c=63.6）含負載端線材/接點電阻 ~24 mΩ，兩域斜率項幾乎相同、
 * 僅常數項平移——韌體必須用與其量測鏈同域的係數。 */
#define SOC_ZDYN_COEF_A_MOHM       18.0f     /* 板端擬合 a（mΩ） */
#define SOC_ZDYN_COEF_B_MOHM       -21.1f    /* 板端擬合 b（mΩ） */
#define SOC_ZDYN_COEF_C_MOHM       39.6f     /* 板端擬合 c（mΩ） */
#define SOC_ZDYN_CAPACITY_MAH      1665.0f   /* 事件間庫倫內插用（同上，實測容量） */
#define SOC_ZDYN_I_FLOOR_MA        50.0f     /* 放電向過濾：事件前後兩樣本電流皆須
                                              * 大於此值（排除充電側／起載邊緣事件，
                                              * 2026-07-07 Round 40 發現） */
#define SOC_ZDYN_DI_MIN_MA         300.0f    /* |ΔI| 下限：低於此視為非擾動 */
#define SOC_ZDYN_DI_MAX_MA         4500.0f   /* |ΔI| 上限：剔除 C-rate 切換等異常（4.4.2-2） */
#define SOC_ZDYN_Z_MAX_MOHM        200.0f    /* Z 合理上限：剔除離群量測 */
/* === MODEL_SET_SOC_ZDYN END === */


/* === MODEL_SET_USER BEGIN === */
/* 使用者自訂參數放這裡 */

/* === MODEL_SET_USER END === */


#endif /* MODEL_SET_H_ */
