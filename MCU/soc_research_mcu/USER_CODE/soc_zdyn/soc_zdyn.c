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

/* ---- 分箱平均降噪（§A）：庫倫參考 + 每 SOC 箱之 Z 累積 ---- */
static float    s_soc_cc;         /* 內建庫倫 SOC 參考（0..1，供分箱與分枝） */
static bool     s_cc_valid;       /* 收到首筆樣本後為 true（庫倫開始積分） */
static float    s_bin_zsum[SOC_ZDYN_NBINS];  /* 各箱 Z 累積和（mΩ） */
static uint32_t s_bin_n[SOC_ZDYN_NBINS];     /* 各箱事件數 */

/* ---- 靈敏度加權融合（§3）：本 tick 待消費之閘控觀測 ---- */
static bool     s_gated_pending;  /* 本 tick 有新的、通過閘控之事件待 EKF 消費 */
static float    s_gated_soc;      /* 該事件之 Z 反解 SOC（0..1） */
static float    s_gated_r_var;    /* 該事件之量測變異數（SOC-frac²） */
static uint32_t s_fuse_cnt;       /* 累計已通過閘控（可餵 EKF）之事件數 */

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

/* 解 a·s² + b·s + (c - z) = 0，取距庫倫參考 soc_ref 較近之根（0..1）。
 * 拋物線對稱、單一 Z 對應兩 SOC；以庫倫參考挑根，避開雜訊 SOC 之趨勢判斷。 */
static float zdyn_invert(float z_mohm, float soc_ref)
{
    const float a = SOC_ZDYN_COEF_A_MOHM;
    const float b = SOC_ZDYN_COEF_B_MOHM;
    const float c = SOC_ZDYN_COEF_C_MOHM;

    float disc = (b * b) - (4.0f * a * (c - z_mohm));

    if (disc <= 0.0f)
    {
        /* 量得的 Z 低於（或等於）擬合曲線最低點：夾到頂點 */
        return clampf01(-b / (2.0f * a));
    }

    float sq   = sqrtf(disc);
    float s_lo = clampf01((-b - sq) / (2.0f * a));   /* 頂點左側（低 SOC） */
    float s_hi = clampf01((-b + sq) / (2.0f * a));   /* 頂點右側（高 SOC） */

    return (fabsf(s_lo - soc_ref) <= fabsf(s_hi - soc_ref)) ? s_lo : s_hi;
}

/* SOC（0..1）→ 分箱索引 */
static uint32_t zdyn_bin_of(float soc_frac)
{
    int32_t idx = (int32_t)(soc_frac * (float)SOC_ZDYN_NBINS);
    if (idx < 0)                      idx = 0;
    if (idx >= SOC_ZDYN_NBINS)        idx = SOC_ZDYN_NBINS - 1;
    return (uint32_t)idx;
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
    s_soc_cc       = SOC_ZDYN_SOC0_PCT / 100.0f;
    s_cc_valid     = false;
    for (uint32_t k = 0U; k < SOC_ZDYN_NBINS; k++)
    {
        s_bin_zsum[k] = 0.0f;
        s_bin_n[k]    = 0U;
    }
    s_gated_pending = false;
    s_gated_soc    = 0.0f;
    s_gated_r_var  = 0.0f;
    s_fuse_cnt     = 0U;
}

/* 靈敏度加權閘控：對已解出之事件 SOC 算 g=|2a·SOC+b|，導出量測變異數
 * R=(σ_Z/g)²，通過門檻（R≤R_VAR_MAX）則登錄為本 tick 待消費之觀測。 */
static void zdyn_gate_event(float soc_frac)
{
#if SOC_ZDYN_EKF_FUSE
    float g = fabsf((2.0f * SOC_ZDYN_COEF_A_MOHM * soc_frac) + SOC_ZDYN_COEF_B_MOHM);
    if (g < SOC_ZDYN_DZDSOC_FLOOR)
    {
        g = SOC_ZDYN_DZDSOC_FLOOR;   /* 頂點附近夾住，避免 R 溢位 */
    }
    float sigma_soc = SOC_ZDYN_SIGMA_Z_MOHM / g;   /* SOC-frac */
    float r_var     = sigma_soc * sigma_soc;

    if (r_var <= SOC_ZDYN_R_VAR_MAX)               /* 靈敏度足夠 → 採用 */
    {
        s_gated_soc     = soc_frac;
        s_gated_r_var   = r_var;
        s_gated_pending = true;
        s_fuse_cnt++;
    }
#else
    (void)soc_frac;
#endif
}

void soc_zdyn_update_1s(float i_ma, float v_mv)
{
    /* 庫倫參考積分（供分箱與分枝；Δt = 1 s，SOC 減量 = i_ma·1s / 容量） */
    if (s_cc_valid)
    {
        s_soc_cc = clampf01(s_soc_cc - i_ma / (SOC_ZDYN_CAPACITY_MAH * 3600.0f));
    }
    else
    {
        s_cc_valid = true;   /* 首筆樣本起開始積分 */
    }

    /* 事件間內插：Δt = 1 s，電荷增量 (mA·s) 數值上等於電流 (mA) */
    if (s_anchored)
    {
        s_q_out_mas += i_ma;
    }

    if (s_prev_valid)
    {
        float di = i_ma - s_prev_i_ma;
        float adi = fabsf(di);

        /* 放電向過濾：Z(SOC) 曲線（表 4-3）由放電擾動辨識，僅雙樣本皆在
         * 放電負載下的事件在定義域內；充電階躍／起載邊緣一律剔除（4.4.2-2） */
        bool in_domain = (i_ma > SOC_ZDYN_I_FLOOR_MA) &&
                         (s_prev_i_ma > SOC_ZDYN_I_FLOOR_MA);

        if (in_domain && (adi >= SOC_ZDYN_DI_MIN_MA) && (adi <= SOC_ZDYN_DI_MAX_MA))
        {
            /* mV/mA = Ω → ×1000 換 mΩ */
            float z = fabsf((v_mv - s_prev_v_mv) / di) * 1000.0f;

            if (z <= SOC_ZDYN_Z_MAX_MOHM)
            {
                /* §A 分箱平均：累進當前庫倫 SOC 之箱，反解用平均 Z 降噪 */
                uint32_t bin = zdyn_bin_of(s_soc_cc);
                s_bin_zsum[bin] += z;
                s_bin_n[bin]++;

                float z_use = (s_bin_n[bin] >= SOC_ZDYN_BIN_MIN_N)
                              ? (s_bin_zsum[bin] / (float)s_bin_n[bin])  /* 降噪後 Z */
                              : z;                                       /* 樣本不足暫用單次 */

                float soc = zdyn_invert(z_use, s_soc_cc);

                s_soc_anchor   = soc;
                s_q_out_mas    = 0.0f;
                s_anchored     = true;
                s_prev_z_mohm  = z;
                s_prev_z_valid = true;
                s_last_z_mohm  = z;
                s_event_cnt++;

                zdyn_gate_event(soc);   /* 靈敏度加權：登錄可餵 EKF 之閘控觀測 */
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

bool soc_zdyn_take_gated_event(float *soc_frac, float *r_var)
{
    if (!s_gated_pending)
    {
        return false;
    }
    if (soc_frac != (void *)0)
    {
        *soc_frac = s_gated_soc;
    }
    if (r_var != (void *)0)
    {
        *r_var = s_gated_r_var;
    }
    s_gated_pending = false;   /* consume-once */
    return true;
}

uint32_t soc_zdyn_get_fuse_count(void)
{
    return s_fuse_cnt;
}

#endif /* SOC_ZDYN_ENABLE */
