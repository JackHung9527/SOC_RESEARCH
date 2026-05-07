"""Battery profile catalogue.

We test single cells (no BMS, no balancing). Every chemistry has a hard
chemistry-imposed envelope (e.g. Li-ion NMC: 4.20 V max, 2.50 V floor) — the
profile here records *user setpoints* (charge cut-off, discharge cut-off,
rated capacity) and the *chemistry envelope* the user setpoints must stay
inside. Validation in `BatteryProfile.validate()` rejects any profile that
would let the test bench drive the cell past the chemistry envelope.

Usage from a phase script:

    from TEST.profiles import load_active_profile
    BATTERY = load_active_profile()        # raises if no profile selected

To pick / change the active profile:

    python3 TEST/select_battery.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


PROFILE_FILE = Path(__file__).resolve().parent / "data" / "active_profile.json"


@dataclass(frozen=True)
class ChemistryEnvelope:
    """Chemistry-level absolute limits — never exceed regardless of setpoint."""
    name: str
    v_abs_max: float       # e.g. Li-ion NMC: 4.25 V (datasheet abs max)
    v_abs_min: float       # e.g. Li-ion NMC: 2.50 V (below = irreversible)
    v_charge_max: float    # standard charge ceiling (4.20 for NMC, 3.65 for LFP)
    v_discharge_min: float # standard discharge floor


CHEMISTRIES: dict[str, ChemistryEnvelope] = {
    "li-ion-nmc": ChemistryEnvelope(
        name="Li-ion NMC/NCA (typical 18650/21700)",
        v_abs_max=4.25, v_abs_min=2.50,
        v_charge_max=4.20, v_discharge_min=2.75,
    ),
    "lfp": ChemistryEnvelope(
        name="LiFePO4 (single cell, e.g. 26650)",
        v_abs_max=3.70, v_abs_min=2.00,
        v_charge_max=3.65, v_discharge_min=2.50,
    ),
    "li-ion-lto": ChemistryEnvelope(
        name="Li-titanate (LTO)",
        v_abs_max=2.85, v_abs_min=1.50,
        v_charge_max=2.80, v_discharge_min=1.80,
    ),
}


@dataclass(frozen=True)
class BatteryProfile:
    """Per-DUT setpoints. All bench scripts must read from here."""
    name: str
    chemistry: str                # key into CHEMISTRIES
    q_rated_mAh: float

    v_charge_cv: float            # CV target during charge
    v_charge_cutoff: float        # alias of v_charge_cv (kept explicit per user spec)
    i_charge_cc: float            # CC current during charge
    i_charge_term: float          # CV-stage termination current

    v_discharge_cutoff: float     # cell hard floor used by phase scripts
    i_discharge_cc: float         # baseline CC discharge current

    v_nominal: float = 3.7

    # Convenience aliases (legacy code expects v_max/v_min)
    @property
    def v_max(self) -> float:
        return self.v_charge_cutoff

    @property
    def v_min(self) -> float:
        return self.v_discharge_cutoff

    def validate(self) -> list[str]:
        """Return list of error strings. Empty list = OK."""
        errs: list[str] = []
        chem = CHEMISTRIES.get(self.chemistry)
        if chem is None:
            errs.append(f"unknown chemistry {self.chemistry!r}; "
                        f"known: {sorted(CHEMISTRIES)}")
            return errs

        if self.v_charge_cutoff > chem.v_abs_max:
            errs.append(
                f"v_charge_cutoff={self.v_charge_cutoff} V exceeds chemistry "
                f"absolute max {chem.v_abs_max} V ({chem.name})"
            )
        if self.v_charge_cutoff > chem.v_charge_max + 0.01:
            errs.append(
                f"v_charge_cutoff={self.v_charge_cutoff} V exceeds standard "
                f"charge ceiling {chem.v_charge_max} V; double-check this is "
                "intentional"
            )
        if self.v_discharge_cutoff < chem.v_abs_min:
            errs.append(
                f"v_discharge_cutoff={self.v_discharge_cutoff} V below "
                f"chemistry absolute floor {chem.v_abs_min} V"
            )
        if self.v_discharge_cutoff >= self.v_charge_cutoff:
            errs.append("v_discharge_cutoff must be lower than v_charge_cutoff")

        if self.q_rated_mAh <= 0:
            errs.append("q_rated_mAh must be > 0")
        if self.i_charge_cc <= 0:
            errs.append("i_charge_cc must be > 0")
        if self.i_discharge_cc <= 0:
            errs.append("i_discharge_cc must be > 0")
        if self.i_charge_term <= 0 or self.i_charge_term >= self.i_charge_cc:
            errs.append("i_charge_term must be > 0 and < i_charge_cc")

        # 1C sanity (warn-level, but make it a hard fail to avoid abuse on
        # cells you are not sure can take >1C).
        c1_A = self.q_rated_mAh / 1000.0
        if self.i_charge_cc > 1.5 * c1_A:
            errs.append(
                f"i_charge_cc={self.i_charge_cc} A is >1.5C ({c1_A:.3f} A); "
                "many cells cannot accept this — confirm datasheet"
            )
        if self.i_discharge_cc > 3.0 * c1_A:
            errs.append(
                f"i_discharge_cc={self.i_discharge_cc} A is >3C ({c1_A:.3f} A); "
                "confirm datasheet"
            )
        return errs

    def chem_envelope(self) -> ChemistryEnvelope:
        return CHEMISTRIES[self.chemistry]


# --- Built-in catalogue. Keep only conservative, well-known cells here. ---
PROFILES: dict[str, BatteryProfile] = {
    "18650-NMC-2150": BatteryProfile(
        name="18650 Li-ion NMC, 2150 mAh (Samsung INR18650-22P-class)",
        chemistry="li-ion-nmc",
        q_rated_mAh=2150.0,
        v_charge_cv=4.20, v_charge_cutoff=4.20,
        i_charge_cc=1.075,           # 0.5 C
        i_charge_term=0.050,
        v_discharge_cutoff=2.75,
        i_discharge_cc=1.075,        # 0.5 C
    ),
    "18650-NMC-3500": BatteryProfile(
        name="18650 Li-ion NMC, 3500 mAh (Panasonic NCR18650GA-class)",
        chemistry="li-ion-nmc",
        q_rated_mAh=3500.0,
        v_charge_cv=4.20, v_charge_cutoff=4.20,
        i_charge_cc=1.750,
        i_charge_term=0.070,
        v_discharge_cutoff=2.75,
        i_discharge_cc=1.750,
    ),
    "26650-LFP-3000": BatteryProfile(
        name="26650 LiFePO4, 3000 mAh (A123 / K2 single cell)",
        chemistry="lfp",
        q_rated_mAh=3000.0,
        v_charge_cv=3.65, v_charge_cutoff=3.65,
        i_charge_cc=1.500,           # 0.5 C
        i_charge_term=0.060,
        v_discharge_cutoff=2.50,
        i_discharge_cc=1.500,
    ),
    "14500-NMC-800": BatteryProfile(
        name="14500 Li-ion NMC, 800 mAh (AA-form factor)",
        chemistry="li-ion-nmc",
        q_rated_mAh=800.0,
        v_charge_cv=4.20, v_charge_cutoff=4.20,
        i_charge_cc=0.400,
        i_charge_term=0.020,
        v_discharge_cutoff=2.75,
        i_discharge_cc=0.400,
    ),
}


def list_profiles() -> list[str]:
    return list(PROFILES.keys())


def get_profile(key: str) -> BatteryProfile:
    if key not in PROFILES:
        raise KeyError(f"unknown profile {key!r}; "
                       f"known: {list_profiles()}")
    return PROFILES[key]


# --- Active profile persistence (data/active_profile.json) ---

def save_active_profile(p: BatteryProfile) -> None:
    errs = p.validate()
    if errs:
        raise ValueError("profile validation failed:\n  - " + "\n  - ".join(errs))
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_FILE.write_text(json.dumps(asdict(p), indent=2, ensure_ascii=False))


def load_active_profile() -> BatteryProfile:
    if not PROFILE_FILE.exists():
        raise FileNotFoundError(
            f"no active battery profile selected. Run:\n"
            f"  python3 TEST/select_battery.py"
        )
    raw = json.loads(PROFILE_FILE.read_text())
    p = BatteryProfile(**raw)
    errs = p.validate()
    if errs:
        raise ValueError(
            "active profile failed validation (file may be hand-edited):\n  - "
            + "\n  - ".join(errs)
        )
    return p


def try_load_active_profile() -> Optional[BatteryProfile]:
    try:
        return load_active_profile()
    except FileNotFoundError:
        return None


# --- Interactive picker (used by select_battery.py) ---

def _prompt_float(label: str, default: float, min_v: float, max_v: float) -> float:
    while True:
        s = input(f"  {label} [{default}]: ").strip()
        if not s:
            return default
        try:
            v = float(s)
        except ValueError:
            print(f"    not a number: {s!r}")
            continue
        if not (min_v <= v <= max_v):
            print(f"    out of range [{min_v}, {max_v}]")
            continue
        return v


def interactive_pick() -> BatteryProfile:
    print("=" * 60)
    print("Battery profile selection")
    print("=" * 60)
    keys = list_profiles()
    for i, k in enumerate(keys, 1):
        p = PROFILES[k]
        print(f"  [{i}] {k}")
        print(f"      {p.name}")
        print(f"      Q={p.q_rated_mAh:.0f} mAh  charge≤{p.v_charge_cutoff} V  "
              f"discharge≥{p.v_discharge_cutoff} V")
    print(f"  [{len(keys) + 1}] custom (type each value)")
    print()

    while True:
        s = input(f"Pick [1-{len(keys) + 1}]: ").strip()
        try:
            idx = int(s)
        except ValueError:
            print("  not a number")
            continue
        if 1 <= idx <= len(keys):
            base = PROFILES[keys[idx - 1]]
            break
        if idx == len(keys) + 1:
            base = None
            break
        print(f"  must be in 1..{len(keys) + 1}")

    if base is not None:
        # Show base, allow tweaks (capacity / cut-offs).
        print()
        print(f"Selected: {base.name}")
        print("Press <enter> to keep default, or type a new value.")
        chem = base.chem_envelope()
        q = _prompt_float("rated capacity (mAh)", base.q_rated_mAh, 50.0, 50000.0)
        v_chg = _prompt_float(
            "charge cut-off voltage (V)", base.v_charge_cutoff,
            chem.v_discharge_min + 0.5, chem.v_abs_max,
        )
        v_dis = _prompt_float(
            "discharge cut-off voltage (V)", base.v_discharge_cutoff,
            chem.v_abs_min, v_chg - 0.5,
        )
        i_chg = _prompt_float(
            "charge CC current (A)", base.i_charge_cc, 0.001, 5.0,
        )
        i_term = _prompt_float(
            "charge termination current (A)", base.i_charge_term,
            0.0001, i_chg * 0.9,
        )
        i_dis = _prompt_float(
            "baseline discharge CC current (A)", base.i_discharge_cc, 0.001, 5.0,
        )
        custom_name = input(f"  display name [{base.name}]: ").strip() or base.name
        p = BatteryProfile(
            name=custom_name,
            chemistry=base.chemistry,
            q_rated_mAh=q,
            v_charge_cv=v_chg, v_charge_cutoff=v_chg,
            i_charge_cc=i_chg, i_charge_term=i_term,
            v_discharge_cutoff=v_dis,
            i_discharge_cc=i_dis,
            v_nominal=base.v_nominal,
        )
    else:
        # Fully custom — chemistry first.
        print()
        chem_keys = list(CHEMISTRIES)
        for i, k in enumerate(chem_keys, 1):
            print(f"  [{i}] {k} — {CHEMISTRIES[k].name}")
        while True:
            s = input(f"chemistry [1-{len(chem_keys)}]: ").strip()
            try:
                idx = int(s) - 1
            except ValueError:
                continue
            if 0 <= idx < len(chem_keys):
                chem_key = chem_keys[idx]
                break
        chem = CHEMISTRIES[chem_key]
        name = input("display name: ").strip() or f"custom-{chem_key}"
        q = _prompt_float("rated capacity (mAh)", 2000.0, 50.0, 50000.0)
        v_chg = _prompt_float(
            "charge cut-off voltage (V)", chem.v_charge_max,
            chem.v_discharge_min + 0.5, chem.v_abs_max,
        )
        v_dis = _prompt_float(
            "discharge cut-off voltage (V)", chem.v_discharge_min,
            chem.v_abs_min, v_chg - 0.5,
        )
        i_chg = _prompt_float("charge CC current (A)", q / 2000.0, 0.001, 5.0)
        i_term = _prompt_float(
            "charge termination current (A)", i_chg * 0.05,
            0.0001, i_chg * 0.9,
        )
        i_dis = _prompt_float("baseline discharge CC current (A)", q / 2000.0, 0.001, 5.0)
        p = BatteryProfile(
            name=name, chemistry=chem_key, q_rated_mAh=q,
            v_charge_cv=v_chg, v_charge_cutoff=v_chg,
            i_charge_cc=i_chg, i_charge_term=i_term,
            v_discharge_cutoff=v_dis, i_discharge_cc=i_dis,
        )

    errs = p.validate()
    if errs:
        print("\nVALIDATION FAILED:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(2)
    return p


def print_summary(p: BatteryProfile) -> None:
    chem = p.chem_envelope()
    print()
    print("=" * 60)
    print(f"Active battery profile: {p.name}")
    print(f"  chemistry: {p.chemistry} ({chem.name})")
    print(f"  Q_rated = {p.q_rated_mAh:.0f} mAh")
    print(f"  charge: V_cv={p.v_charge_cutoff:.3f} V  "
          f"I_cc={p.i_charge_cc:.3f} A  I_term={p.i_charge_term:.3f} A")
    print(f"  discharge: V_cutoff={p.v_discharge_cutoff:.3f} V  "
          f"I_cc={p.i_discharge_cc:.3f} A")
    print(f"  chemistry envelope: V_abs=[{chem.v_abs_min}, {chem.v_abs_max}] V")
    print("=" * 60)
