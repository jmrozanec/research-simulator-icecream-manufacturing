#!/usr/bin/env python3
"""
Run the Ice Cream Manufacturing & Wastewater Valorization Simulator.

One full cycle: Mixing → CIP → Filtration → Bioplastic.
Uses default parameters; report is printed to stdout.

Usage (from project root):
  python run.py
  python run.py --preset GIUDICI_2021_INDUSTRIAL
  python run.py --literature-suite
  uv run python run.py
"""

import argparse
import sys
from pathlib import Path

# Allow running without installing (e.g. from repo clone)
if __name__ == "__main__":
    src = Path(__file__).resolve().parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from icecream_simulator import list_preset_ids, run_full_cycle, print_report, run_literature_suite

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ice cream manufacturing & valorization simulator")
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        metavar="ID",
        help="Literature recipe preset id (see icecream_simulator.literature_recipes)",
    )
    parser.add_argument(
        "--literature-suite",
        action="store_true",
        help="Run all literature presets (compact table to stdout)",
    )
    parser.add_argument(
        "--no-cleaning",
        action="store_true",
        help="Skip CIP/filtration/bioconversion (faster batch runs)",
    )
    args = parser.parse_args()

    if args.literature_suite:
        rows = run_literature_suite(include_cleaning_phase=not args.no_cleaning)
        print("preset_id\tproduct_kg\tice_um\tifp_C\tkelvin_K\thardness_kPa\tmass_ok")
        for r in rows:
            print(
                f"{r['preset_id']}\t{r['product_kg']:.4f}\t{r['ice_crystal_mean_um']:.4f}\t"
                f"{r['initial_freezing_point_mix_C']:.4f}\t{r['kelvin_depression_K']:.6f}\t"
                f"{r['hardness_proxy_kPa']:.4f}\t{r['mass_balance_closed']}"
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
