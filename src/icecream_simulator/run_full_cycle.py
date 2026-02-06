"""
Main execution: one full cycle
  Mixing → Washing (CIP) → Filtering → Plastic Conversion
with a report on efficiency and plastic yield.
Supports optional on_stage_complete callback for dashboards and
pluggable mixing_model / bioconversion_model for extensibility.
"""

from __future__ import annotations

from collections.abc import Callable

from icecream_simulator.schemas import RawMaterials, MassBalanceState, StageResult
from icecream_simulator.mixer import MixerInput, MixerModelBase, DefaultMixerModel, run_mixer
from icecream_simulator.cip import CIPInput, run_cip
from icecream_simulator.filtration import FiltrationConfig, run_filtration
from icecream_simulator.bioconversion import (
    run_bioconversion,
    BioconversionModelBase,
    DefaultBioconversionModel,
)


def run_full_cycle(
    raw_materials: RawMaterials | None = None,
    tank_surface_area_m2: float = 10.0,
    water_volume_L: float = 80.0,
    bioplastic_yield_coefficient: float = 0.4,
    mixing_model: MixerModelBase | None = None,
    bioconversion_model: BioconversionModelBase | None = None,
    on_stage_complete: Callable[[str, StageResult, dict], None] | None = None,
) -> dict:
    """
    Run one full cycle: Mixing → CIP → Filtration → Bioconversion.
    Returns a report dict with efficiency and plastic yield.

    Args:
        raw_materials: Input recipe; default 200 kg batch if None.
        tank_surface_area_m2: Tank surface for residue model.
        water_volume_L: CIP water volume.
        bioplastic_yield_coefficient: Used only if bioconversion_model is None.
        mixing_model: Pluggable mixer; uses DefaultMixerModel if None.
        bioconversion_model: Pluggable bioconversion; uses DefaultBioconversionModel if None.
        on_stage_complete: Optional callback (stage_name, StageResult, cumulative) for monitoring.
    """
    raw = raw_materials or RawMaterials(
        milk=100.0, cream=30.0, sugar=25.0, stabilizers=2.0, water=43.0
    )
    total_input_kg = raw.total_mass
    mixer_impl = mixing_model or DefaultMixerModel()
    bioconv_impl = bioconversion_model or DefaultBioconversionModel(
        yield_coefficient=bioplastic_yield_coefficient
    )
    cumulative: dict = {"product_kg": 0.0, "energy_consumed": 0.0}

    # --- 1. Mixer ---
    mixer_in = MixerInput(
        raw_materials=raw,
        tank_surface_area_m2=tank_surface_area_m2,
        rpm=60.0,
        mixing_time_s=300.0,
    )
    product_batch, tank_residue, power_W = mixer_impl.run(mixer_in)
    product_kg = product_batch.mass_kg
    residue_kg = tank_residue.mass_kg
    mixer_efficiency = (product_kg / total_input_kg * 100.0) if total_input_kg > 0 else 0.0
    cumulative["product_kg"] = product_kg
    cumulative["energy_consumed"] = power_W  # J not tracked per-stage; use power as proxy

    if on_stage_complete:
        mb = MassBalanceState(
            stage="mixer",
            mass_in=total_input_kg,
            mass_out=product_kg + residue_kg,
            energy_consumed=power_W,
            mass_product=product_kg,
            mass_waste=residue_kg,
            metadata={"viscosity": product_batch.viscosity_Pa_s, "residue_kg": residue_kg},
        )
        on_stage_complete(
            "mixer",
            StageResult(
                stage_name="mixer",
                mass_balance=mb,
                outputs={
                    "product_to_freezer_kg": product_kg,
                    "tank_residue_kg": residue_kg,
                    "viscosity_Pa_s": product_batch.viscosity_Pa_s,
                    "mixing_power_W": power_W,
                },
                model_used=mixer_impl.model_name,
            ),
            dict(cumulative),
        )

    # --- 2. CIP ---
    cip_in = CIPInput(
        tank_residue=tank_residue,
        water_volume_L=water_volume_L,
    )
    wastewater = run_cip(cip_in)

    if on_stage_complete:
        mb = MassBalanceState(
            stage="cip",
            mass_in=cip_in.water_volume_L * 1.0 + residue_kg,
            mass_out=wastewater.mass_kg,
            energy_consumed=0.0,
            mass_product=0.0,
            mass_waste=wastewater.mass_kg,
            metadata={"tss_mg_L": wastewater.tss_mg_L, "bod_mg_L": wastewater.bod_mg_L},
        )
        on_stage_complete(
            "cip",
            StageResult(
                stage_name="cip",
                mass_balance=mb,
                outputs=wastewater.model_dump(),
                model_used="CIP",
            ),
            dict(cumulative),
        )

    # --- 3. Filtration ---
    config = FiltrationConfig(
        filter_pore_size_um=0.1,
        membrane_surface_area_m2=10.0,
    )
    permeate, retentate, filter_state = run_filtration(wastewater, config)
    maintenance_flag = filter_state.maintenance_required

    if on_stage_complete:
        mb = MassBalanceState(
            stage="filtration",
            mass_in=wastewater.mass_kg,
            mass_out=permeate.mass_kg + retentate.mass_kg,
            energy_consumed=0.0,
            mass_product=permeate.mass_kg,
            mass_waste=retentate.mass_kg,
            metadata={
                "filter_saturation": filter_state.saturation_fraction,
                "maintenance_required": maintenance_flag,
                "retentate_sugar_kg": retentate.sugar_mass_kg,
            },
        )
        on_stage_complete(
            "filtration",
            StageResult(
                stage_name="filtration",
                mass_balance=mb,
                outputs={
                    "permeate_volume_L": permeate.volume_L,
                    "retentate_mass_kg": retentate.mass_kg,
                    "retentate_sugar_kg": retentate.sugar_mass_kg,
                    "filter_saturation_pct": filter_state.saturation_fraction * 100,
                    "maintenance_required": maintenance_flag,
                },
                model_used="Filtration",
            ),
            dict(cumulative),
        )

    # --- 4. Bioconversion ---
    bioplastic_out = bioconv_impl.run(retentate)
    pha_kg = bioplastic_out.mass_kg
    sugar_for_plastic_kg = bioplastic_out.sugar_consumed_kg
    plastic_yield_from_sugar = (
        (pha_kg / sugar_for_plastic_kg * 100.0) if sugar_for_plastic_kg > 0 else 0.0
    )
    plastic_yield_from_total_input = (pha_kg / total_input_kg * 100.0) if total_input_kg > 0 else 0.0

    if on_stage_complete:
        mb = MassBalanceState(
            stage="bioconversion",
            mass_in=retentate.sugar_mass_kg,
            mass_out=pha_kg,
            energy_consumed=0.0,
            mass_product=pha_kg,
            mass_waste=0.0,
            metadata={
                "yield_coefficient": bioplastic_out.yield_coefficient,
                "sugar_consumed_kg": sugar_for_plastic_kg,
            },
        )
        on_stage_complete(
            "bioconversion",
            StageResult(
                stage_name="bioconversion",
                mass_balance=mb,
                outputs=bioplastic_out.model_dump(),
                model_used=bioconv_impl.model_name,
            ),
            {**cumulative, "bioplastic_kg": pha_kg},
        )

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
            "yield_coefficient": bioplastic_out.yield_coefficient,
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
