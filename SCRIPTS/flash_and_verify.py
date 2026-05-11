#!/usr/bin/env python3
"""Flash MCU and verify boot banner + 1 Hz heartbeat on /dev/ttyACM2.

Auto-detects which mode the firmware is currently in (based on heartbeat
line content) and applies the matching pass criteria:

  absent  :  "[Ns] alive — i2c=idle ina=absent"
              ↳ require graceful warn lines on boot, no V/I/P expected.
  present :  "[Ns] alive V=..mV I=..mA P=..mW i2c=ok ina=present cal=on|off"
              ↳ require ID-match log on boot, V in 0.5..4.5 V, I/P parseable.

Common criteria (both modes):
  - boot banner printed once in once() via uart_debug_printf()
  - clock/peripheral line printed once with SYSCLK=64MHz / I2C1=400kHz / TIM6=100us
  - 100 µs base tick (TIM6 ISR) → 1 Hz heartbeat via softWareTimTick_100us(Period=10000)
  - heartbeat lines monotonic, worst jitter <50 ms vs 1 s
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

    # Find when the banner arrived; ignore any heartbeat lines that came before
    # it (those are leftover bytes the kernel buffered from the previous boot).
    banner_t = next(
        (ts for ts, t in lines if "=== SOC_RESEARCH" in t),
        None,
    )
    after_banner = [(ts, t) for ts, t in lines
                    if banner_t is not None and ts >= banner_t]

    # Auto-detect INA226 mode from heartbeat content. Two formats:
    #   absent:  "[Ns] alive — i2c=idle ina=absent"
    #   present: "[Ns] alive V=..mV I=..mA P=..mW i2c=ok ina=present cal=on|off"
    has_absent_heartbeat = any("ina=absent" in t for _, t in after_banner)
    has_present_heartbeat = any("ina=present" in t for _, t in after_banner)
    mode = "present" if has_present_heartbeat else ("absent" if has_absent_heartbeat else "unknown")

    # Mode-specific checks
    if mode == "absent":
        ina_status_ok = any("[INA226]" in t and "not detected" in t for _, t in lines)
        i2c_status_ok = any("[I2C1] no ACK at 0x40" in t for _, t in lines)
        ina_label = "INA226 absent graceful warn"
        i2c_label = "I2C1 idle (no slave) warn"
    elif mode == "present":
        # Firmware boot strings when INA226 ACKs:
        #   "[INA226] CONFIG/CAL written, monitor armed."
        #   "[I2C1] device ACKed at 0x40"
        ina_status_ok = any(
            "[INA226]" in t and ("CONFIG/CAL written" in t or "monitor armed" in t)
            for _, t in lines
        )
        i2c_status_ok = any("[I2C1]" in t and "ACKed at 0x40" in t for _, t in lines)
        ina_label = "INA226 armed (CONFIG/CAL written)"
        i2c_label = "I2C1 device ACK at 0x40"
    else:
        ina_status_ok = False
        i2c_status_ok = False
        ina_label = "INA226 state (unknown mode)"
        i2c_label = "I2C1 state (unknown mode)"

    # Heartbeat shape (mode-aware): "[<n>s] alive ..."  always starts with this
    tick_re = re.compile(r"\[(\d+)s\] alive")
    tick_pairs = [
        (ts, int(m.group(1)))
        for ts, t in after_banner
        for m in [tick_re.search(t)]
        if m
    ]

    # In present mode, also sanity-check that V/I/P fields are populated and
    # V is in a plausible Li-ion range.
    sample_re = re.compile(
        r"\[(\d+)s\] alive V=([\-\d.]+)mV I=([\-\d.]+)mA P=([\-\d.]+)mW"
    )
    samples = [
        (int(m.group(1)), float(m.group(2)) / 1000.0,
         float(m.group(3)) / 1000.0, float(m.group(4)) / 1000.0)
        for _, t in after_banner
        for m in [sample_re.search(t)]
        if m
    ]
    v_in_range = True
    if mode == "present":
        v_in_range = bool(samples) and all(0.5 <= s[1] <= 4.5 for s in samples)

    print("\n──────── verification ────────")
    print(f"  banner present              : {'OK' if banner_seen else 'FAIL'}")
    print(f"  clock/peripheral line       : {'OK' if sysclk_ok else 'FAIL'}")
    print(f"  INA226 mode (auto-detect)   : {mode}")
    print(f"  {ina_label:<27} : {'OK' if ina_status_ok else 'FAIL'}")
    print(f"  {i2c_label:<27} : {'OK' if i2c_status_ok else 'FAIL'}")
    if mode == "present":
        if samples:
            v_mean = sum(s[1] for s in samples) / len(samples)
            i_mean = sum(s[2] for s in samples) / len(samples)
            p_mean = sum(s[3] for s in samples) / len(samples)
            print(f"  V (mean over {len(samples):>3} samples) : {v_mean:.4f} V "
                  f"{'(in range 0.5-4.5 V)' if v_in_range else '(OUT OF RANGE!)'}")
            print(f"  I (mean over {len(samples):>3} samples) : {i_mean*1000:+.2f} mA")
            print(f"  P (mean over {len(samples):>3} samples) : {p_mean*1000:+.2f} mW")
        else:
            print(f"  V/I/P fields                : FAIL (no parseable samples)")
    print(f"  heartbeat lines captured    : {len(tick_pairs)}")

    if len(tick_pairs) >= 2:
        intervals = [tick_pairs[i + 1][0] - tick_pairs[i][0]
                     for i in range(len(tick_pairs) - 1)]
        avg = sum(intervals) / len(intervals)
        worst = max(abs(x - 1.0) for x in intervals)
        seq_ok = all(tick_pairs[i + 1][1] == tick_pairs[i][1] + 1
                     for i in range(len(tick_pairs) - 1))
        print(f"  heartbeat interval avg      : {avg*1000:.1f} ms (target 1000 ms)")
        print(f"  heartbeat interval worst    : ±{worst*1000:.1f} ms vs 1 s")
        print(f"  heartbeat counter monotonic : {'OK' if seq_ok else 'FAIL — RESET / SKIP'}")
        ok = (banner_seen and sysclk_ok and ina_status_ok and i2c_status_ok
              and seq_ok and worst < 0.05 and v_in_range
              and mode in ("present", "absent"))
    else:
        ok = False
        print("  not enough heartbeat lines — likely flash did not run / reset issue")

    print(f"\n[verify] overall: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
