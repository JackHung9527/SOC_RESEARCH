#!/usr/bin/env python3
"""Slow-paced, narrated dry run of both instruments — no battery connected.

Walks through the same sequence the phase scripts use, but with visible
pauses and explicit "what you should see on the panel" prompts so the
operator can flag any wrong step.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from TEST.config import BAUD, PORT_LOAD, PORT_PSU
from TEST.drivers.it6302 import IT6302
from TEST.drivers.it8512 import IT8512


PAUSE = 2.5   # seconds between visible state changes


def step(n: int, title: str) -> None:
    print(f"\n──────── STEP {n}: {title} ────────")


def watch(msg: str) -> None:
    print(f"  >>> 面板應顯示: {msg}")


def main() -> int:
    # ─────────────────────────────────────────────
    step(1, "開啟兩台儀器並讀 *IDN?")
    print("  指令: open serial /dev/ttyACM0 (Load) + /dev/ttyACM1 (PSU)")
    psu = IT6302.open(PORT_PSU, BAUD)
    load = IT8512.open(PORT_LOAD, BAUD)
    time.sleep(0.5)
    print(f"  PSU  IDN : {psu.idn()}")
    print(f"  LOAD IDN : {load.idn()}")
    watch("兩台都進入 Rmt 燈亮（遠端模式）")
    time.sleep(PAUSE)

    # ─────────────────────────────────────────────
    step(2, "PSU 選 CH1, 設 3.30 V / 1.000 A, 不開輸出")
    print("  指令: INST:NSEL 1 ; VOLT 3.30 ; CURR 1.000")
    psu.select(1)
    psu.set_voltage(3.30)
    psu.set_current(1.000)
    time.sleep(0.5)
    print(f"  讀回: VOLT? = {psu.s.query('VOLT?')} V, CURR? = {psu.s.query('CURR?')} A")
    watch("CH1 顯示 3.30V/1.000A 的 SET 值, 但 OUT 燈未亮")
    time.sleep(PAUSE)

    # ─────────────────────────────────────────────
    step(3, "PSU 開 CH1 輸出（無負載 → 電壓應穩定 3.30 V, 電流 0 A）")
    print("  指令: CHAN:OUTP ON")
    psu.channel_output(True)
    time.sleep(1.0)
    v = psu.measure_voltage()
    i = psu.measure_current()
    print(f"  量測: V={v:.4f} V, I={i:.4f} A")
    watch(f"CH1 OUT 燈亮, 顯示約 {v:.2f} V / 0.000 A (CV 模式)")
    time.sleep(PAUSE)

    # ─────────────────────────────────────────────
    step(4, "PSU 改設定 5.00 V / 2.000 A（線上即時改參數）")
    print("  指令: VOLT 5.00 ; CURR 2.000")
    psu.set_voltage(5.00)
    psu.set_current(2.000)
    time.sleep(1.0)
    v = psu.measure_voltage()
    print(f"  量測: V={v:.4f} V")
    watch("CH1 顯示電壓跳到約 5.00 V, 電流上限改 2.000 A")
    time.sleep(PAUSE)

    # ─────────────────────────────────────────────
    step(5, "PSU 關 CH1 輸出")
    print("  指令: CHAN:OUTP OFF")
    psu.channel_output(False)
    time.sleep(1.0)
    print(f"  CH1 OUTP? = {psu.s.query('CHAN:OUTP?')}")
    watch("CH1 OUT 燈熄, 顯示 0.000 V / 0.000 A")
    time.sleep(PAUSE)

    # ─────────────────────────────────────────────
    step(6, "Load 設 CC 模式 0.300 A, 不開輸入")
    print("  指令: FUNC CC ; CURR 0.300")
    load.set_mode("CC")
    load.set_cc(0.300)
    time.sleep(0.5)
    print(f"  FUNC? = {load.s.query('FUNC?')}, CURR? = {load.s.query('CURR?')} A")
    watch("Load 上半屏顯示 CC 模式, SET 值 0.300A, 輸入未開")
    time.sleep(PAUSE)

    # ─────────────────────────────────────────────
    step(7, "Load 開輸入（沒接電池 → V/I 都是 0）")
    print("  指令: INP ON")
    load.input_on()
    time.sleep(1.0)
    v = load.measure_voltage()
    i = load.measure_current()
    print(f"  量測: V={v:.4f} V, I={i:.4f} A")
    watch("Load INPUT 燈亮, V≈0, I≈0 (因為沒接電源)")
    time.sleep(PAUSE)

    # ─────────────────────────────────────────────
    step(8, "Load 切換 CC 設定 1.234 A（驗證即時改 setpoint）")
    print("  指令: CURR 1.234")
    load.set_cc(1.234)
    time.sleep(1.0)
    print(f"  CURR? = {load.s.query('CURR?')} A")
    watch("Load SET 值跳到 1.234A")
    time.sleep(PAUSE)

    # ─────────────────────────────────────────────
    step(9, "Load 關輸入")
    print("  指令: INP OFF")
    load.input_off()
    time.sleep(0.5)
    print(f"  INP? = {load.s.query('INP?')}")
    watch("Load INPUT 燈熄")
    time.sleep(PAUSE)

    # ─────────────────────────────────────────────
    step(10, "收尾: 兩台離開遠端 → 本地控制")
    print("  指令: SYST:LOC (兩台都送)")
    psu.close()
    load.close()
    print("\n[dry_run] 完成。兩台都已關輸出/輸入並回到本地。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
