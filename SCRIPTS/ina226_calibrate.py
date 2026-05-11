#!/usr/bin/env python3
"""Multi-point calibration of INA226 current readout against Load and PSU.

Procedure:
  Phase A (discharge): Load CC at each I_target. Compare Load.I (truth) vs
    INA226 I read from MCU /dev/ttyACM2 heartbeat lines.
  Phase B (charge):    PSU APPLY V=4.20, I=I_target. Compare PSU.I vs INA226.

Two separate piecewise-linear LUTs are saved (discharge / charge) — they
are NOT averaged together because the INA226 may have asymmetric offset
when current flows the other direction across the shunt.

Output: TEST/data/calibration_ina226.json
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
from pathlib import Path

import serial

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from TEST.config import BAUD, PORT_LOAD, PORT_PSU
from TEST.drivers.it6302 import IT6302
from TEST.drivers.it8512 import IT8512


VCP = "/dev/ttyACM2"
TARGETS_A = [0.000, 0.050, 0.100, 0.500, 1.000, 1.500, 2.000]
SETTLE_S = 3.0          # let the loop reach steady state before sampling
SAMPLE_S = 5.0          # window during which we collect samples
DEAD_TIME_S = 10.0      # between Phase A and Phase B
V_CHARGE_COMPLIANCE = 4.20   # PSU V clamp (cell V_cutoff)
V_DISCHARGE_FLOOR = 2.50     # Load auto-off threshold

OUTPUT = Path(__file__).resolve().parent.parent / "TEST" / "data" / "calibration_ina226.json"


HEARTBEAT_RX = re.compile(
    r"\[(\d+)s\] alive V=([\-\d.]+)mV I=([\-\d.]+)mA P=([\-\d.]+)mW"
)


class McuReader:
    def __init__(self, port: str = VCP, baud: int = 115200):
        self._ser = serial.Serial(port, baud, timeout=0.5)
        self._ser.reset_input_buffer()
        self._lines: list[tuple[float, str]] = []
        self._stop = threading.Event()
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()

    def _run(self):
        while not self._stop.is_set():
            ln = self._ser.readline()
            if ln:
                self._lines.append((time.monotonic(),
                                    ln.decode(errors="replace").rstrip()))

    def samples_between(self, t_start: float, t_end: float):
        """Return [(v_V, i_A)] parsed from heartbeats within [t_start, t_end]."""
        out = []
        for ts, line in self._lines:
            if not (t_start <= ts <= t_end):
                continue
            m = HEARTBEAT_RX.search(line)
            if m:
                v = float(m.group(2)) / 1000.0
                i = float(m.group(3)) / 1000.0
                out.append((v, i))
        return out

    def close(self):
        self._stop.set()
        self._th.join(timeout=1)
        self._ser.close()


def collect_point(label: str, target_A: float, ref_fn, mcu: McuReader):
    """Wait for settle, then sample for SAMPLE_S. Return dict."""
    print(f"  [{label} {target_A:5.3f} A] settle...", end=" ", flush=True)
    time.sleep(SETTLE_S)
    t0 = time.monotonic()
    ref_samples = []
    while time.monotonic() - t0 < SAMPLE_S:
        ref_samples.append(ref_fn())
        time.sleep(0.4)
    t1 = time.monotonic()
    mcu_samples = mcu.samples_between(t0, t1)

    if not ref_samples:
        print("FAIL: no ref samples")
        return None
    if not mcu_samples:
        print("FAIL: no MCU samples (heartbeat not seen)")
        return None

    ref_v = sum(s[0] for s in ref_samples) / len(ref_samples)
    ref_i = sum(s[1] for s in ref_samples) / len(ref_samples)
    mcu_v = sum(s[0] for s in mcu_samples) / len(mcu_samples)
    mcu_i = sum(s[1] for s in mcu_samples) / len(mcu_samples)

    print(f"ref V={ref_v:.4f} I={ref_i*1000:6.1f} mA   "
          f"MCU V={mcu_v:.4f} I={mcu_i*1000:6.1f} mA   "
          f"(n_ref={len(ref_samples)} n_mcu={len(mcu_samples)})")

    return {
        "target_A": target_A,
        "ref_V": ref_v,
        "ref_A": ref_i,
        "mcu_V": mcu_v,
        "mcu_A": mcu_i,
        "n_ref": len(ref_samples),
        "n_mcu": len(mcu_samples),
    }


def main() -> int:
    print("=" * 60)
    print("INA226 multi-point calibration")
    print(f"  targets: {TARGETS_A} A")
    print(f"  per point: {SETTLE_S:.1f} s settle + {SAMPLE_S:.1f} s sample")
    print("=" * 60)

    # Bring everything to known idle.
    with IT6302.open(PORT_PSU, BAUD) as psu:
        psu.all_outputs(False)
    with IT8512.open(PORT_LOAD, BAUD) as load:
        load.input_off()
    print("✓ both instruments idle")

    mcu = McuReader()
    time.sleep(1.0)
    if not mcu.samples_between(0, time.monotonic() + 100):
        print("WARN: no MCU heartbeat seen yet — make sure MCU is powered and INA226 wired.")

    discharge_points = []
    charge_points = []

    try:
        # ── Phase A: discharge calibration ──
        print()
        print("── Phase A: discharge (Load active, PSU OFF) ──")
        with IT8512.open(PORT_LOAD, BAUD) as load:
            load.set_mode("CC")
            load.set_voltage_off_threshold(V_DISCHARGE_FLOOR)

            for tgt in TARGETS_A:
                if tgt <= 0.0001:
                    # 0 A point: keep Load OFF, just measure baseline
                    load.input_off()
                    pt = collect_point(
                        "dis", tgt,
                        ref_fn=lambda l=load: (l.measure_voltage(), 0.0),
                        mcu=mcu,
                    )
                else:
                    load.set_cc(tgt)
                    # Verify setpoint stuck before INP ON
                    rb = float(load.s.query("CURR?").strip())
                    if abs(rb - tgt) > 0.05:
                        print(f"  setpoint readback {rb} != target {tgt}, retry")
                        load.set_cc(tgt)
                        rb = float(load.s.query("CURR?").strip())
                    load.input_on()
                    pt = collect_point(
                        "dis", tgt,
                        ref_fn=lambda l=load: (l.measure_voltage(),
                                               l.measure_current()),
                        mcu=mcu,
                    )
                    load.input_off()
                    time.sleep(0.8)   # let bus relax before next point

                if pt:
                    discharge_points.append(pt)

        # ── Rest between phases ──
        print(f"\n── Rest {DEAD_TIME_S:.0f} s before charge phase ──")
        time.sleep(DEAD_TIME_S)

        # ── Phase B: charge calibration ──
        print()
        print("── Phase B: charge (PSU CH1 active, Load OFF) ──")
        with IT6302.open(PORT_PSU, BAUD) as psu:
            psu.select(1)
            psu.set_voltage(V_CHARGE_COMPLIANCE)
            psu.set_current(0.0)

            for tgt in TARGETS_A:
                if tgt <= 0.0001:
                    psu.channel_output(False)
                    pt = collect_point(
                        "chg", tgt,
                        ref_fn=lambda p=psu: (p.measure_voltage(), 0.0),
                        mcu=mcu,
                    )
                else:
                    # APPLy command on IT6302 is unreliable for sequential current
                    # changes; use V/I separate writes and tight readback tolerance.
                    psu.set_voltage(V_CHARGE_COMPLIANCE)
                    psu.set_current(tgt)
                    time.sleep(0.3)
                    rb_i = float(psu.s.query("CURR?").strip())
                    tol = max(0.005, 0.05 * tgt)   # 5% or 5 mA, whichever larger
                    if abs(rb_i - tgt) > tol:
                        print(f"  setpoint readback {rb_i} != target {tgt}, retry")
                        psu.set_current(tgt)
                        time.sleep(0.3)
                        rb_i = float(psu.s.query("CURR?").strip())
                        if abs(rb_i - tgt) > tol:
                            print(f"  STILL OFF after retry ({rb_i} A) — SKIPPING")
                            continue
                    psu.channel_output(True)
                    pt = collect_point(
                        "chg", tgt,
                        ref_fn=lambda p=psu: (p.measure_voltage(),
                                              p.measure_current()),
                        mcu=mcu,
                    )
                    psu.channel_output(False)
                    time.sleep(0.8)

                if pt:
                    charge_points.append(pt)

    finally:
        # Belt-and-suspenders: force everything off.
        with IT6302.open(PORT_PSU, BAUD) as psu:
            psu.all_outputs(False)
        with IT8512.open(PORT_LOAD, BAUD) as load:
            load.input_off()
        mcu.close()

    # ── Save LUT ──
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "ina226-cal/v1",
        "shunt_ohm_assumed": 0.010,
        "current_lsb_a_assumed": 0.0001525879,
        "interpolation": "piecewise-linear",
        "discharge": discharge_points,
        "charge": charge_points,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    # ── Summary table ──
    print()
    print("=" * 60)
    print(f"Saved → {OUTPUT}")
    print("=" * 60)
    for direction, pts in (("DISCHARGE", discharge_points),
                           ("CHARGE", charge_points)):
        print(f"\n{direction}:")
        print(f"  {'target':>8}  {'ref_A':>10}  {'mcu_A':>10}  "
              f"{'delta':>10}  {'ratio':>8}")
        for p in pts:
            ref = p["ref_A"]
            mcu_ = p["mcu_A"]
            ratio = (ref / mcu_) if abs(mcu_) > 1e-6 else float("inf")
            print(f"  {p['target_A']:8.3f}  {ref*1000:9.2f}mA  "
                  f"{mcu_*1000:9.2f}mA  {(mcu_-ref)*1000:+8.2f}mA  "
                  f"{ratio:8.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
