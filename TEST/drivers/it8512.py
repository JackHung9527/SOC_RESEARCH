"""ITECH IT8512A+ programmable DC electronic load driver.

Range: 0–120 V, 0–30 A, 300 W. Modes: CC / CV / CW / CR.
"""
from __future__ import annotations

from .scpi_serial import ScpiSerial


class IT8512:
    MODES = ("CC", "CV", "CW", "CR")

    def __init__(self, scpi: ScpiSerial):
        self.s = scpi
        self.s.write("SYST:REM")

    @classmethod
    def open(cls, port: str, baud: int = 9600) -> "IT8512":
        return cls(ScpiSerial(port, baud))

    def close(self) -> None:
        # Always leave the load in a safe state on disconnect.
        try:
            self.input_off()
        finally:
            self.s.write("SYST:LOC")
            self.s.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def idn(self) -> str:
        return self.s.query("*IDN?")

    # --- mode + setpoints ---
    def set_mode(self, mode: str) -> None:
        m = mode.upper()
        if m not in self.MODES:
            raise ValueError(f"mode must be one of {self.MODES}, got {mode!r}")
        self.s.write(f"FUNC {m}")

    def set_cc(self, amps: float) -> None:
        """Set constant-current setpoint (load sinks `amps` regardless of V)."""
        self.s.write(f"CURR {amps:.4f}")

    def set_cv(self, volts: float) -> None:
        self.s.write(f"VOLT {volts:.4f}")

    def set_cr(self, ohms: float) -> None:
        self.s.write(f"RES {ohms:.4f}")

    def set_cw(self, watts: float) -> None:
        self.s.write(f"POW {watts:.4f}")

    # --- protection envelope ---
    def set_voltage_on_threshold(self, volts: float) -> None:
        """Load only starts sinking when terminal V exceeds this."""
        self.s.write(f"VOLT:ON {volts:.4f}")

    def set_voltage_off_threshold(self, volts: float) -> None:
        """Load auto-disables when terminal V falls below this."""
        self.s.write(f"VOLT:OFF {volts:.4f}")

    def set_current_protection(self, amps: float) -> None:
        self.s.write(f"CURR:PROT {amps:.4f}")

    # --- input control ---
    def input_on(self) -> None:
        self.s.write("INP ON")

    def input_off(self) -> None:
        self.s.write("INP OFF")

    def is_input_on(self) -> bool:
        return self.s.query("INP?").strip().startswith("1")

    # --- measurements ---
    def measure_voltage(self) -> float:
        return self.s.query_float("MEAS:VOLT?")

    def measure_current(self) -> float:
        return self.s.query_float("MEAS:CURR?")

    def measure_power(self) -> float:
        return self.s.query_float("MEAS:POW?")
