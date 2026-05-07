/*
 * ina_cal.c — implementation per ina_cal.h.
 *
 * Flash layout (G071RB, 128KB / 2KB pages):
 *   - User app占 page 0..62 (0x0800_0000 .. 0x0801_F7FF)
 *   - Calibration page = page 63 (0x0801_F800 .. 0x0801_FFFF, 2 KB)
 *   - Record sizeof = 160 bytes，DOUBLEWORD 對齊（20 doublewords）
 *
 * 我們不引入 stm32-flash-scaffold 通用 driver，因為這裡只需要一頁、單 record、
 * 單一寫入點，整段 < 200 行直接寫掉更乾淨。
 */

#include "global_includes.h"
#include "ina_cal/ina_cal.h"
#include <stdlib.h>
#include <string.h>


/* ---------------- flash layout constants ---------------- */
#define INA_CAL_FLASH_PAGE       (63U)
#define INA_CAL_FLASH_BASE_ADDR  ((uint32_t)0x0801F800U)
#define INA_CAL_RECORD_BYTES     (sizeof(ina_cal_record_t))


_Static_assert((INA_CAL_RECORD_BYTES % 8U) == 0U,
               "ina_cal_record_t must be 8-byte aligned for DOUBLEWORD program");
_Static_assert(INA_CAL_RECORD_BYTES <= 256U,
               "ina_cal record larger than expected — re-check flash layout budget");


/* ---------------- in-RAM working table ---------------- */
static ina_cal_record_t s_table;
static bool             s_table_valid = false;       /* true 後 apply() 才會內插 */


/* ---------------- small SW CRC32 (ZIP / Ethernet poly 0xEDB88320) ---------------- */
/* table-less，跑 ~160 bytes 不到 0.1 ms，不值得吃 1 KB ROM 換速度 */
static uint32_t crc32_update(uint32_t crc, const uint8_t *data, uint32_t len)
{
    crc = ~crc;
    for (uint32_t i = 0U; i < len; ++i)
    {
        crc ^= (uint32_t)data[i];
        for (uint32_t b = 0U; b < 8U; ++b)
        {
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1U);
            crc = (crc >> 1) ^ (0xEDB88320U & mask);
        }
    }
    return ~crc;
}

static uint32_t record_compute_crc(const ina_cal_record_t *r)
{
    /* CRC over everything except the trailing crc32 + pad fields (last 8 bytes). */
    return crc32_update(0U, (const uint8_t *)r,
                        (uint32_t)(INA_CAL_RECORD_BYTES - 2U * sizeof(uint32_t)));
}


/* ---------------- flash R/W primitives ---------------- */
/* read：直接 memory-mapped */
static void flash_read_record(ina_cal_record_t *out)
{
    memcpy(out, (const void *)INA_CAL_FLASH_BASE_ADDR, INA_CAL_RECORD_BYTES);
}

/* erase last page */
static bool flash_erase_cal_page(void)
{
    HAL_FLASH_Unlock();
    FLASH_EraseInitTypeDef e = {0};
    e.TypeErase = FLASH_TYPEERASE_PAGES;
    e.Page      = INA_CAL_FLASH_PAGE;
    e.NbPages   = 1U;
    /* G0：只有一個 bank，無 Banks 欄位 */
    uint32_t err = 0U;
    HAL_StatusTypeDef st = HAL_FLASHEx_Erase(&e, &err);
    HAL_FLASH_Lock();
    return (st == HAL_OK) && (err == 0xFFFFFFFFU);
}

/* program：DOUBLEWORD（8 bytes）一次 */
static bool flash_program_record(const ina_cal_record_t *r)
{
    HAL_FLASH_Unlock();
    const uint8_t *src = (const uint8_t *)r;
    bool ok = true;
    for (uint32_t off = 0U; off < INA_CAL_RECORD_BYTES; off += 8U)
    {
        uint64_t dw;
        memcpy(&dw, src + off, sizeof(uint64_t));
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_DOUBLEWORD,
                              INA_CAL_FLASH_BASE_ADDR + off, dw) != HAL_OK)
        {
            ok = false;
            break;
        }
    }
    HAL_FLASH_Lock();
    return ok;
}


/* ---------------- public table API ---------------- */
void ina_cal_table_clear(void)
{
    memset(&s_table, 0, sizeof(s_table));
    s_table.magic     = INA_CAL_MAGIC;
    s_table.version   = INA_CAL_VERSION;
    s_table.n_points  = 0U;
    s_table_valid     = false;
}

bool ina_cal_table_push(float raw_ma, float ref_ma)
{
    if (s_table.n_points >= INA_CAL_MAX_POINTS)
    {
        return false;
    }
    s_table.raw_ma[s_table.n_points] = raw_ma;
    s_table.ref_ma[s_table.n_points] = ref_ma;
    s_table.n_points = (uint16_t)(s_table.n_points + 1U);
    /* push 階段不標 valid；要 commit 或 reload_from_flash 後才能用 apply() */
    return true;
}

/* 依 raw_ma 升冪排序（push 進來的順序未必對）— 內插需要單調 */
static void table_sort_by_raw(ina_cal_record_t *r)
{
    /* insertion sort：N <= 16 */
    for (uint16_t i = 1U; i < r->n_points; ++i)
    {
        float kr = r->raw_ma[i];
        float kf = r->ref_ma[i];
        int j = (int)i - 1;
        while (j >= 0 && r->raw_ma[j] > kr)
        {
            r->raw_ma[j + 1] = r->raw_ma[j];
            r->ref_ma[j + 1] = r->ref_ma[j];
            j--;
        }
        r->raw_ma[j + 1] = kr;
        r->ref_ma[j + 1] = kf;
    }
}

bool ina_cal_table_commit(void)
{
    if (s_table.n_points < 2U)
    {
        return false;        /* 線性內插至少要 2 點 */
    }
    table_sort_by_raw(&s_table);
    s_table.magic   = INA_CAL_MAGIC;
    s_table.version = INA_CAL_VERSION;
    s_table.crc32   = record_compute_crc(&s_table);

    if (!flash_erase_cal_page())
    {
        return false;
    }
    if (!flash_program_record(&s_table))
    {
        return false;
    }
    /* read-back verify */
    ina_cal_record_t check;
    flash_read_record(&check);
    if (memcmp(&check, &s_table, INA_CAL_RECORD_BYTES) != 0)
    {
        return false;
    }
    s_table_valid = true;
    return true;
}

bool ina_cal_table_reload_from_flash(void)
{
    ina_cal_record_t r;
    flash_read_record(&r);
    if (r.magic != INA_CAL_MAGIC || r.version != INA_CAL_VERSION)
    {
        return false;
    }
    if (r.n_points < 2U || r.n_points > INA_CAL_MAX_POINTS)
    {
        return false;
    }
    if (record_compute_crc(&r) != r.crc32)
    {
        return false;
    }
    /* 排序 invariant 保險再做一次（flash 上應該已排好）*/
    table_sort_by_raw(&r);
    memcpy(&s_table, &r, INA_CAL_RECORD_BYTES);
    s_table_valid = true;
    return true;
}


/* ---------------- piecewise linear interp ---------------- */
float ina_cal_apply(float raw_ma)
{
    if (!s_table_valid || s_table.n_points < 2U)
    {
        return raw_ma;       /* identity */
    }
    const float *xs = s_table.raw_ma;
    const float *ys = s_table.ref_ma;
    uint16_t n = s_table.n_points;

    /* 邊界外左推 */
    if (raw_ma <= xs[0])
    {
        float dx = xs[1] - xs[0];
        float k  = (dx != 0.0f) ? (ys[1] - ys[0]) / dx : 0.0f;
        return ys[0] + k * (raw_ma - xs[0]);
    }
    /* 邊界外右推 */
    if (raw_ma >= xs[n - 1U])
    {
        float dx = xs[n - 1U] - xs[n - 2U];
        float k  = (dx != 0.0f) ? (ys[n - 1U] - ys[n - 2U]) / dx : 0.0f;
        return ys[n - 1U] + k * (raw_ma - xs[n - 1U]);
    }
    /* 內插：bisect 找區間 */
    uint16_t lo = 0U, hi = (uint16_t)(n - 1U);
    while ((hi - lo) > 1U)
    {
        uint16_t mid = (uint16_t)((lo + hi) >> 1);
        if (raw_ma >= xs[mid]) lo = mid; else hi = mid;
    }
    float dx = xs[hi] - xs[lo];
    float k  = (dx != 0.0f) ? (ys[hi] - ys[lo]) / dx : 0.0f;
    return ys[lo] + k * (raw_ma - xs[lo]);
}

bool     ina_cal_is_valid(void)        { return s_table_valid; }
uint16_t ina_cal_n_points(void)        { return s_table_valid ? s_table.n_points : 0U; }
const ina_cal_record_t *ina_cal_get_record(void) { return &s_table; }


/* ---------------- once() / loop() hooks ---------------- */
void ina_cal_init(void)
{
    ina_cal_table_clear();
    if (ina_cal_table_reload_from_flash())
    {
        uart_debug_printf("[ina_cal] flash record loaded, n=%u\r\n",
                          (unsigned)s_table.n_points);
    }
    else
    {
        uart_debug_printf("[ina_cal] no valid flash record (identity passthrough)\r\n");
    }
}

void ina_cal_handle(void)
{
    /* nothing periodic — UART CLI 是 event-driven */
}


/* ---------------- UART CLI ---------------- */
/* 解析整行 ASCII：忽略 leading WS、CR/LF；token 用空白/tab 分隔 */
static bool tok_next(const char **p, const char *end, char *out, uint16_t out_sz)
{
    /* skip WS */
    while (*p < end && (**p == ' ' || **p == '\t')) (*p)++;
    if (*p >= end) return false;
    uint16_t i = 0U;
    while (*p < end && **p != ' ' && **p != '\t')
    {
        if (i + 1U < out_sz) out[i++] = **p;
        (*p)++;
    }
    out[i] = '\0';
    return (i > 0U);
}

static int strieq(const char *a, const char *b)
{
    while (*a && *b)
    {
        char ca = *a++; if (ca >= 'a' && ca <= 'z') ca = (char)(ca - 32);
        char cb = *b++; if (cb >= 'a' && cb <= 'z') cb = (char)(cb - 32);
        if (ca != cb) return 0;
    }
    return (*a == '\0' && *b == '\0');
}

static void cmd_help(void)
{
    uart_debug_printf(
        "CMD: HELP | CAL_RAW | CAL_RESET | CAL_PUSH <raw_ma> <ref_ma> | "
        "CAL_COMMIT | CAL_LOAD | CAL_DUMP | CAL_GET_I | RESET\r\n");
}

static void cmd_cal_raw(void)
{
    /* 直接讀 ina226 (battery_monitor 已經初始化過 ina226 handle) */
    extern bool battery_monitor_sample(void);
    extern bool battery_monitor_get_latest(battery_sample_t *out);

    if (!battery_monitor_sample())
    {
        uart_debug_printf("ERR INA226 sample failed\r\n");
        return;
    }
    battery_sample_t s;
    if (!battery_monitor_get_latest(&s))
    {
        uart_debug_printf("ERR INA226 latest failed\r\n");
        return;
    }
    uart_debug_printf("RAW BUS=%.3f SHU=%.3f INA=%.3f\r\n",
                      (double)s.bus_v_mv,
                      (double)0.0,
                      (double)s.current_ma);
}

static void cmd_cal_reset(void)
{
    ina_cal_table_clear();
    uart_debug_printf("OK CLEARED\r\n");
}

static void cmd_cal_push(const char *args, uint16_t len)
{
    const char *p = args;
    const char *end = args + len;
    char tok[32];
    if (!tok_next(&p, end, tok, sizeof(tok))) { uart_debug_printf("ERR need raw_ma\r\n"); return; }
    float raw = strtof(tok, NULL);
    if (!tok_next(&p, end, tok, sizeof(tok))) { uart_debug_printf("ERR need ref_ma\r\n"); return; }
    float ref = strtof(tok, NULL);
    if (!ina_cal_table_push(raw, ref))
    {
        uart_debug_printf("ERR table full (max=%u)\r\n", (unsigned)INA_CAL_MAX_POINTS);
        return;
    }
    uart_debug_printf("OK n=%u raw=%.3f ref=%.3f\r\n",
                      (unsigned)s_table.n_points, (double)raw, (double)ref);
}

static void cmd_cal_commit(void)
{
    if (!ina_cal_table_commit())
    {
        uart_debug_printf("ERR commit failed (n=%u)\r\n", (unsigned)s_table.n_points);
        return;
    }
    uart_debug_printf("OK WROTE n=%u CRC=%08lX\r\n",
                      (unsigned)s_table.n_points,
                      (unsigned long)s_table.crc32);
}

static void cmd_cal_load(void)
{
    if (!ina_cal_table_reload_from_flash())
    {
        uart_debug_printf("ERR no valid flash record\r\n");
        return;
    }
    uart_debug_printf("OK LOADED n=%u CRC=%08lX\r\n",
                      (unsigned)s_table.n_points,
                      (unsigned long)s_table.crc32);
}

static void cmd_cal_dump(void)
{
    uart_debug_printf("DUMP n=%u valid=%u\r\n",
                      (unsigned)s_table.n_points, (unsigned)s_table_valid);
    for (uint16_t i = 0U; i < s_table.n_points; ++i)
    {
        uart_debug_printf("P%u RAW=%.3f REF=%.3f\r\n",
                          (unsigned)i,
                          (double)s_table.raw_ma[i],
                          (double)s_table.ref_ma[i]);
    }
    uart_debug_printf("DUMP_END\r\n");
}

static void cmd_cal_get_i(void)
{
    extern bool battery_monitor_sample(void);
    extern bool battery_monitor_get_latest(battery_sample_t *out);

    if (!battery_monitor_sample()) { uart_debug_printf("ERR sample failed\r\n"); return; }
    battery_sample_t s;
    if (!battery_monitor_get_latest(&s)) { uart_debug_printf("ERR latest failed\r\n"); return; }
    float cal = ina_cal_apply(s.current_ma);
    uart_debug_printf("CAL_I raw=%.3f cal=%.3f valid=%u n=%u\r\n",
                      (double)s.current_ma, (double)cal,
                      (unsigned)s_table_valid, (unsigned)s_table.n_points);
}

static void cmd_reset(void)
{
    uart_debug_printf("OK RESETTING\r\n");
    /* 給 UART 一點 flush 時間 */
    HAL_Delay(50);
    NVIC_SystemReset();
}

void ina_cal_dispatch_line(const char *line, uint16_t len)
{
    if (line == NULL || len == 0U) return;

    /* 去尾巴的 \r */
    while (len > 0U && (line[len - 1U] == '\r' || line[len - 1U] == '\n')) len--;
    if (len == 0U) return;

    const char *p = line;
    const char *end = line + len;
    char cmd[16];
    if (!tok_next(&p, end, cmd, sizeof(cmd))) return;

    if (strieq(cmd, "HELP") || strieq(cmd, "CAL_HELP"))      cmd_help();
    else if (strieq(cmd, "CAL_RAW"))                          cmd_cal_raw();
    else if (strieq(cmd, "CAL_RESET"))                        cmd_cal_reset();
    else if (strieq(cmd, "CAL_PUSH"))                         cmd_cal_push(p, (uint16_t)(end - p));
    else if (strieq(cmd, "CAL_COMMIT"))                       cmd_cal_commit();
    else if (strieq(cmd, "CAL_LOAD"))                         cmd_cal_load();
    else if (strieq(cmd, "CAL_DUMP"))                         cmd_cal_dump();
    else if (strieq(cmd, "CAL_GET_I"))                        cmd_cal_get_i();
    else if (strieq(cmd, "RESET"))                            cmd_reset();
    else uart_debug_printf("ERR unknown cmd '%s' — try HELP\r\n", cmd);
}

void ina_cal_uart_attach(void)
{
    uart_debug_set_rx_line_cb(ina_cal_dispatch_line);
}
