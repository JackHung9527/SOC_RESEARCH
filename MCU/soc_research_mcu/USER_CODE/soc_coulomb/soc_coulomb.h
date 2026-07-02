/*
 * soc_coulomb.h — 庫倫計數法 SOC 估測（論文 4.1；兼三法比較之基準真值）。
 *
 * 演算法（每秒一次，對應圖 4-1）：
 *     SOC(t) = SOC(t0) - (1/C_rated) * ∫ I dτ         （放電為正）
 *
 * 嵌入式實作重點（對應 4.1.3「三法中最輕量、資源下界」）：
 *   - 全整數運算，不用浮點：電流以 µA (int32) 餵入、電荷累加器 int64 µA·s、
 *     SOC 以 0.01% 解析度 (int32, 0..10000) 輸出。
 *   - int64 累加器避免長時間積分的量化流失；乘除順序保證不溢位
 *     （|q| < 2^43 µA·s 時 q*10000 仍遠小於 2^63）。
 *   - 無查表、無矩陣、無收斂機制；初值錯誤永不恢復（4.4.2 預期失分項）。
 *
 * set_soc() 供外部重新錨定（例如放電起點錨 100%、或混合策略之離散校正）。
 */

#ifndef SOC_COULOMB_H_
#define SOC_COULOMB_H_

#include <stdint.h>

void    soc_coulomb_init(void);                        /* 以 model_set 預設初值起步 */
void    soc_coulomb_set_soc(int32_t soc_pct_x100);     /* 重新錨定（0..10000 = 0..100%） */
void    soc_coulomb_update_1s(int32_t i_ua);           /* 每秒餵一次校正後電流（µA，放電為正） */
int32_t soc_coulomb_get_pct_x100(void);                /* 目前 SOC（0.01% 解析度，已夾限） */
int64_t soc_coulomb_get_out_uas(void);                 /* 自上次錨定起累計流出電荷（µA·s） */

#endif /* SOC_COULOMB_H_ */
