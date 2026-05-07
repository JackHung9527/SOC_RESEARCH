/*
 * ina_cal.h — INA226 多點線性內插電流校正 + last-page flash 儲存。
 *
 * 校正模型（純 N-point piecewise linear，沒有 LUT 反查、沒有 polyfit）：
 *
 *     原始 ina226 量測值 raw_ma  ──→  apply()  ──→  校正後 cal_ma
 *
 *     已知 N 個點 (raw_i, ref_i)，依 raw_i 升冪排序：
 *         raw_ma <= raw_0          → cal_ma = ref_0 + slope_0 * (raw_ma - raw_0)        // 邊界外左推
 *         raw_i <= raw_ma <= raw_{i+1}
 *                                  → cal_ma = ref_i + (ref_{i+1}-ref_i)/(raw_{i+1}-raw_i) * (raw_ma - raw_i)
 *         raw_ma >= raw_{N-1}      → 用最後一段斜率外推
 *
 * 儲存：MCU 內部 flash 最後一頁（G071RB 128KB / 2KB page → page 63 @ 0x0801F800），
 *      整段 record 對齊 8 bytes，DOUBLEWORD 寫入。
 *      Boot 時 ina_cal_init() 嘗試 load；magic + CRC 任一不對就標 invalid，apply()
 *      會直接回 raw_ma（identity，等同未校正）。
 *
 * Host 端介面：透過 uart_debug 收到的 ASCII 命令觸發；
 *      由本模組 register 一個 line callback。
 *      所有命令見 ina_cal_uart_cli_help()。
 */

#ifndef INA_CAL_H_
#define INA_CAL_H_

#include <stdint.h>
#include <stdbool.h>


#define INA_CAL_MAGIC        ((uint32_t)0x494E4143U)   /* 'I''N''A''C' */
#define INA_CAL_VERSION      ((uint16_t)1U)
#define INA_CAL_MAX_POINTS   (16U)


/* 在 RAM 中持有的校正表。寫入 flash 的 record 直接 memcpy 這個結構。
 * 大小固定，與 flash 上的 layout 完全一致；改 layout 必 bump version。 */
/* 全部欄位都是 4-byte naturally aligned；不用 __packed__。
 * 為了讓總長度對 8-byte 對齊（DOUBLEWORD program 要求），
 * crc32 後補 1 個 uint32_t 的 pad。
 *
 * 大小計算：
 *   magic(4) + version(2) + n_points(2) = 8
 *   raw_ma[16] (float) = 64
 *   ref_ma[16] (float) = 64
 *   reserved[4]        = 16
 *   crc32(4) + pad(4)  = 8
 *   total              = 160 bytes (= 20 doublewords)
 */
typedef struct
{
    uint32_t magic;                              /* INA_CAL_MAGIC */
    uint16_t version;                            /* INA_CAL_VERSION */
    uint16_t n_points;                           /* 有效點數 0..INA_CAL_MAX_POINTS */
    float    raw_ma[INA_CAL_MAX_POINTS];         /* INA226 報的 mA（升冪） */
    float    ref_ma[INA_CAL_MAX_POINTS];         /* 對應 reference 真值（mA） */
    uint32_t reserved[4];                        /* 保留欄位（寫 0） */
    uint32_t crc32;                              /* CRC32 over [magic .. reserved[3]] */
    uint32_t pad;                                /* 對 8-byte 補齊；CRC 不涵蓋 */
} ina_cal_record_t;


/* APIs (called from once() / loop()) */
void  ina_cal_init(void);                                       /* once() — load flash */
void  ina_cal_handle(void);                                     /* loop() — currently no-op */

/* 套用內插。若無有效校正表，直接回傳 raw_ma（identity）。 */
float ina_cal_apply(float raw_ma);

bool  ina_cal_is_valid(void);
uint16_t ina_cal_n_points(void);
const ina_cal_record_t *ina_cal_get_record(void);


/* 給 ina_cal CLI 用的內部 builder API（也可由其他模組直接使用） */
void  ina_cal_table_clear(void);
bool  ina_cal_table_push(float raw_ma, float ref_ma);            /* append; 滿 16 點則拒絕 */
bool  ina_cal_table_commit(void);                                /* erase last page + program */
bool  ina_cal_table_reload_from_flash(void);                     /* re-read */


/* Hook 進 uart_debug：在 once() 裡呼叫 ina_cal_uart_attach()，
 * 之後從 host 發來的整行 ASCII 命令會經過 ina_cal_dispatch_line()。
 * 命令清單：
 *   HELP / CAL_HELP            — 印出命令清單
 *   CAL_RAW                    — 回 "RAW BUS=<mv> SHU=<uv> INA=<ma>"
 *   CAL_RESET                  — 清空 RAM 表（不動 flash）
 *   CAL_PUSH <raw_ma> <ref_ma> — 加入一個 (raw, ref) 點
 *   CAL_COMMIT                 — RAM 表寫入 flash 最後一頁
 *   CAL_LOAD                   — 從 flash 重新載入
 *   CAL_DUMP                   — 印出 RAM 表
 *   CAL_GET_I                  — 印出當前 raw 套用內插後的校正電流
 *   RESET                      — NVIC_SystemReset
 */
void  ina_cal_uart_attach(void);
void  ina_cal_dispatch_line(const char *line, uint16_t len);

#endif /* INA_CAL_H_ */
