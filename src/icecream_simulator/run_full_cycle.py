"""
Main execution: one full cycle
  Mixing → Washing (CIP) → Filtering → Plastic Conversion
with a report on efficiency and plastic yield.
"""

from __future__ import annotations

from icecream_simulator.schemas import RawMaterials
from icecream_simulator.mixer import MixerInput, run_mixer
from icecream_simulator.cip import CIPInput, run_cip
from icecream_simulator.filtration import FiltrationConfig, run_filtration
from icecream_simulator.bioconversion import run_bioconversion


def run_full_cycle(
    raw_materials: RawMaterials | None = None,
    tank_surface_area_m2: float = 10.0,
    water_volume_L: float = 80.0,
    bioplastic_yield_coefficient: float = 0.4,
) -> dict:
    """
    Run one full cycle: Mixing → CIP → Filtration → Bioconversion.
    Returns a report dict with efficiency and plastic yield.
    """
    raw = raw_materials or RawMaterials(
        milk=100.0, cream=30.0, sugar=25.0, stabilizers=2.0, water=43.0
    )
    total_input_kg = raw.total_mass

    # --- 1. Mixer ---
    mixer_in = MixerInput(
        raw_materials=raw,
        tank_surface_area_m2=tank_surface_area_m2,
        rpm=60.0,
        mixing_time_s=300.0,
    )
    product_batch, tank_residue, power_W = run_mixer(mixer_in)
    product_kg = product_batch.mass_kg
    residue_kg = tank_residue.mass_kg
    mixer_efficiency = (product_kg / total_input_kg * 100.0) if total_input_kg > 0 else 0.0

    # --- 2. CIP ---
    cip_in = CIPInput(
        tank_residue=tank_residue,
        water_volume_L=water_volume_L,
    )
    wastewater = run_cip(cip_in)

    # --- 3. Filtration ---
    config = FiltrationConfig(
        filter_pore_size_um=0.1,
        membrane_surface_area_m2=10.0,
    )
    permeate, retentate, filter_state = run_filtration(wastewater, config)
    maintenance_flag = filter_state.maintenance_required

    # --- 4. Bioconversion ---
    bioplastic_out = run_bioconversion(retentate, yield_coefficient=bioplastic_yield_coefficient)
    pha_kg = bioplastic_out.mass_kg
    sugar_for_plastic_kg = bioplastic_out.sugar_consumed_kg
    plastic_yield_from_sugar = (
        (pha_kg / sugar_for_plastic_kg * 100.0) if sugar_for_plastic_kg > 0 else 0.0
    )
    plastic_yield_from_total_input = (pha_kg / total_input_kg * 100.0) if total_input_kg > 0 else 0.0

    report = {
        "inputs": {
            "raw_materials_kg": total_input_kg,
            "tank_surface_area_m2": tank_surface_area_m2,
            "cleaning_water_L": water_volume_L,
        },
        "mixer": {
            "product_to_freezer_kg": product_kg,
            "tank_residue_kg": residue_kg,
            "mixing_power_W": power_W,
            "viscosity_Pa_s": product_batch.viscosity_Pa_s,
            "mixer_efficiency_pct": round(mixer_efficiency, 2),
        },
        "cip": {
            "wastewater_volume_L": wastewater.volume_L,
            "wastewater_mass_kg": wastewater.mass_kg,
            "dissolved_sugar_kg": wastewater.dissolved_sugar_kg,
            "tss_mg_L": round(wastewater.tss_mg_L, 2),
            "bod_mg_L": round(wastewater.bod_mg_L, 2),
        },
        "filtration": {
            "permeate_volume_L": permeate.volume_L,
            "retentate_mass_kg": retentate.mass_kg,
            "retentate_sugar_kg": retentate.sugar_mass_kg,
            "filter_saturation_pct": round(filter_state.saturation_fraction * 100, 2),
            "maintenance_required": maintenance_flag,
        },
        "bioconversion": {
            "bioplastic_mass_kg": pha_kg,
            "sugar_consumed_kg": sugar_for_plastic_kg,
            "yield_coefficient": bioplastic_yield_coefficient,
            "plastic_yield_from_sugar_pct": round(plastic_yield_from_sugar, 2),
            "plastic_yield_from_input_pct": round(plastic_yield_from_total_input, 4),
        },
        "efficiency_summary": {
            "product_recovery_pct": round(mixer_efficiency, 2),
            "plastic_kg_per_tonne_input": round(pha_kg / (total_input_kg / 1000.0), 4),
            "maintenance_required": maintenance_flag,
        },
    }
    return report


def print_report(report: dict) -> None:
    """Print a human-readable report to stdout."""
    print("=" * 60)
    print("ICE CREAM MANUFACTURING & WASTEWATER VALORIZATION SIMULATOR")
    print("Full cycle report: Mixing → CIP → Filtration → Bioplastic")
    print("=" * 60)
    r = report
    print("\n--- INPUTS ---")
    print(f"  Raw materials (kg):     {r['inputs']['raw_materials_kg']:.2f}")
    print(f"  Tank surface area (m²): {r['inputs']['tank_surface_area_m2']:.2f}")
    print(f"  Cleaning water (L):     {r['inputs']['cleaning_water_L']:.2f}")

    print("\n--- MIXER ---")
    print(f"  Product to freezer (kg): {r['mixer']['product_to_freezer_kg']:.2f}")
    print(f"  Tank residue (kg):       {r['mixer']['tank_residue_kg']:.2f}")
    print(f"  Mixing power (W):        {r['mixer']['mixing_power_W']:.2f}")
    print(f"  Viscosity (Pa·s):        {r['mixer']['viscosity_Pa_s']:.4f}")
    print(f"  Mixer efficiency (%):    {r['mixer']['mixer_efficiency_pct']}")

    print("\n--- CIP (Wastewater) ---")
    print(f"  Wastewater volume (L):   {r['cip']['wastewater_volume_L']:.2f}")
    print(f"  Dissolved sugar (kg):     {r['cip']['dissolved_sugar_kg']:.2f}")
    print(f"  TSS (mg/L):              {r['cip']['tss_mg_L']}")
    print(f"  BOD (mg/L):              {r['cip']['bod_mg_L']}")

    print("\n--- FILTRATION ---")
    print(f"  Permeate volume (L):     {r['filtration']['permeate_volume_L']:.2f}")
    print(f"  Retentate mass (kg):     {r['filtration']['retentate_mass_kg']:.2f}")
    print(f"  Retentate sugar (kg):    {r['filtration']['retentate_sugar_kg']:.2f}")
    print(f"  Filter saturation (%):   {r['filtration']['filter_saturation_pct']}")
    print(f"  Maintenance required:     {r['filtration']['maintenance_required']}")

    print("\n--- BIOCONVERSION (Sugar → PHA) ---")
    print(f"  Bioplastic produced (kg): {r['bioconversion']['bioplastic_mass_kg']:.4f}")
    print(f"  Sugar consumed (kg):      {r['bioconversion']['sugar_consumed_kg']:.4f}")
    print(f"  Yield coefficient:       {r['bioconversion']['yield_coefficient']}")
    print(f"  Yield from sugar (%):    {r['bioconversion']['plastic_yield_from_sugar_pct']}")
    print(f"  Yield from total input (%): {r['bioconversion']['plastic_yield_from_input_pct']}")

    print("\n--- EFFICIENCY SUMMARY ---")
    print(f"  Product recovery (%):    {r['efficiency_summary']['product_recovery_pct']}")
    print(f"  Plastic (kg/tonne input): {r['efficiency_summary']['plastic_kg_per_tonne_input']}")
    print(f"  Maintenance required:     {r['efficiency_summary']['maintenance_required']}")
    print("=" * 60)


if __name__ == "__main__":
    report = run_full_cycle()
    print_report(report)
