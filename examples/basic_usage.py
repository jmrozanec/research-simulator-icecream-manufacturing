"""
Basic Usage: Run one full cycle with default models.

Minimal example: Mixing → CIP → Filtration → Bioconversion.
"""

import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from icecream_simulator import RawMaterials, run_full_cycle, print_report


def main() -> None:
    raw_materials = RawMaterials(
        milk=100.0,
        cream=30.0,
        sugar=25.0,
        stabilizers=2.0,
        water=43.0,
    )

    report = run_full_cycle(raw_materials=raw_materials)

    print("=== Simulation Report ===")
    print(f"Product to freezer: {report['mixer']['product_to_freezer_kg']:.2f} kg")
    print(f"Ice cream volume:   {report['mixer']['ice_cream_volume_L']:.2f} L")
    print(f"Wastewater:         {report['cip']['wastewater_mass_kg']:.2f} kg")
    print(f"Bioplastic (PHA):   {report['bioconversion']['bioplastic_mass_kg']:.2f} kg")
    print(f"Mass balance closed: {report['efficiency_summary']['mass_balance_closed']}")

    # Full report (exclude typed_report for JSON)
    out = {k: v for k, v in report.items() if k != "typed_report"}
    print("\n--- JSON (excerpt) ---")
    print(json.dumps(out, indent=2, default=str)[:1500] + "...")


if __name__ == "__main__":
    main()
