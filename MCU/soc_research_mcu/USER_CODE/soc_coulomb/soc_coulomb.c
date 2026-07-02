/*
 * soc_coulomb.c — 庫倫計數法實作（全整數）。
 *
 * 每秒工作量：一次 int64 加法（累加）＋讀取時一次 int64 乘除（正規化）。
 * SOC 換算不在 update 內做，get 時才算——update 熱路徑只剩累加，
 * 是 4.4.3 資源比較的運算量下界。
 */

#include "global_includes.h"

#if SOC_COULOMB_ENABLE

/* 額定容量換 µA·s：mAh * 3600 * 1000 */
#define SOC_COULOMB_CAP_UAS  ((int64_t)SOC_COULOMB_CAPACITY_MAH * 3600LL * 1000LL)

static int32_t s_soc0_x100;    /* 錨定點 SOC（0.01%） */
static int64_t s_q_out_uas;    /* 自錨定起累計流出電荷（µA·s，放電為正） */

void soc_coulomb_init(void)
{
    s_soc0_x100 = SOC_COULOMB_SOC0_PCT_X100;
    s_q_out_uas = 0;
}

void soc_coulomb_set_soc(int32_t soc_pct_x100)
{
    if (soc_pct_x100 < 0)
    {
        soc_pct_x100 = 0;
    }
    if (soc_pct_x100 > 10000)
    {
        soc_pct_x100 = 10000;
    }
    s_soc0_x100 = soc_pct_x100;
    s_q_out_uas = 0;
}

void soc_coulomb_update_1s(int32_t i_ua)
{
    /* Δt 固定 1 s：電荷增量 (µA·s) 數值上等於電流 (µA) */
    s_q_out_uas += (int64_t)i_ua;
}

int32_t soc_coulomb_get_pct_x100(void)
{
    int64_t soc = (int64_t)s_soc0_x100 - ((s_q_out_uas * 10000LL) / SOC_COULOMB_CAP_UAS);

    if (soc < 0)
    {
        soc = 0;
    }
    if (soc > 10000)
    {
        soc = 10000;
    }
    return (int32_t)soc;
}

int64_t soc_coulomb_get_out_uas(void)
{
    return s_q_out_uas;
}

#endif /* SOC_COULOMB_ENABLE */
