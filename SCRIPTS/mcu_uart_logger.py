#!/usr/bin/env python3
"""mcu_uart_logger.py — 長時間記錄 MCU UART 輸出（三法 SOC 估測比較實驗用）。

從 /dev/ttyACM2 逐行讀 STM32 的每秒回報（alive 行＋soc 行），每行前面加
系統時間戳（ISO 與 unix epoch）寫入 TEST/data/mcu_soc_log_<ts>.log。
台架側 round_runner.py 的 CSV 也用同一顆系統時鐘，事後以 epoch 對齊即可
把「板端估測」對上「台架庫倫真值」。

特性：
  - 斷線（拔線／板子 reset 導致 USB re-enumerate）自動重連，事件寫入 log
  - 每行即時 flush，中途強制中斷不掉資料
  - 板子若 reset，開機 banner 會原樣入 log，可作 cc=100% 對齊標記
  - Ctrl-C（SIGINT/SIGTERM）優雅收尾

用法：
    python3 SCRIPTS/mcu_uart_logger.py [--port /dev/ttyACM2] [--baud 115200]
"""

import argparse
import os
import signal
import sys
import time
from datetime import datetime

import serial

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(ROOT, "TEST", "data")

_running = True


def _stop(signum, frame):
    global _running
    _running = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyACM2")
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(DATA_DIR, f"mcu_soc_log_{ts}.log")
    fp = open(out_path, "a", encoding="utf-8")

    def emit(tag, text):
        now = time.time()
        iso = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        fp.write(f"{now:.3f}\t{iso}\t{tag}\t{text}\n")
        fp.flush()

    print(f"[logger] → {out_path}")
    emit("logger", f"start port={args.port} baud={args.baud}")

    ser = None
    n_lines = 0
    last_report = time.time()
    while _running:
        # ---- (re)connect ----
        if ser is None:
            try:
                ser = serial.Serial(args.port, args.baud, timeout=1.0)
                emit("logger", "port opened")
                print(f"[logger] {args.port} opened")
            except (serial.SerialException, OSError) as e:
                emit("logger", f"open failed: {e}; retry in 2s")
                time.sleep(2.0)
                continue
        # ---- read ----
        try:
            ln = ser.readline()
        except (serial.SerialException, OSError) as e:
            emit("logger", f"read error: {e}; reconnecting")
            try:
                ser.close()
            except Exception:
                pass
            ser = None
            time.sleep(1.0)
            continue
        if ln:
            emit("mcu", ln.decode(errors="replace").rstrip("\r\n"))
            n_lines += 1
        if time.time() - last_report >= 600.0:
            print(f"[logger] alive, {n_lines} lines so far "
                  f"({datetime.now().strftime('%H:%M:%S')})")
            last_report = time.time()

    emit("logger", f"stop ({n_lines} lines)")
    fp.close()
    if ser is not None:
        ser.close()
    print(f"[logger] stopped, {n_lines} lines → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
