#!/usr/bin/env python3
"""Flash MCU and verify boot banner + 1 Hz heartbeat on /dev/ttyACM2.

After the firmware-project-builder (skill + manual-equivalent) refactor:
  - Boot banner is printed once in once() via uart_debug_printf().
  - 100 µs base tick (TIM6 ISR) increments g_softWareTimCnt only — no UART.
  - 1 Hz heartbeat is scheduled in loop() via softWareTimTick_100us(Period=10000).
    Each tick prints either:
      "[Ns] alive — i2c=idle ina=absent"           (sensor not wired)
      "[Ns] alive V=..mV I=..mA P=..mW i2c=ok ina=present"  (sensor wired)
  - INA226 absence must NOT hard-fault — graceful "not detected" warn from once().
"""
from __future__ import annotations

import re
import subprocess
import threading
import time
from pathlib import Path

import serial


VCP = "/dev/ttyACM2"
BAUD = 115200
CAPTURE_SECONDS = 60.0
# SCRIPTS/ lives at the firmware-project root (SOC_RESEARCH/SCRIPTS/).
# The CubeIDE project (Makefile, sources, .ioc) is at
# SOC_RESEARCH/MCU/soc_research_mcu/ — MCU/ is a category folder above the
# CubeIDE root, whose name must match the .ioc base name.
PROJECT_ROOT = Path(__file__).resolve().parent.parent          # SOC_RESEARCH/
CUBE_DIR = PROJECT_ROOT / "MCU" / "soc_research_mcu"           # SOC_RESEARCH/MCU/soc_research_mcu/


def reader(ser: serial.Serial, lines: list, t0_holder: dict):
    while True:
        ln = ser.readline()
        if not ln:
            if time.monotonic() - t0_holder["t0"] > CAPTURE_SECONDS:
                return
            continue
        ts = time.monotonic() - t0_holder["t0"]
        text = ln.decode(errors="replace").rstrip("\r\n")
        lines.append((ts, text))
        print(f"[{ts:6.3f}s] {text}")


def main() -> int:
    print("[verify] opening", VCP)
    ser = serial.Serial(VCP, BAUD, timeout=0.5)

    # Drain anything left in the kernel buffer from previous runs, then sit
    # idle for 1 s to make sure no new data sneaks in before flash begins.
    print("[verify] draining stale UART buffer ...")
    ser.reset_input_buffer()
    drain_t0 = time.monotonic()
    while time.monotonic() - drain_t0 < 1.0:
        ser.read(4096)

    print("[verify] running `make flash` ...")
    flash = subprocess.run(
        ["make", "flash"], cwd=CUBE_DIR, capture_output=True, text=True, timeout=30,
    )

    # NOW start the reader, with t0 anchored to flash completion.
    lines: list[tuple[float, str]] = []
    t0_holder = {"t0": time.monotonic()}
    th = threading.Thread(target=reader, args=(ser, lines, t0_holder), daemon=True)
    th.start()
    if "Verified OK" not in flash.stdout + flash.stderr:
        print("[verify] FLASH FAILED:")
        print(flash.stdout[-1500:])
        print(flash.stderr[-1500:])
        return 1
    print("[verify] flash + verify OK; capturing UART for "
          f"{CAPTURE_SECONDS:.0f}s ...")

    # Re-anchor t0 to right after flash so the heartbeat lines map to MCU seconds.
    th.join(timeout=CAPTURE_SECONDS + 2.0)
    ser.close()

    # ── Verification ──
    # Boot banner: printed once in once() via uart_debug_printf().
    banner_seen = any("=== SOC_RESEARCH STM32G071RB boot ===" in t for _, t in lines)
    sysclk_ok = any(
        "SYSCLK=64MHz" in t and "I2C1=400kHz" in t and "TIM6=100us" in t
        for _, t in lines
    )
    # Graceful "INA226 absent" path:
    ina_warn = any("[INA226]" in t and "not detected" in t for _, t in lines)
    # I2C bus idle warn (no slave ACK):
    i2c_idle = any("[I2C1] no ACK at 0x40" in t for _, t in lines)

    # Find when the banner arrived; ignore any heartbeat lines that came before
    # it (those are leftover bytes the kernel buffered from the previous boot).
    banner_t = next(
        (ts for ts, t in lines if "=== SOC_RESEARCH" in t),
        None,
    )
    # Heartbeat shape: "[<n>s] alive ..."  (n = unsigned seconds since boot)
    tick_re = re.compile(r"\[(\d+)s\] alive")
    tick_pairs = [
        (ts, int(m.group(1)))
        for ts, t in lines
        for m in [tick_re.search(t)]
        if m and banner_t is not None and ts > banner_t
    ]

    print("\n──────── verification ────────")
    print(f"  banner present              : {'OK' if banner_seen else 'FAIL'}")
    print(f"  clock/peripheral line       : {'OK' if sysclk_ok else 'FAIL'}")
    print(f"  INA226 absent graceful warn : {'OK' if ina_warn else 'FAIL'}")
    print(f"  I2C1 idle (no slave) warn   : {'OK' if i2c_idle else 'FAIL'}")
    print(f"  heartbeat lines captured    : {len(tick_pairs)}")

    if len(tick_pairs) >= 2:
        intervals = [tick_pairs[i+1][0] - tick_pairs[i][0]
                     for i in range(len(tick_pairs) - 1)]
        avg = sum(intervals) / len(intervals)
        worst = max(abs(x - 1.0) for x in intervals)
        seq_ok = all(tick_pairs[i+1][1] == tick_pairs[i][1] + 1
                     for i in range(len(tick_pairs) - 1))
        print(f"  heartbeat interval avg      : {avg*1000:.1f} ms (target 1000 ms)")
        print(f"  heartbeat interval worst    : ±{worst*1000:.1f} ms vs 1 s")
        print(f"  heartbeat counter monotonic : {'OK' if seq_ok else 'FAIL — RESET / SKIP'}")
        ok = banner_seen and sysclk_ok and ina_warn and i2c_idle and seq_ok and worst < 0.05
    else:
        ok = False
        print("  not enough heartbeat lines — likely flash did not run / reset issue")

    print(f"\n[verify] overall: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
