#!/usr/bin/env python3
"""CC-CV charge to full — run before any baseline / multi-rate test.

Procedure (per meeting_0416 slide 8):
  1. PSU CH1 set V_max=4.20 V, I_lim=1.075 A (0.5C). Output ON.
  2. Cell pulls full current → CC stage. Voltage rises toward 4.20 V.
  3. When voltage clamps at 4.20 V, current tapers → CV stage.
  4. Stop when measured I drops below 0.05 A (≈ C/43 termination).
  5. Output OFF, log final state.

Usage:
  python3 TEST/charge.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from TEST.config import BAUD, BATTERY, PORT_LOAD, PORT_PSU, SAFETY
from TEST.core.logger import CsvLogger
from TEST.core.safety import SafetyAbort, SafetyGuard
from TEST.drivers.it6302 import IT6302
from TEST.drivers.it8512 import IT8512


SAMPLE_DT = SAFETY.sample_period_s
DATA_DIR = Path(__file__).resolve().parent / "data"


def main() -> int:
    print(f"[charge] target {BATTERY.v_charge_cv:.2f} V CC={BATTERY.i_charge_cc:.3f} A "
          f"term={BATTERY.i_charge_term:.3f} A")

    # Make sure load is OFF before we energise the rails.
    with IT8512.open(PORT_LOAD, BAUD) as load:
        load.input_off()

    guard = SafetyGuard(
        v_high=SAFETY.v_hard_high,
        v_low=SAFETY.v_hard_low,
        i_high=SAFETY.i_hard_high,
    )
    logger = CsvLogger(DATA_DIR, tag="charge")
    print(f"[charge] log -> {logger.path}")

    with IT6302.open(PORT_PSU, BAUD) as psu:
        print(f"[charge] {psu.idn()}")
        psu.select(1)
        psu.set_apply(BATTERY.v_charge_cv, BATTERY.i_charge_cc)
        psu.channel_output(True)
        time.sleep(0.5)

        t0 = time.monotonic()
        try:
            while True:
                v = psu.measure_voltage()
                i = psu.measure_current()
                t = time.monotonic() - t0

                guard.check(v, -i)   # charging current is "negative" by our sign convention
                # Naive SoC during charge: 1 - remaining capacity (rough; we don't know start state)
                logger.log(t, "charge", v, i, soc_cc=0.0, note="cc-cv")

                stage = "CC" if i >= BATTERY.i_charge_cc * 0.95 else "CV"
                if int(t) % 5 == 0:
                    print(f"  t={t:6.1f}s  V={v:.4f}  I={i:.4f}  [{stage}]")

                # CV-stage termination: current has tapered to <= I_term and we're near V_max.
                if v >= BATTERY.v_charge_cv - 0.02 and i <= BATTERY.i_charge_term:
                    print("[charge] termination reached")
                    break

                time.sleep(SAMPLE_DT)
        except KeyboardInterrupt:
            print("\n[charge] interrupted by user")
        except SafetyAbort as e:
            print(f"\n[charge] SAFETY ABORT: {e}")
        finally:
            psu.channel_output(False)
            logger.close()

    print("[charge] PSU off, file closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
