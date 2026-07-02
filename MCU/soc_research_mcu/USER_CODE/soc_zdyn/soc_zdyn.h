/*
 * soc_zdyn.h — 動態阻抗法 SOC 估測（論文 4.3；圖 4-3 即時估測階段）。
 *
 * 原理（Lin et al. [1]，二次擬合係數為 fresh-cell rounds 1–3 實測，表 4-3）：
 *     |ΔV/ΔI| = a·SOC² + b·SOC + c        （SOC 以 0..1 分數代入，阻抗 mΩ）
 *
 * 即時流程（每秒餵一次樣本）：
 *   1. 事件偵測：相鄰兩秒樣本 |ΔI| 落在 [DI_MIN, DI_MAX] 視為協定注入之
 *      dV/dI 擾動（每 60 s 由基礎倍率步降至 0.2C、dwell 1 s，步降/步回各成一事件）。
 *   2. 量測 Z = |ΔV/ΔI|，解二次式取兩根，依分枝規則挑唯一解，夾限 [0,1]。
 *   3. 事件間以模組內部之浮點庫倫積分自錨定點內插（「阻抗離散校正＋庫倫內插」
 *      混合形態，4.3.2；內部自帶積分器使本模組 footprint 量測時自足、不依賴
 *      soc_coulomb 模組）。
 *
 * 分枝選擇（拋物線對稱、單一 Z 對應兩個 SOC）：
 *   - 已有錨定 → 取距目前內插 SOC 較近之根（連續性準則）。
 *   - 尚無錨定但有前一事件 Z → 依 Z 趨勢與電流方向判在頂點哪一側 [1]：
 *       放電中 Z 遞增 → SOC 已低於頂點（取小根）；Z 遞減 → 高於頂點（取大根）。
 *   - 完全無歷史 → 預設取大根（實驗協定自滿電起放）。
 *
 * 無須初始值：首個擾動事件即產生獨立估測（4.4.2 初值恢復之理論最快者）。
 */

#ifndef SOC_ZDYN_H_
#define SOC_ZDYN_H_

#include <stdint.h>
#include <stdbool.h>

void     soc_zdyn_init(void);
void     soc_zdyn_update_1s(float i_ma, float v_mv);  /* 每秒餵一次（校正後電流，放電為正） */
bool     soc_zdyn_has_estimate(void);                 /* 首個擾動事件後才為 true */
float    soc_zdyn_get_soc_pct(void);                  /* 0..100（未錨定時回 -1） */
float    soc_zdyn_get_last_z_mohm(void);              /* 最近一次事件量得之 |ΔV/ΔI|（mΩ） */
uint32_t soc_zdyn_get_event_count(void);              /* 累計已採用之擾動事件數 */

#endif /* SOC_ZDYN_H_ */
