"""
Sample Run: Verbose data flow demonstration.

Run this script to see exactly how data flows through each stage of the
ice cream production and waste-to-plastic pipeline. Useful for understanding
the simulator's behavior.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from icecream_simulator import (
    RawMaterials,
    SimulationRunner,
    PlaceholderMixingModel,
    PlaceholderBioplasticModel,
)


def main() -> None:
    print("=" * 70)
    print("ICE CREAM PRODUCTION & WASTE-TO-PLASTIC SIMULATION — DATA FLOW")
    print("=" * 70)

    # -----------------------------------------------------------------------
    # INPUT STAGE
    # -----------------------------------------------------------------------
    raw_materials = RawMaterials(
        milk=100.0,
        cream=30.0,
        sugar=25.0,
        stabilizers=2.0,
        water=43.0,
    )

    print("\n┌─ INPUT: Raw Materials ─────────────────────────────────────────┐")
    print(f"│  milk: {raw_materials.milk:>6.1f} kg   cream: {raw_materials.cream:>6.1f} kg   sugar: {raw_materials.sugar:>6.1f} kg")
    print(f"│  stabilizers: {raw_materials.stabilizers:>6.1f} kg   water: {raw_materials.water:>6.1f} kg")
    print(f"│  TOTAL MASS: {raw_materials.total_mass:.1f} kg")
    print("└────────────────────────────────────────────────────────────────┘")

    runner = SimulationRunner(
        mixing_model=PlaceholderMixingModel(),
        bioplastic_model=PlaceholderBioplasticModel(conversion_yield=0.40),
    )

    # -----------------------------------------------------------------------
    # RUN WITH CALLBACK TO TRACE DATA FLOW
    # -----------------------------------------------------------------------

    def on_stage(stage_name: str, result, cumulative: dict) -> None:
        stage_display = {
            "mixing": ("MIXING (PIML)", "Raw materials → Viscosity, thermal properties"),
            "production": ("PRODUCTION", "Mass balance: Output = Input - Shrinkage"),
            "wastewater": ("WASTEWATER", "Cleaning water + product loss → BOD, FOG"),
            "bioplastic_conversion": ("BIOPLASTIC CONVERSION", "Wastewater organics → PHA"),
        }
        title, desc = stage_display.get(stage_name, (stage_name, ""))
        print(f"\n┌─ STAGE: {title}")
        print(f"│  {desc}")
        print("├────────────────────────────────────────────────────────────────")
        print(f"│  Model used: {result.model_used}")
        print(f"│  Mass in:  {result.mass_balance.mass_in:.2f} kg")
        print(f"│  Mass out: {result.mass_balance.mass_out:.2f} kg")
        print(f"│  Product:  {result.mass_balance.mass_product:.2f} kg")
        print(f"│  Waste:    {result.mass_balance.mass_waste:.2f} kg")
        print(f"│  Energy:   {result.mass_balance.energy_consumed:.2e} J")
        if result.outputs:
            print("│  Outputs:")
            for k, v in result.outputs.items():
                if isinstance(v, float):
                    print(f"│    {k}: {v:.4g}")
                else:
                    print(f"│    {k}: {v}")
        print("└────────────────────────────────────────────────────────────────")

    report = runner.run(
        raw_materials=raw_materials,
        shear_rate=120.0,
        temperature=278.15,
        mixing_time=300.0,
        on_stage_complete=on_stage,
        interface_flush_L=5.0,
        cleaning_water_inflow_L=80.0,
    )

    # -----------------------------------------------------------------------
    # FINAL REPORT
    # -----------------------------------------------------------------------
    print("\n┌─ FINAL REPORT ──────────────────────────────────────────────────┐")
    print(f"│  Ice cream product:    {report.total_product_mass:>8.2f} kg")
    print(f"│  Wastewater stream:    {report.total_wastewater_mass:>8.2f} kg")
    print(f"│  Bioplastic (PHA):     {report.total_bioplastic_mass:>8.2f} kg")
    print(f"│  Total energy:         {report.total_energy_consumed:>8.2e} J")
    print(f"│  Mass balance closed:  {report.mass_balance_closed}")
    print("└────────────────────────────────────────────────────────────────┘")

    print("\n► Mass flow summary (closed-loop + operational loss):")
    print(f"  Raw materials ({raw_materials.total_mass:.1f} kg)")
    shrinkage = report.metadata.get("shrinkage_kg", 0)
    print(f"    → Production → {report.total_product_mass:.1f} kg ice cream (shrinkage: {shrinkage:.2f} kg)")
    print(f"    → Wastewater = cleaning water + shrinkage → BOD/FOG")
    print(f"    → Bioplastic → {report.total_bioplastic_mass:.2f} kg PHA from organics")
    print()


if __name__ == "__main__":
    main()
