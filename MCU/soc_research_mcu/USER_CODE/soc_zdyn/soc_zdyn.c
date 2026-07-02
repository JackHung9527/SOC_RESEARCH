/*
 * soc_zdyn.c — 動態阻抗法實作（浮點；軟浮點模擬，G071 無 FPU）。
 *
 * 晶片上只存幾個擬合係數；事件時一次差分＋一次開根解二次式，
 * 事件間每秒一次乘加內插——運算量介於庫倫計數與 EKF 之間（4.3.4）。
 */

#include "global_includes.h"
#include <math.h>

#if SOC_ZDYN_ENABLE

/* ---- 模組狀態 ---- */
static bool     s_prev_valid;
static float    s_prev_i_ma;
static float    s_prev_v_mv;

static bool     s_anchored;       /* 首個事件後為 true */
static float    s_soc_anchor;     /* 事件解出之 SOC（0..1） */
static float    s_q_out_mas;      /* 錨定後累計流出電荷（mA·s） */

static bool     s_prev_z_valid;
static float    s_prev_z_mohm;    /* 前一事件之 Z（分枝趨勢判斷用） */
static float    s_last_z_mohm;
static uint32_t s_event_cnt;

static float clampf01(float x)
{
    if (x < 0.0f)
    {
        x = 0.0f;
    }
    if (x > 1.0f)
    {
        x = 1.0f;
    }
    return x;
}

/* 目前內插 SOC（0..1）；未錨定回 -1 */
static float zdyn_soc_now(void)
{
    if (!s_anchored)
    {
        return -1.0f;
    }
    return clampf01(s_soc_anchor
                    - s_q_out_mas / (SOC_ZDYN_CAPACITY_MAH * 3600.0f));
}

/* 解 a·s² + b·s + (c - z) = 0 並依分枝規則取唯一解（0..1） */
static float zdyn_solve_soc(float z_mohm, float i_ma)
{
    const float a = SOC_ZDYN_COEF_A_MOHM;
    const float b = SOC_ZDYN_COEF_B_MOHM;
    const float c = SOC_ZDYN_COEF_C_MOHM;

    float vertex = -b / (2.0f * a);
    float disc   = (b * b) - (4.0f * a * (c - z_mohm));

    if (disc <= 0.0f)
    {
        /* 量得的 Z 低於（或等於）擬合曲線最低點：夾到頂點 */
        return clampf01(vertex);
    }

    float sq = sqrtf(disc);
    float s_lo = clampf01((-b - sq) / (2.0f * a));   /* 頂點左側（低 SOC） */
    float s_hi = clampf01((-b + sq) / (2.0f * a));   /* 頂點右側（高 SOC） */

    if (s_anchored)
    {
        /* 連續性準則：取距目前內插 SOC 較近之根 */
        float now = zdyn_soc_now();
        return (fabsf(s_lo - now) <= fabsf(s_hi - now)) ? s_lo : s_hi;
    }

    if (s_prev_z_valid)
    {
        /* Z 趨勢 × 電流方向 → 判頂點側（[1] 之變化率正負判別） */
        bool discharging = (i_ma > 0.0f);
        bool z_rising    = (z_mohm > s_prev_z_mohm);
        bool below_vertex = (discharging && z_rising) || (!discharging && !z_rising);
        return below_vertex ? s_lo : s_hi;
    }

    /* 無任何歷史：協定自滿電起放，預設高 SOC 側 */
    return s_hi;
}

void soc_zdyn_init(void)
{
    s_prev_valid   = false;
    s_anchored     = false;
    s_soc_anchor   = 0.0f;
    s_q_out_mas    = 0.0f;
    s_prev_z_valid = false;
    s_prev_z_mohm  = 0.0f;
    s_last_z_mohm  = 0.0f;
    s_event_cnt    = 0U;
}

void soc_zdyn_update_1s(float i_ma, float v_mv)
{
    /* 事件間內插：Δt = 1 s，電荷增量 (mA·s) 數值上等於電流 (mA) */
    if (s_anchored)
    {
        s_q_out_mas += i_ma;
    }

    if (s_prev_valid)
    {
        float di = i_ma - s_prev_i_ma;
        float adi = fabsf(di);

        if ((adi >= SOC_ZDYN_DI_MIN_MA) && (adi <= SOC_ZDYN_DI_MAX_MA))
        {
            /* mV/mA = Ω → ×1000 換 mΩ */
            float z = fabsf((v_mv - s_prev_v_mv) / di) * 1000.0f;

            if (z <= SOC_ZDYN_Z_MAX_MOHM)
            {
                float soc = zdyn_solve_soc(z, i_ma);

                s_soc_anchor   = soc;
                s_q_out_mas    = 0.0f;
                s_anchored     = true;
                s_prev_z_mohm  = z;
                s_prev_z_valid = true;
                s_last_z_mohm  = z;
                s_event_cnt++;
            }
        }
    }

    s_prev_i_ma  = i_ma;
    s_prev_v_mv  = v_mv;
    s_prev_valid = true;
}

bool soc_zdyn_has_estimate(void)
{
    return s_anchored;
}

float soc_zdyn_get_soc_pct(void)
{
    float s = zdyn_soc_now();
    return (s < 0.0f) ? -1.0f : (s * 100.0f);
}

float soc_zdyn_get_last_z_mohm(void)
{
    return s_last_z_mohm;
}

uint32_t soc_zdyn_get_event_count(void)
{
    return s_event_cnt;
}

#endif /* SOC_ZDYN_ENABLE */
