"""
Basic Usage: Run simulation with default placeholder models.

Minimal example showing the full pipeline with default models.
"""

import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from icecream_simulator import (
    RawMaterials,
    SimulationRunner,
    PlaceholderMixingModel,
    PlaceholderBioplasticModel,
)


def main() -> None:
    runner = SimulationRunner(
        mixing_model=PlaceholderMixingModel(),
        bioplastic_model=PlaceholderBioplasticModel(conversion_yield=0.40),
    )

    raw_materials = RawMaterials(
        milk=100.0,
        cream=30.0,
        sugar=25.0,
        stabilizers=2.0,
        water=43.0,
    )

    report = runner.run(raw_materials)

    print("=== Simulation Report ===")
    print(f"Total product mass: {report.total_product_mass:.2f} kg")
    print(f"Total wastewater: {report.total_wastewater_mass:.2f} kg")
    print(f"Total bioplastic: {report.total_bioplastic_mass:.2f} kg")
    print(f"Total energy consumed: {report.total_energy_consumed:.2e} J")
    print(f"Mass balance closed: {report.mass_balance_closed}")

    # JSON output
    print("\n--- JSON (excerpt) ---")
    print(json.dumps(report.model_dump(), indent=2, default=str)[:1500] + "...")


if __name__ == "__main__":
    main()
