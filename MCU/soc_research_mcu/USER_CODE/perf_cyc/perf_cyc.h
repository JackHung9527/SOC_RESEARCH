/*
 * perf_cyc.h — 單次區段 CPU cycle 計時（給論文 4.4.3「每次更新運算量」量測用）。
 *
 * Cortex-M0+ 沒有 DWT CYCCNT，改用 SysTick 換算：
 *   HAL 預設 SysTick 以 SYSCLK (64 MHz) 遞減、每 1 ms reload（LOAD = 63999），
 *   cycles = (tick 差) * (LOAD+1) + (VAL 起 - VAL 迄)
 *   → 解析度 1 cycle，量測範圍不限（跨 ms 由 uwTick 差補足）。
 *
 * 使用方式（量測區段內不得關 SysTick 中斷，否則 uwTick 停走）：
 *     perf_cyc_t t;
 *     perf_cyc_begin(&t);
 *     ... 待測程式 ...
 *     uint32_t cyc = perf_cyc_end(&t);
 *
 * 本模組屬「量測儀器」而非估測方法本體：footprint 變體比較時所有變體
 * 一律保持 SOC_PERF_ENABLE=1，使其成本在相減時互相抵銷。
 */

#ifndef PERF_CYC_H_
#define PERF_CYC_H_

#include <stdint.h>
#include "model_set.h"

typedef struct
{
    uint32_t tick0;   /* HAL_GetTick() 快照（ms） */
    uint32_t val0;    /* SysTick->VAL 快照（遞減計數） */
} perf_cyc_t;

#if SOC_PERF_ENABLE
void     perf_cyc_begin(perf_cyc_t *t);
uint32_t perf_cyc_end(const perf_cyc_t *t);
#else
/* 量測儀器關閉時退化為 no-op，呼叫端不用改碼 */
static inline void     perf_cyc_begin(perf_cyc_t *t) { (void)t; }
static inline uint32_t perf_cyc_end(const perf_cyc_t *t) { (void)t; return 0U; }
#endif

#endif /* PERF_CYC_H_ */
