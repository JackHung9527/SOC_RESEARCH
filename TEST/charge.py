#!/usr/bin/env python3
"""CC-CV charge to full — run before any baseline / multi-rate test.

Procedure (per meeting_0416 slide 8):
  1. PSU CH1 set V_max=V_charge_cutoff, I_lim=I_charge_cc. Output ON via
     BenchInterlock (which verifies Load is OFF first).
  2. Cell pulls full current → CC stage. Voltage rises toward V_cutoff.
  3. When voltage clamps at V_cutoff, current tapers → CV stage.
  4. Stop when measured I drops below I_charge_term.
  5. Output OFF via BenchInterlock; mandatory dead-time before any
     subsequent discharge phase can run.

Safety layers active during the run:
  - PSU APPLY V is set to V_charge_cutoff (so if the comms hangs the PSU
    cannot drive past it).
  - SafetyGuard absolute envelope = chemistry V_abs_max / V_abs_min.
  - SafetyGuard soft envelope = profile cut-off ± 50 mV (debounced 2 samples).
  - BenchInterlock guarantees Load is verified OFF before PSU enables.

Usage:
  python3 TEST/charge.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from TEST.config import BAUD, PHASE2, PORT_LOAD, PORT_PSU, SAFETY, require_battery
from TEST.core.bench import BenchInterlock, BenchInterlockError
from TEST.core.logger import CsvLogger
from TEST.core.safety import SafetyAbort, SafetyGuard
from TEST.drivers.it6302 import IT6302
from TEST.drivers.it8512 import IT8512
from TEST.profiles import print_summary


SAMPLE_DT = SAFETY.sample_period_s
DATA_DIR = Path(__file__).resolve().parent / "data"


def main() -> int:
    battery = require_battery()
    print_summary(battery)

    print(f"[charge] target V_cv={battery.v_charge_cutoff:.3f} V "
          f"CC={battery.i_charge_cc:.3f} A "
          f"term={battery.i_charge_term:.3f} A")

    guard = SafetyGuard.from_profile(battery, i_hard_high=SAFETY.i_hard_high)
    logger = CsvLogger(DATA_DIR, tag="charge")
    print(f"[charge] log -> {logger.path}")

    with IT6302.open(PORT_PSU, BAUD) as psu, IT8512.open(PORT_LOAD, BAUD) as load:
        print(f"[charge] PSU: {psu.idn()}")
        print(f"[charge] LOAD: {load.idn()}")

        bench = BenchInterlock(psu=psu, load=load, deadtime_s=SAFETY.deadtime_s)
        try:
            # 1) Force both outputs OFF and confirm by readback.
            bench.assert_idle()

            # 2) Configure PSU: clamp V at the chemistry-safe charge cutoff.
            psu.select(1)
            psu.set_apply(battery.v_charge_cutoff, battery.i_charge_cc)

            # 3) Sanity: read OCV via PSU's measurement (pre-output-on).
            #    With output OFF the meter usually returns ~0; we just record
            #    the configuration write for the log.
            logger.log(0.0, "rest", 0.0, 0.0, soc_cc=0.0, note="pre-charge-config")

            # 4) Energise PSU through the interlock.
            bench.start_charge(ch=1)
            t0 = time.monotonic()

            while True:
                v = psu.measure_voltage()
                i = psu.measure_current()
                t = time.monotonic() - t0

                # Sign convention: SafetyGuard sees |I|; charging is "negative
                # discharge", so we still pass |I| to keep i_high a |I| limit.
                guard.check(v, i)

                logger.log(t, "charge", v, i, soc_cc=0.0, note="cc-cv")

                stage = "CC" if i >= battery.i_charge_cc * 0.95 else "CV"
                if int(t) % 5 == 0:
                    print(f"  t={t:6.1f}s  V={v:.4f}  I={i:.4f}  [{stage}]")

                # CV-stage termination: V near V_cutoff and I tapered.
                if v >= battery.v_charge_cutoff - 0.02 and i <= battery.i_charge_term:
                    logger.log(t, "charge", v, i, soc_cc=0.0, note="term")
                    print("[charge] termination reached")
                    break

                time.sleep(SAMPLE_DT)

        except KeyboardInterrupt:
            print("\n[charge] interrupted by user")
        except SafetyAbort as e:
            print(f"\n[charge] !!! SAFETY ABORT: {e}")
        except BenchInterlockError as e:
            print(f"\n[charge] !!! BENCH INTERLOCK: {e}")
        finally:
            try:
                bench.stop_charge()
            except Exception:
                bench.emergency_stop()
            logger.close()

    print(f"[charge] PSU off, file closed: {logger.path}")
    print(f"[charge] dead-time {SAFETY.deadtime_s:.0f} s — wait before connecting load.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
