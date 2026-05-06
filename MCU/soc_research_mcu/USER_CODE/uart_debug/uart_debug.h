/*
 * uart_debug.h
 * 由 stm32-uart-scaffold 自動產生
 *
 * 周邊：USART2（HAL handle = huart2）
 * Baud：115200
 *
 * IT-driven UART driver，含 TX ring buffer。
 * RX line buffer / printf retarget 由 sentinel 區塊控制是否保留。
 */

#ifndef UART_DEBUG_H_
#define UART_DEBUG_H_


/*
 * Task Select — 大項
 */
typedef enum
{
    Uart_debug_TaskSel_TaskAwait        = 0,
    Uart_debug_TaskSel_Service_Routine  = 1
} Uart_debug_TaskSel;


/*
 * Flow Select — 小項
 */
typedef enum
{
    /* common */
    Uart_debug_FlowSel_FlowAwait        = 0,
    Uart_debug_FlowSel_FirstFlow        = 1,
    /* Service Routine */
    Uart_debug_FlowSel_RxDispatch       = 1,
    Uart_debug_FlowSel_finish           = 2
} Uart_debug_FlowSel;


/* globals */
extern Uart_debug_TaskSel
    g_uart_debug_taskSel;
extern Uart_debug_FlowSel
    g_uart_debug_flowSel;

extern uint32_t
    g_uart_debug_cmd,
    g_uart_debug_cnt;


typedef void (*Uart_debug_RxLineCb)(const char *line, uint16_t len);


/* APIs */
void uart_debug_init(void);                                     /* once() */
void uart_debug_handle(void);                                   /* loop() */
void uart_debug_TASK(Uart_debug_TaskSel *task,
                          Uart_debug_FlowSel *flow);

uint16_t uart_debug_send(const uint8_t *data, uint16_t len);    /* 推 TX ring，回傳實際寫入 byte 數 */
int      uart_debug_printf(const char *fmt, ...);               /* vsnprintf + send，回傳 send 出的 byte 數 */
uint16_t uart_debug_tx_free(void);                              /* TX ring 剩餘可寫空間 */

void uart_debug_set_rx_line_cb(Uart_debug_RxLineCb cb);


#endif /* UART_DEBUG_H_ */
