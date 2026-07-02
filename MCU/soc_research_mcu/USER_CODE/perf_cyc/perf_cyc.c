/*
 * perf_cyc.c — SysTick 為基底的 cycle 計時實作。
 *
 * 快照一致性：讀 uwTick 與 SysTick->VAL 之間若剛好跨過 reload，兩者會
 * 不同步（差一整個 LOAD+1）。用「讀兩次 tick 夾住 VAL、不一致就重讀」
 * 消除，最多重試一次即穩定。
 */

#include "global_includes.h"

#if SOC_PERF_ENABLE

void perf_cyc_begin(perf_cyc_t *t)
{
    uint32_t tick;
    uint32_t val;

    do
    {
        tick = HAL_GetTick();
        val  = SysTick->VAL;
    } while (tick != HAL_GetTick());

    t->tick0 = tick;
    t->val0  = val;
}

uint32_t perf_cyc_end(const perf_cyc_t *t)
{
    uint32_t tick;
    uint32_t val;
    int64_t  cyc;

    do
    {
        tick = HAL_GetTick();
        val  = SysTick->VAL;
    } while (tick != HAL_GetTick());

    cyc = ((int64_t)(uint32_t)(tick - t->tick0) * (int64_t)(SysTick->LOAD + 1U))
        + (int64_t)t->val0 - (int64_t)val;

    if (cyc < 0)
    {
        cyc = 0;
    }
    return (uint32_t)cyc;
}

#endif /* SOC_PERF_ENABLE */
