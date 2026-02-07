#!/usr/bin/env python3
"""
Run the Ice Cream Manufacturing & Wastewater Valorization Simulator.

One full cycle: Mixing → CIP → Filtration → Bioplastic.
Uses default parameters; report is printed to stdout.

Usage (from project root):
  python run.py
  uv run python run.py
"""

import sys
from pathlib import Path

# Allow running without installing (e.g. from repo clone)
if __name__ == "__main__":
    src = Path(__file__).resolve().parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from icecream_simulator import run_full_cycle, print_report

if __name__ == "__main__":
    report = run_full_cycle()
    print_report(report)
