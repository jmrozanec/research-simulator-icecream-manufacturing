#!/usr/bin/env python3
"""
Run the simplified ice cream + bioplastic simulator.

Usage (from project root):
  python run.py
  python run.py --preset GIUDICI_2021_INDUSTRIAL
  python run.py --literature-suite
  uv run python run.py
"""

import argparse
import sys
from pathlib import Path

if __name__ == "__main__":
    src = Path(__file__).resolve().parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from icecream_simulator import list_preset_ids, print_report, run_full_cycle, run_literature_suite

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simplified ice cream + valorization simulator")
    parser.add_argument("--preset", type=str, default=None, metavar="ID", help="Literature preset id")
    parser.add_argument(
        "--literature-suite",
        action="store_true",
        help="Run all presets (compact table)",
    )
    parser.add_argument(
        "--no-cleaning",
        action="store_true",
        help="Skip CIP and downstream treatment (zeros valorization)",
    )
    args = parser.parse_args()

    if args.literature_suite:
        rows = run_literature_suite(include_cleaning_phase=not args.no_cleaning)
        print("preset_id\tproduct_kg\tbioplastic_kg\tmass_ok")
        for r in rows:
            print(
                f"{r['preset_id']}\t{r['product_kg']:.4f}\t{r['bioplastic_kg']:.4f}\t{r['mass_balance_closed']}"
            )
    else:
        if args.preset is not None and args.preset not in list_preset_ids():
            print(f"Unknown preset {args.preset!r}. Valid: {', '.join(list_preset_ids())}", file=sys.stderr)
            sys.exit(2)
        report = run_full_cycle(
            literature_preset_id=args.preset,
            include_cleaning_phase=not args.no_cleaning,
        )
        print_report(report)
