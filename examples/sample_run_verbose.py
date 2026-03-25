"""
Sample Run: Verbose data flow demonstration.

Shows how data flows through each stage: Mixer → CIP → Filtration → Bioplastic.
Useful for understanding the simulator's behavior.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from icecream_simulator import RawMaterials, run_full_cycle


def main() -> None:
    print("=" * 70)
    print("ICE CREAM PRODUCTION & WASTE-TO-PLASTIC SIMULATION — DATA FLOW")
    print("=" * 70)

    raw_materials = RawMaterials(
        milk=100.0,
        cream=30.0,
        sugar=25.0,
        stabilizers=1.65,
        emulsifiers_kg=0.35,
        water=43.0,
    )

    print("\n┌─ INPUT: Raw Materials ─────────────────────────────────────────┐")
    print(f"│  milk: {raw_materials.milk:>6.1f} kg   cream: {raw_materials.cream:>6.1f} kg   sugar: {raw_materials.sugar:>6.1f} kg")
    print(f"│  stabilizers: {raw_materials.stabilizers:>6.1f} kg   water: {raw_materials.water:>6.1f} kg")
    print(f"│  TOTAL MASS: {raw_materials.total_mass:.1f} kg")
    print("└────────────────────────────────────────────────────────────────┘")

    stage_display = {
        "mixer": ("MIXER", "Rheology, power, residue → Product + TankResidue"),
        "cip": ("CIP", "Residue + water → Wastewater (TSS, BOD, FOG)"),
        "filtration": ("FILTRATION", "Wastewater → Permeate + Retentate (sugar concentrate)"),
        "bioconversion": ("BIOCONVERSION", "Retentate sugar → PHA"),
    }

    def on_stage(stage_name: str, result, cumulative: dict) -> None:
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

    report = run_full_cycle(
        raw_materials=raw_materials,
        on_stage_complete=on_stage,
        interface_flush_L=5.0,
        water_volume_L=80.0,
    )

    print("\n┌─ FINAL REPORT ──────────────────────────────────────────────────┐")
    print(f"│  Product to freezer:   {report['mixer']['product_to_freezer_kg']:>8.2f} kg")
    print(f"│  Ice cream volume:     {report['mixer']['ice_cream_volume_L']:>8.2f} L")
    print(f"│  Wastewater:           {report['cip']['wastewater_mass_kg']:>8.2f} kg")
    print(f"│  Bioplastic (PHA):     {report['bioconversion']['bioplastic_mass_kg']:>8.2f} kg")
    print(f"│  Mass balance closed: {report['efficiency_summary']['mass_balance_closed']}")
    print("└────────────────────────────────────────────────────────────────┘")

    print("\n► Mass flow summary:")
    print(f"  Raw materials ({raw_materials.total_mass:.1f} kg)")
    print(f"    → Mixer → {report['mixer']['product_to_freezer_kg']:.1f} kg to freezer + {report['mixer']['tank_residue_kg']:.2f} kg residue + {report['mixer']['interface_flush_kg']:.2f} kg interface flush")
    print(f"    → CIP → wastewater {report['cip']['wastewater_mass_kg']:.1f} kg (TSS, BOD, FOG)")
    print(f"    → Filtration → permeate + retentate ({report['filtration']['retentate_sugar_kg']:.2f} kg sugar)")
    print(f"    → Bioconversion → {report['bioconversion']['bioplastic_mass_kg']:.2f} kg PHA")
    print()


if __name__ == "__main__":
    main()
