"""ITECH IT6302 three-channel DC power supply driver.

CH1, CH2: 30 V / 3 A. CH3: 5 V / 3 A.
Channel select is required before any per-channel SOURce/MEASure command.
"""
from __future__ import annotations

from .scpi_serial import ScpiSerial


class IT6302:
    def __init__(self, scpi: ScpiSerial):
        self.s = scpi
        self.s.write("SYST:REM")

    @classmethod
    def open(cls, port: str, baud: int = 9600) -> "IT6302":
        return cls(ScpiSerial(port, baud))

    def close(self) -> None:
        self.s.write("SYST:LOC")
        self.s.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def idn(self) -> str:
        return self.s.query("*IDN?")

    # --- channel selection ---
    def select(self, ch: int) -> None:
        if ch not in (1, 2, 3):
            raise ValueError(f"channel must be 1..3, got {ch}")
        self.s.write(f"INST:NSEL {ch}")

    # --- setpoints (act on currently selected channel) ---
    def set_voltage(self, volts: float) -> None:
        self.s.write(f"VOLT {volts:.4f}")

    def set_current(self, amps: float) -> None:
        self.s.write(f"CURR {amps:.4f}")

    def set_apply(self, volts: float, amps: float) -> None:
        """Convenience: set V and I limit in one shot via APPLy."""
        self.s.write(f"APPL {volts:.4f},{amps:.4f}")

    def channel_max_current(self) -> float:
        return self.s.query_float("CURR? MAX")

    # --- output control ---
    def channel_output(self, on: bool) -> None:
        """Enable/disable only the currently selected channel."""
        self.s.write(f"CHAN:OUTP {'ON' if on else 'OFF'}")

    def all_outputs(self, on: bool) -> None:
        """Master switch — drives all three channels."""
        self.s.write(f"OUTP {'ON' if on else 'OFF'}")

    # --- measurements (currently selected channel) ---
    def measure_voltage(self) -> float:
        return self.s.query_float("MEAS:VOLT?")

    def measure_current(self) -> float:
        return self.s.query_float("MEAS:CURR?")

    def measure_power(self) -> float:
        return self.s.query_float("MEAS:POW?")
