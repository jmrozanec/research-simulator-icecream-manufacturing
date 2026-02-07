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
from icecream_simulator.batch_models import (
    TankResidue,
    WastewaterStream,
    MaterialBatchCycleReport,
)

# Mix density (kg/L) for volume and interface flush
MIX_DENSITY_KG_L = 1.05


def _thermal_properties_from_composition(water_fraction: float) -> tuple[float, float]:
    """Thermal conductivity (W/(m·K)) and specific heat (J/(kg·K)) from water fraction (parity with PIML)."""
    return (0.4 + 0.2 * water_fraction, 3500.0 + 500.0 * water_fraction)


def run_full_cycle(
    raw_materials: RawMaterials | None = None,
    tank_surface_area_m2: float = 10.0,
    water_volume_L: float = 80.0,
    bioplastic_yield_coefficient: float = 0.4,
    mixing_model: MixerModelBase | None = None,
    bioconversion_model: BioconversionModelBase | None = None,
    on_stage_complete: Callable[[str, StageResult, dict], None] | None = None,
    air_overrun: float = 0.5,
    interface_flush_L: float = 5.0,
    include_cleaning_phase: bool = True,
    temperature_K: float = 278.0,
    mixing_time_s: float = 300.0,
    rpm: float = 60.0,
) -> dict:
    """
    Run one full cycle: Mixing → [CIP → Filtration → Bioconversion when include_cleaning_phase].
    Single ice cream process: no duplicate phases. Interface flush is applied as additional
    loss from mixer output (same as P1); residue + interface flush go to CIP together.

    Returns a report dict with efficiency, plastic yield, and mass_balance_closed.

    Args:
        raw_materials: Input recipe; default 200 kg batch if None.
        tank_surface_area_m2: Tank surface for residue model.
        water_volume_L: CIP water volume (used only when include_cleaning_phase=True).
        bioplastic_yield_coefficient: Used only if bioconversion_model is None.
        mixing_model: Pluggable mixer; uses DefaultMixerModel if None.
        bioconversion_model: Pluggable bioconversion; uses DefaultBioconversionModel if None.
        on_stage_complete: Optional callback (stage_name, StageResult, cumulative) for monitoring.
        air_overrun: Volume overrun fraction (0.5 = 50%) for ice cream volume.
        interface_flush_L: Start-of-run discard (L); subtracted from product, added to CIP feed.
        include_cleaning_phase: If False, skip CIP/filtration/bioconversion (no wastewater path).
        temperature_K: Initial mix temperature (K) for mixer.
        mixing_time_s: Mixing duration (s).
        rpm: Mixer RPM.
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

    # --- 1. Mixer (single phase: rheology + residue) ---
    mixer_in = MixerInput(
        raw_materials=raw,
        tank_surface_area_m2=tank_surface_area_m2,
        rpm=rpm,
        mixing_time_s=mixing_time_s,
        initial_temperature_K=temperature_K,
    )
    product_batch, tank_residue, power_W = mixer_impl.run(mixer_in)
    product_kg = product_batch.mass_kg
    residue_kg = tank_residue.mass_kg

    # Interface flush: additional operational loss (parity with P1). Not a separate phase:
    # subtract from product, add to the mass that goes to CIP.
    interface_flush_kg = min(interface_flush_L * MIX_DENSITY_KG_L, product_kg)
    product_to_freezer_kg = product_kg - interface_flush_kg
    # Combined residue for CIP = tank residue + interface flush (same composition as product)
    cip_residue = TankResidue(
        mass_kg=residue_kg + interface_flush_kg,
        composition=product_batch.composition,
        viscosity_Pa_s=product_batch.viscosity_Pa_s,
    )

    mixer_efficiency = (
        (product_to_freezer_kg / total_input_kg * 100.0) if total_input_kg > 0 else 0.0
    )
    cumulative["product_kg"] = product_to_freezer_kg
    cumulative["energy_consumed"] = power_W

    thermal_conductivity, specific_heat = _thermal_properties_from_composition(
        product_batch.composition.water
    )
    ice_cream_volume_L = (product_to_freezer_kg / MIX_DENSITY_KG_L) * (1.0 + air_overrun)

    if on_stage_complete:
        mb = MassBalanceState(
            stage="mixer",
            mass_in=total_input_kg,
            mass_out=product_to_freezer_kg + cip_residue.mass_kg,
            energy_consumed=power_W,
            mass_product=product_to_freezer_kg,
            mass_waste=cip_residue.mass_kg,
            metadata={
                "viscosity": product_batch.viscosity_Pa_s,
                "residue_kg": residue_kg,
                "interface_flush_kg": interface_flush_kg,
                "thermal_conductivity": thermal_conductivity,
                "specific_heat": specific_heat,
            },
        )
        on_stage_complete(
            "mixer",
            StageResult(
                stage_name="mixer",
                mass_balance=mb,
                outputs={
                    "product_to_freezer_kg": product_to_freezer_kg,
                    "tank_residue_kg": residue_kg,
                    "interface_flush_kg": interface_flush_kg,
                    "viscosity_Pa_s": product_batch.viscosity_Pa_s,
                    "mixing_power_W": power_W,
                    "thermal_conductivity_W_mK": thermal_conductivity,
                    "specific_heat_J_kgK": specific_heat,
                    "ice_cream_volume_L": ice_cream_volume_L,
                },
                model_used=mixer_impl.model_name,
            ),
            dict(cumulative),
        )

    # --- 2. CIP (only when cleaning phase included; same phase, no duplicate) ---
    if include_cleaning_phase:
        cip_in = CIPInput(
            tank_residue=cip_residue,
            water_volume_L=water_volume_L,
        )
        wastewater = run_cip(cip_in)
    else:
        # No cleaning: zero wastewater (residue stays in tank until next clean)
        wastewater = WastewaterStream(
            volume_L=0.0,
            mass_kg=0.0,
            temperature_K=323.0,
            tss_mg_L=0.0,
            dissolved_sugar_kg=0.0,
            cod_mg_L=0.0,
            bod_mg_L=0.0,
            fog_mg_L=0.0,
        )
        cip_in = CIPInput(tank_residue=cip_residue, water_volume_L=0.0)

    if on_stage_complete:
        mb = MassBalanceState(
            stage="cip",
            mass_in=cip_in.water_volume_L * 1.0 + cip_residue.mass_kg,
            mass_out=wastewater.mass_kg,
            energy_consumed=0.0,
            mass_product=0.0,
            mass_waste=wastewater.mass_kg,
            metadata={
                "tss_mg_L": wastewater.tss_mg_L,
                "bod_mg_L": wastewater.bod_mg_L,
                "fog_mg_L": wastewater.fog_mg_L,
            },
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

    # Mass balance: input = product to freezer + loss (residue + interface flush). Water is external.
    total_out_kg = product_to_freezer_kg + cip_residue.mass_kg
    mass_balance_closed = abs(total_input_kg - total_out_kg) < 1e-6

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
            "cleaning_water_L": water_volume_L if include_cleaning_phase else 0.0,
            "air_overrun": air_overrun,
            "interface_flush_L": interface_flush_L,
            "include_cleaning_phase": include_cleaning_phase,
            "temperature_K": temperature_K,
            "mixing_time_s": mixing_time_s,
            "rpm": rpm,
        },
        "mixer": {
            "product_to_freezer_kg": product_to_freezer_kg,
            "ice_cream_volume_L": ice_cream_volume_L,
            "tank_residue_kg": residue_kg,
            "interface_flush_kg": interface_flush_kg,
            "mixing_power_W": power_W,
            "viscosity_Pa_s": product_batch.viscosity_Pa_s,
            "thermal_conductivity_W_mK": thermal_conductivity,
            "specific_heat_J_kgK": specific_heat,
            "mixer_efficiency_pct": round(mixer_efficiency, 2),
        },
        "cip": {
            "wastewater_volume_L": wastewater.volume_L,
            "wastewater_mass_kg": wastewater.mass_kg,
            "dissolved_sugar_kg": wastewater.dissolved_sugar_kg,
            "tss_mg_L": round(wastewater.tss_mg_L, 2),
            "bod_mg_L": round(wastewater.bod_mg_L, 2),
            "fog_mg_L": round(wastewater.fog_mg_L, 2),
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
            "plastic_kg_per_tonne_input": round(
                pha_kg / (total_input_kg / 1000.0), 4
            ) if total_input_kg > 0 else 0.0,
            "maintenance_required": maintenance_flag,
            "mass_balance_closed": mass_balance_closed,
        },
    }
    report["typed_report"] = MaterialBatchCycleReport(
        raw_materials_kg=total_input_kg,
        product_to_freezer_kg=product_to_freezer_kg,
        ice_cream_volume_L=ice_cream_volume_L,
        total_wastewater_mass_kg=wastewater.mass_kg,
        total_bioplastic_mass_kg=pha_kg,
        total_energy_consumed_J=power_W,
        mass_balance_closed=mass_balance_closed,
        report_dict={k: v for k, v in report.items() if k != "typed_report"},
    )
    return report


def print_report(report: dict) -> None:
    """Print a human-readable report to stdout."""
    print("=" * 60)
    print("ICE CREAM MANUFACTURING & WASTEWATER VALORIZATION SIMULATOR")
    print("Full cycle report: Mixing → CIP → Filtration → Bioplastic")
    print("=" * 60)
    r = report
    inp = r.get("inputs", {})
    print("\n--- INPUTS ---")
    print(f"  Raw materials (kg):     {inp.get('raw_materials_kg', 0):.2f}")
    print(f"  Tank surface area (m²): {inp.get('tank_surface_area_m2', 0):.2f}")
    print(f"  Cleaning water (L):     {inp.get('cleaning_water_L', 0):.2f}")
    print(f"  Air overrun:            {inp.get('air_overrun', 0.5)}")
    print(f"  Interface flush (L):    {inp.get('interface_flush_L', 0):.2f}")
    print(f"  Include cleaning:      {inp.get('include_cleaning_phase', True)}")
    print(f"  Temperature (K):       {inp.get('temperature_K', 278):.1f}  RPM: {inp.get('rpm', 60)}")

    mix = r.get("mixer", {})
    print("\n--- MIXER ---")
    print(f"  Product to freezer (kg): {mix.get('product_to_freezer_kg', 0):.2f}")
    print(f"  Ice cream volume (L):    {mix.get('ice_cream_volume_L', 0):.2f}")
    print(f"  Tank residue (kg):       {mix.get('tank_residue_kg', 0):.2f}")
    print(f"  Interface flush (kg):    {mix.get('interface_flush_kg', 0):.2f}")
    print(f"  Mixing power (W):        {mix.get('mixing_power_W', 0):.2f}")
    print(f"  Viscosity (Pa·s):       {mix.get('viscosity_Pa_s', 0):.4f}")
    print(f"  Thermal cond. (W/(m·K)): {mix.get('thermal_conductivity_W_mK', 0):.3f}")
    print(f"  Specific heat (J/(kg·K)): {mix.get('specific_heat_J_kgK', 0):.0f}")
    print(f"  Mixer efficiency (%):    {mix.get('mixer_efficiency_pct', 0)}")

    cip = r.get("cip", {})
    print("\n--- CIP (Wastewater) ---")
    print(f"  Wastewater volume (L):   {cip.get('wastewater_volume_L', 0):.2f}")
    print(f"  Dissolved sugar (kg):    {cip.get('dissolved_sugar_kg', 0):.2f}")
    print(f"  TSS (mg/L):              {cip.get('tss_mg_L', 0)}")
    print(f"  BOD (mg/L):              {cip.get('bod_mg_L', 0)}")
    print(f"  FOG (mg/L):              {cip.get('fog_mg_L', 0)}")

    flt = r.get("filtration", {})
    print("\n--- FILTRATION ---")
    print(f"  Permeate volume (L):     {flt.get('permeate_volume_L', 0):.2f}")
    print(f"  Retentate mass (kg):     {flt.get('retentate_mass_kg', 0):.2f}")
    print(f"  Retentate sugar (kg):    {flt.get('retentate_sugar_kg', 0):.2f}")
    print(f"  Filter saturation (%):   {flt.get('filter_saturation_pct', 0)}")
    print(f"  Maintenance required:    {flt.get('maintenance_required', False)}")

    bio = r.get("bioconversion", {})
    print("\n--- BIOCONVERSION (Sugar → PHA) ---")
    print(f"  Bioplastic produced (kg): {bio.get('bioplastic_mass_kg', 0):.4f}")
    print(f"  Sugar consumed (kg):      {bio.get('sugar_consumed_kg', 0):.4f}")
    print(f"  Yield coefficient:       {bio.get('yield_coefficient', 0)}")
    print(f"  Yield from sugar (%):    {bio.get('plastic_yield_from_sugar_pct', 0)}")
    print(f"  Yield from input (%):    {bio.get('plastic_yield_from_input_pct', 0)}")

    eff = r.get("efficiency_summary", {})
    print("\n--- EFFICIENCY SUMMARY ---")
    print(f"  Product recovery (%):    {eff.get('product_recovery_pct', 0)}")
    print(f"  Plastic (kg/tonne input): {eff.get('plastic_kg_per_tonne_input', 0)}")
    print(f"  Maintenance required:    {eff.get('maintenance_required', False)}")
    print(f"  Mass balance closed:     {eff.get('mass_balance_closed', True)}")
    print("=" * 60)


if __name__ == "__main__":
    report = run_full_cycle()
    print_report(report)
