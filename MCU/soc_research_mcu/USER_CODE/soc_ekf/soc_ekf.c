/*
 * soc_ekf.c — 一階 RC EKF 實作（軟浮點）。
 *
 * 內部一律 SI 單位（A / V / s / Ω），mA/mV 於 API 邊界換算。
 * P 為 2×2 對稱矩陣，只存 p00 / p01 / p11 三元素。
 */

#include "global_includes.h"
#include <math.h>

#if SOC_EKF_ENABLE

#include "soc_ekf_ocv_table.h"

/* ---- 離散化常數（init 時算一次） ---- */
static float s_a22;        /* e^{-Δt/τ1} */
static float s_b2;         /* R1(1 - e^{-Δt/τ1}) */
static float s_cap_as;     /* 容量（A·s） */

/* ---- 狀態與協方差 ---- */
static float s_soc;        /* 0..1 */
static float s_v1;         /* V */
static float s_p00;
static float s_p01;
static float s_p11;

static float clampf(float x, float lo, float hi)
{
    if (x < lo)
    {
        x = lo;
    }
    if (x > hi)
    {
        x = hi;
    }
    return x;
}

/* 分段線性 OCV 內插；回傳 V_OC（V），*slope 帶出該段 ∂V_OC/∂SOC（V/1） */
static float ocv_lookup(float soc, float *slope)
{
    uint32_t i;

    if (soc <= SOC_EKF_OCV_SOC[0])
    {
        i = 0U;
    }
    else if (soc >= SOC_EKF_OCV_SOC[SOC_EKF_OCV_N - 1U])
    {
        i = SOC_EKF_OCV_N - 2U;
    }
    else
    {
        i = 0U;
        while (SOC_EKF_OCV_SOC[i + 1U] < soc)
        {
            i++;
        }
    }

    float ds = SOC_EKF_OCV_SOC[i + 1U] - SOC_EKF_OCV_SOC[i];
    float k  = (SOC_EKF_OCV_V[i + 1U] - SOC_EKF_OCV_V[i]) / ds;

    *slope = k;
    return SOC_EKF_OCV_V[i] + k * (soc - SOC_EKF_OCV_SOC[i]);
}

void soc_ekf_init(void)
{
    s_a22    = expf(-SOC_EKF_DT_S / SOC_EKF_TAU1_S);
    s_b2     = SOC_EKF_R1_OHM * (1.0f - s_a22);
    s_cap_as = SOC_EKF_CAPACITY_MAH * 3.6f;   /* mAh → A·s */

    s_soc = SOC_EKF_SOC0_PCT / 100.0f;
    s_v1  = 0.0f;
    s_p00 = SOC_EKF_P0_SOC;
    s_p01 = 0.0f;
    s_p11 = SOC_EKF_P0_V1;
}

void soc_ekf_seed_from_voltage(float v_mv)
{
    /* 近似靜置：V_t ≈ V_OC，對佔位/實測 OCV 表反查（表單調遞增，線性反插） */
    float v = v_mv * 0.001f;
    uint32_t i;

    if (v <= SOC_EKF_OCV_V[0])
    {
        s_soc = SOC_EKF_OCV_SOC[0];
    }
    else if (v >= SOC_EKF_OCV_V[SOC_EKF_OCV_N - 1U])
    {
        s_soc = SOC_EKF_OCV_SOC[SOC_EKF_OCV_N - 1U];
    }
    else
    {
        i = 0U;
        while (SOC_EKF_OCV_V[i + 1U] < v)
        {
            i++;
        }
        s_soc = SOC_EKF_OCV_SOC[i]
              + (SOC_EKF_OCV_SOC[i + 1U] - SOC_EKF_OCV_SOC[i])
              * (v - SOC_EKF_OCV_V[i])
              / (SOC_EKF_OCV_V[i + 1U] - SOC_EKF_OCV_V[i]);
    }

    s_v1  = 0.0f;
    s_p00 = SOC_EKF_P0_SOC;
    s_p01 = 0.0f;
    s_p11 = SOC_EKF_P0_V1;
}

void soc_ekf_set_soc(float soc_pct)
{
    s_soc = clampf(soc_pct / 100.0f, 0.0f, 1.0f);
    s_p00 = SOC_EKF_P0_SOC;
    s_p01 = 0.0f;
}

void soc_ekf_update_1s(float i_ma, float v_mv)
{
    float i_a = i_ma * 0.001f;   /* 放電為正 */
    float v_t = v_mv * 0.001f;

    /* ---- 時間更新（預測） ---- */
    s_soc -= (SOC_EKF_DT_S / s_cap_as) * i_a;
    s_v1   = (s_a22 * s_v1) + (s_b2 * i_a);

    /* P = A P Aᵀ + Q（A = diag(1, a22)） */
    s_p01 = s_a22 * s_p01;
    s_p11 = (s_a22 * s_a22 * s_p11) + SOC_EKF_Q_V1;
    s_p00 = s_p00 + SOC_EKF_Q_SOC;

    /* ---- 量測更新 ---- */
    float dvoc;
    float voc = ocv_lookup(s_soc, &dvoc);
    float e   = v_t - (voc - (i_a * SOC_EKF_R0_OHM) - s_v1);

    /* C = [dvoc, -1]；S 為純量 → 增益免矩陣求逆（4.2.3） */
    float pc0 = (dvoc * s_p00) - s_p01;          /* (P Cᵀ)[0] */
    float pc1 = (dvoc * s_p01) - s_p11;          /* (P Cᵀ)[1] */
    float s   = (dvoc * pc0) - pc1 + SOC_EKF_R_MEAS_V2;
    float k0  = pc0 / s;
    float k1  = pc1 / s;

    s_soc += k0 * e;
    s_v1  += k1 * e;

    /* Joseph 形式：P = (I−KC) P (I−KC)ᵀ + K R Kᵀ（數值穩定） */
    float m00 = 1.0f - (k0 * dvoc);
    float m01 = k0;                  /* -k0 * c1, c1 = -1 */
    float m10 = -(k1 * dvoc);
    float m11 = 1.0f + k1;

    float t00 = (m00 * s_p00) + (m01 * s_p01);   /* M P 之第一列 */
    float t01 = (m00 * s_p01) + (m01 * s_p11);
    float t10 = (m10 * s_p00) + (m11 * s_p01);   /* M P 之第二列 */
    float t11 = (m10 * s_p01) + (m11 * s_p11);

    s_p00 = (t00 * m00) + (t01 * m01) + (k0 * k0 * SOC_EKF_R_MEAS_V2);
    s_p01 = (t10 * m00) + (t11 * m01) + (k0 * k1 * SOC_EKF_R_MEAS_V2);
    s_p11 = (t10 * m10) + (t11 * m11) + (k1 * k1 * SOC_EKF_R_MEAS_V2);

    /* ---- 輸出限幅 ---- */
    s_soc = clampf(s_soc, 0.0f, 1.0f);
    s_v1  = clampf(s_v1, -0.5f, 0.5f);
}

void soc_ekf_correct_soc(float soc_frac, float r_var)
{
    /* 直接觀測 SOC：C = [1, 0] → PCᵀ = [p00, p01]、S = p00 + R（純量）。 */
    float e = soc_frac - s_soc;
    float s = s_p00 + r_var;
    float k0 = s_p00 / s;
    float k1 = s_p01 / s;

    s_soc += k0 * e;
    s_v1  += k1 * e;

    /* Joseph 形式：M = I − KC = [[1−k0, 0], [−k1, 1]]，P = M P Mᵀ + K R Kᵀ */
    float m00 = 1.0f - k0;
    float m10 = -k1;

    float t00 = (m00 * s_p00);                   /* M P 第一列（m01=0；t01 不參與下列運算） */
    float t10 = (m10 * s_p00) + s_p01;           /* M P 第二列（m11=1） */
    float t11 = (m10 * s_p01) + s_p11;

    s_p00 = (t00 * m00) + (k0 * k0 * r_var);      /* Mᵀ 第一行 = [m00; 0] */
    s_p01 = (t10 * m00) + (k0 * k1 * r_var);
    s_p11 = (t10 * m10) + t11 + (k1 * k1 * r_var);/* Mᵀ 第二行 = [m10; 1] */

    s_soc = clampf(s_soc, 0.0f, 1.0f);
    s_v1  = clampf(s_v1, -0.5f, 0.5f);
}

float soc_ekf_get_soc_pct(void)
{
    return s_soc * 100.0f;
}

float soc_ekf_get_v1_mv(void)
{
    return s_v1 * 1000.0f;
}

#endif /* SOC_EKF_ENABLE */
