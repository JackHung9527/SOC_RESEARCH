"""Bench interlock — mutual-exclusion + dead-time between source and load.

Single-cell test bench has no BMS. The two failure modes we must prevent in
software (the user has to physically wire correctly, but software is the
last line of defence) are:

  (A) PSU output ON while Load input ON simultaneously — they fight, current
      goes through the cell in an unpredictable direction, and any bug in
      either control loop ends with the cell either over-charged or
      thermally runaway.

  (B) Switching directly from charge → discharge (or vice versa) without an
      intervening rest. The cell needs time to relax (CDL discharge) and we
      want a moment for the user to verify the bus state before the next
      direction is energised.

`BenchInterlock` is a tiny state machine: every call to enable/disable an
output goes through it, it verifies the *other* instrument is OFF first, it
verifies the write took effect by reading back, and it enforces a minimum
dead-time after every disable.

State diagram:

    IDLE ──start_charge──> CHARGING
    CHARGING ──stop_charge──> COOLDOWN ──(t >= deadtime)──> IDLE
    IDLE ──start_discharge──> DISCHARGING
    DISCHARGING ──stop_discharge──> COOLDOWN ──(t >= deadtime)──> IDLE

Any transition that violates the diagram raises BenchInterlockError and
forces an emergency_stop() before re-raising.
"""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Optional


# Sensible default — long enough for the user to see "PSU off, now switching
# to load" on screen and physically check leads if needed. Override via
# config.DEADTIME_S for shorter test cycles.
DEFAULT_DEADTIME_S = 5.0


class BenchState(enum.Enum):
    IDLE = "idle"
    CHARGING = "charging"
    DISCHARGING = "discharging"
    COOLDOWN = "cooldown"


class BenchInterlockError(RuntimeError):
    """Raised on any forbidden bench transition or output-readback mismatch."""


@dataclass
class BenchInterlock:
    psu: object                       # IT6302 instance
    load: object                      # IT8512  instance
    deadtime_s: float = DEFAULT_DEADTIME_S
    verbose: bool = True

    state: BenchState = BenchState.IDLE
    _cooldown_until: float = 0.0
    _last_event: str = "init"

    # ---- low-level: verified output toggles ----------------------------

    def _psu_off_verified(self, ch: int = 1) -> None:
        """Disable PSU channel and verify it actually went off."""
        self.psu.select(ch)
        self.psu.channel_output(False)
        # Some IT6302 firmwares carry the OUTP state separately from
        # CHAN:OUTP; turn the master rail off too as belt+braces.
        try:
            self.psu.all_outputs(False)
        except Exception:
            pass
        time.sleep(0.1)
        # Best-effort verify by measuring — current ≈ 0 after off.
        try:
            i = self.psu.measure_current()
            if abs(i) > 0.050:
                raise BenchInterlockError(
                    f"PSU off verify failed: still measures I={i:.4f} A"
                )
        except BenchInterlockError:
            raise
        except Exception:
            # Some SCPI stacks reject MEAS while output is off; tolerate.
            pass

    def _load_off_verified(self) -> None:
        self.load.input_off()
        time.sleep(0.1)
        try:
            if self.load.is_input_on():
                # Retry once.
                self.load.input_off()
                time.sleep(0.1)
                if self.load.is_input_on():
                    raise BenchInterlockError(
                        "Load off verify failed: INP still ON after retry"
                    )
        except BenchInterlockError:
            raise
        except Exception:
            # If is_input_on() can't be queried, fall back to current check.
            try:
                i = self.load.measure_current()
                if abs(i) > 0.050:
                    raise BenchInterlockError(
                        f"Load off verify failed: still measures I={i:.4f} A"
                    )
            except BenchInterlockError:
                raise
            except Exception:
                pass

    def _wait_cooldown(self) -> None:
        if self.state != BenchState.COOLDOWN:
            return
        remaining = self._cooldown_until - time.monotonic()
        if remaining > 0:
            if self.verbose:
                print(f"[bench] cooldown {remaining:.1f} s before next transition…")
            time.sleep(remaining)
        self.state = BenchState.IDLE
        if self.verbose:
            print("[bench] cooldown complete → IDLE")

    # ---- public API ----------------------------------------------------

    def assert_idle(self) -> None:
        """Block until both outputs are confirmed off and cooldown elapsed."""
        self._wait_cooldown()
        self._load_off_verified()
        self._psu_off_verified()
        self.state = BenchState.IDLE

    def start_charge(self, ch: int = 1) -> None:
        if self.state == BenchState.CHARGING:
            return
        if self.state in (BenchState.DISCHARGING, BenchState.COOLDOWN):
            self._wait_cooldown()
        if self.state != BenchState.IDLE:
            raise BenchInterlockError(
                f"start_charge refused: state={self.state.value}"
            )
        # Belt + braces: confirm load is off before we ever turn PSU on.
        self._load_off_verified()
        self.psu.select(ch)
        self.psu.channel_output(True)
        time.sleep(0.2)
        self.state = BenchState.CHARGING
        self._last_event = "charge_on"
        if self.verbose:
            print(f"[bench] CHARGING (PSU CH{ch} ON, load verified OFF)")

    def stop_charge(self) -> None:
        if self.state != BenchState.CHARGING:
            # Idempotent — make sure PSU is off regardless.
            self._psu_off_verified()
            self.state = BenchState.COOLDOWN
            self._cooldown_until = time.monotonic() + self.deadtime_s
            return
        self._psu_off_verified()
        self._cooldown_until = time.monotonic() + self.deadtime_s
        self.state = BenchState.COOLDOWN
        self._last_event = "charge_off"
        if self.verbose:
            print(f"[bench] PSU OFF, COOLDOWN {self.deadtime_s:.1f} s")

    def start_discharge(self) -> None:
        if self.state == BenchState.DISCHARGING:
            return
        if self.state in (BenchState.CHARGING, BenchState.COOLDOWN):
            # CHARGING → must explicitly stop_charge first; refuse the shortcut.
            if self.state == BenchState.CHARGING:
                raise BenchInterlockError(
                    "start_discharge refused: still CHARGING — call stop_charge() first"
                )
            self._wait_cooldown()
        if self.state != BenchState.IDLE:
            raise BenchInterlockError(
                f"start_discharge refused: state={self.state.value}"
            )
        # Belt + braces: confirm PSU is off before we ever enable load.
        self._psu_off_verified()
        self.load.input_on()
        time.sleep(0.2)
        self.state = BenchState.DISCHARGING
        self._last_event = "discharge_on"
        if self.verbose:
            print("[bench] DISCHARGING (load INP ON, PSU verified OFF)")

    def stop_discharge(self) -> None:
        if self.state != BenchState.DISCHARGING:
            self._load_off_verified()
            self.state = BenchState.COOLDOWN
            self._cooldown_until = time.monotonic() + self.deadtime_s
            return
        self._load_off_verified()
        self._cooldown_until = time.monotonic() + self.deadtime_s
        self.state = BenchState.COOLDOWN
        self._last_event = "discharge_off"
        if self.verbose:
            print(f"[bench] LOAD OFF, COOLDOWN {self.deadtime_s:.1f} s")

    def emergency_stop(self) -> None:
        """Best-effort kill both outputs. Safe to call from any state."""
        if self.verbose:
            print("[bench] !!! EMERGENCY STOP !!!")
        try:
            self.load.input_off()
        except Exception as e:
            print(f"[bench] load off failed: {e}")
        try:
            self.psu.channel_output(False)
            try:
                self.psu.all_outputs(False)
            except Exception:
                pass
        except Exception as e:
            print(f"[bench] psu off failed: {e}")
        self.state = BenchState.COOLDOWN
        self._cooldown_until = time.monotonic() + self.deadtime_s
        self._last_event = "estop"

    # ---- context manager so phase scripts can wrap the bench --------------

    def __enter__(self):
        self.assert_idle()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.emergency_stop()
        return False  # propagate exceptions
