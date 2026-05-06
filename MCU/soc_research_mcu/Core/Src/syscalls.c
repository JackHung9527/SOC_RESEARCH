/*
 * @brief  Minimal newlib syscall stubs for a bare-metal target.
 *         Supplies just enough so that linking against libc / libm does not
 *         pull in undefined references.  No semihosting, no file I/O, no
 *         heap-aware printf — _write retarget is owned by USER_CODE/uart_debug
 *         (which sends bytes through the uart_debug TX ring buffer). This
 *         file must NOT also define _write or the linker will complain about
 *         multiple definitions.
 */

#include <errno.h>
#include <stdint.h>
#include <sys/stat.h>
#include <sys/times.h>

#undef errno
extern int errno;

extern uint8_t _end;            /* set by linker script — start of heap */
extern uint8_t _estack;         /* set by linker script — top of stack  */

/* sbrk: minimal, single-direction heap. Will refuse if the heap collides
 * with the current main stack pointer. */
void *_sbrk(int incr)
{
    static uint8_t *cur = 0;
    if (cur == 0) cur = &_end;

    register uint8_t *sp __asm__("sp");
    if ((cur + incr) > sp)
    {
        errno = ENOMEM;
        return (void *)-1;
    }

    uint8_t *prev = cur;
    cur += incr;
    return prev;
}

int _close(int fd)            { (void)fd; return -1; }
int _fstat(int fd, struct stat *st) { (void)fd; if (st) st->st_mode = S_IFCHR; return 0; }
int _isatty(int fd)           { (void)fd; return 1; }
int _lseek(int fd, int off, int whence) { (void)fd; (void)off; (void)whence; return 0; }
int _read(int fd, char *buf, int len)   { (void)fd; (void)buf; (void)len; return 0; }
/* _write is implemented by USER_CODE/uart_debug/uart_debug.c (printf retarget). */
int _getpid(void)             { return 1; }
int _kill(int pid, int sig)   { (void)pid; (void)sig; errno = EINVAL; return -1; }
void _exit(int status)        { (void)status; while (1) {} }
