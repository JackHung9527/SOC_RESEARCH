#!/usr/bin/env python3
"""Pick the active battery profile for this bench.

Run this once before any charge / phase script. Persists the choice to
TEST/data/active_profile.json so subsequent scripts auto-load it.

Examples:
  python3 TEST/select_battery.py            # interactive picker
  python3 TEST/select_battery.py --show     # print current selection
  python3 TEST/select_battery.py --list     # list catalogue keys
  python3 TEST/select_battery.py 18650-NMC-2150   # pick by key, no prompt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from TEST.profiles import (
    PROFILES,
    get_profile,
    interactive_pick,
    list_profiles,
    print_summary,
    save_active_profile,
    try_load_active_profile,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Pick active battery profile.")
    ap.add_argument("key", nargs="?", help="catalogue key (skip prompt)")
    ap.add_argument("--show", action="store_true",
                    help="print the currently active profile and exit")
    ap.add_argument("--list", action="store_true",
                    help="list catalogue keys and exit")
    args = ap.parse_args()

    if args.list:
        print("Available profiles:")
        for k in list_profiles():
            p = PROFILES[k]
            print(f"  {k:<22}  {p.name}")
        return 0

    if args.show:
        p = try_load_active_profile()
        if p is None:
            print("(no active profile selected)")
            return 1
        print_summary(p)
        return 0

    if args.key:
        try:
            p = get_profile(args.key)
        except KeyError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        save_active_profile(p)
        print_summary(p)
        print(f"Saved to TEST/data/active_profile.json")
        return 0

    # Interactive.
    p = interactive_pick()
    save_active_profile(p)
    print_summary(p)
    print(f"\nSaved to TEST/data/active_profile.json")
    print("Now you can run:")
    print("  python3 TEST/charge.py")
    print("  python3 TEST/phase2_baseline.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
