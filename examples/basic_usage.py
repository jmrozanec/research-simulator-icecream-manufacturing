"""Minimal programmatic example."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from icecream_simulator import RawMaterials, print_report, run_full_cycle

raw = RawMaterials(milk=100, cream=30, sugar=25, stabilizers=2, water=43, emulsifiers_kg=0.5)
report = run_full_cycle(raw_materials=raw, residue_mass_fraction=0.02, air_overrun=0.5)
print_report(report)
