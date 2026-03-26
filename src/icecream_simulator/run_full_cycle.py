"""
Main execution: one full cycle
  Industrial chain (preparation → pasteurization → homogenization → cooling →
  ageing → freezer → hardening) → CIP → pre-filtration → hydrodynamic cavitation →
  filtration → bioplastic.
Mixing (blending) is only in the preparation stage; aeration (overrun) is in the freezer.
Supports optional on_stage_complete callback and pluggable bioconversion_model.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from icecream_simulator.schemas import RawMaterials, MassBalanceState, StageResult
from icecream_simulator.cip import CIPInput, run_cip
from icecream_simulator.prefiltration import PrefiltrationConfig, run_prefiltration
from icecream_simulator.cavitation import CavitationConfig, run_hydrodynamic_cavitation
from icecream_simulator.filtration import FiltrationConfig, run_filtration
from icecream_simulator.bioconversion import (
    BioconversionModelBase,
    DefaultBioconversionModel,
)
from icecream_simulator.batch_models import (
    WastewaterStream,
    MaterialBatchCycleReport,
)
from icecream_simulator.industrial_chain import run_industrial_chain
from icecream_simulator import industrial_physics as phys
from icecream_simulator import literature_recipes as lit
from icecream_simulator.crystallization_parameters import (
    DEFAULT_CRYSTALLIZATION_PARAMETERS,
    CrystallizationParameters,
)

# Mix density (kg/L) for volume and interface flush
MIX_DENSITY_KG_L = 1.05


def _thermal_properties_from_composition(water_fraction: float) -> tuple[float, float]:
    """Thermal conductivity (W/(m·K)) and specific heat (J/(kg·K)) from water fraction (parity with PIML)."""
    return (0.4 + 0.2 * water_fraction, 3500.0 + 500.0 * water_fraction)


def _quality_summary(stage_results: list[dict], product_metadata: dict) -> dict:
    """Aggregate key quality metrics from stage results and final product metadata."""
    out: dict = {}
    for s in stage_results:
        st = s.get("stage")
        if st == "pasteurization":
            out["log10_pathogen_reduction"] = s.get("log10_pathogen_reduction")
            out["d_value_minutes_at_hold_T"] = s.get("d_value_minutes_at_hold_T")
        elif st == "homogenization":
            out["fat_globule_d32_um"] = s.get("fat_globule_d32_um")
        elif st == "ageing_vat":
            out["fat_crystallinity_fraction"] = s.get("fat_crystallinity_fraction")
        elif st == "freezer":
            out["air_overrun_effective"] = s.get("air_overrun_effective")
            out["ice_crystal_wall_um"] = s.get("ice_crystal_wall_um")
            out["ice_crystal_bulk_um"] = s.get("ice_crystal_bulk_um")
            out["ice_crystal_volume_mean_um"] = s.get("ice_crystal_volume_mean_um")
            out["ice_crystal_primary_um"] = s.get("ice_crystal_primary_um")
            out["ice_crystal_mean_um"] = s.get("ice_crystal_mean_um")
            out["gompertz_frozen_water_fraction"] = s.get("gompertz_frozen_water_fraction")
            out["avrami_frozen_water_fraction"] = s.get("avrami_frozen_water_fraction")
            out["frozen_water_fraction_kinetic_blend"] = s.get("frozen_water_fraction_kinetic_blend")
            out["initial_freezing_point_mix_C"] = s.get("initial_freezing_point_mix_C")
            out["kelvin_freezing_point_depression_for_mean_crystal_K"] = s.get(
                "kelvin_freezing_point_depression_for_mean_crystal_K"
            )
            out["dasher_shaft_power_W"] = s.get("dasher_shaft_power_W")
            out["crystallization_parameters_name"] = s.get("crystallization_parameters_name")
        elif st == "storage_recrystallization":
            out["storage_time_s"] = s.get("storage_time_s")
            out["storage_temp_K"] = s.get("storage_temp_K")
            out["ice_crystal_mean_um_before_storage"] = s.get("ice_crystal_mean_um_before_storage")
            out["ice_crystal_mean_um"] = s.get("ice_crystal_mean_um")
            out["kelvin_freezing_point_depression_for_mean_crystal_K"] = s.get(
                "kelvin_freezing_point_depression_for_mean_crystal_K"
            )
            out["hardness_proxy_kPa"] = s.get("hardness_proxy_kPa")
            out["melt_rate_proxy_per_s"] = s.get("melt_rate_proxy_per_s")
        elif st == "packaging":
            out["package_count"] = s.get("package_count")
            out["net_mass_kg_per_package"] = s.get("net_mass_kg_per_package")
    out["hardness_proxy_kPa"] = product_metadata.get("hardness_proxy_kPa")
    out["melt_rate_proxy_per_s"] = product_metadata.get("melt_rate_proxy_per_s")
    return out


def run_full_cycle(
    raw_materials: Optional[RawMaterials] = None,
    literature_preset_id: Optional[str] = None,
    tank_surface_area_m2: float = 10.0,
    water_volume_L: float = 80.0,
    bioplastic_yield_coefficient: float = 0.4,
    bioconversion_model: Optional[BioconversionModelBase] = None,
    on_stage_complete: Optional[Callable[[str, StageResult, dict], None]] = None,
    air_overrun: float = 0.5,
    interface_flush_L: float = 5.0,
    include_cleaning_phase: bool = True,
    homogenization_pressure_bar: float = 200.0,
    stirrer_on: bool = True,
    jacket_flow_L_min: float = 20.0,
    preparation_rpm: float = 60.0,
    preparation_mixing_time_s: float = 300.0,
    pasteurization_hold_time_s: float = 15.0,
    flavor_syrup_mass_kg: float = 0.0,
    inclusion_mass_kg: float = 0.0,
    coolant_temp_K: float = 253.15,
    freezer_residence_time_s: float = 45.0,
    dasher_rpm: float = 55.0,
    barrel_diameter_m: float = 0.15,
    package_count: int = 1,
    volume_fraction_wall_ice: float = 0.28,
    storage_time_s: float = 0.0,
    storage_temp_K: float = 248.15,
    crystallization_parameters: Optional[CrystallizationParameters] = None,
) -> dict:
    """
    Run one full cycle: Industrial chain (preparation through packaging) → CIP →
    Pre-filtration → Hydrodynamic cavitation → Filtration → Bioconversion when
    include_cleaning_phase and wastewater volume > 0.

    Returns a report dict with efficiency, plastic yield, mass_balance_closed,
    and per-stage industrial_chain details.

    Args:
        raw_materials: Input recipe; default 200 kg batch if None. Ignored when
            ``literature_preset_id`` is set (preset supplies recipe and optional flavor).
        literature_preset_id: If set, load ``RawMaterials`` and optional flavor/inclusion
            masses from ``literature_recipes.LITERATURE_PRESETS`` (see module docstring).
        tank_surface_area_m2: Tank surface for residue (preparation + ageing).
        water_volume_L: CIP water volume (when include_cleaning_phase=True).
        bioplastic_yield_coefficient: Used only if bioconversion_model is None.
        bioconversion_model: Pluggable bioconversion; DefaultBioconversionModel if None.
        on_stage_complete: Optional callback (stage_name, StageResult, cumulative).
        air_overrun: Requested overrun fraction; freezer applies effective overrun.
        interface_flush_L: Start-of-run discard (L); added to CIP feed.
        include_cleaning_phase: If False, skip CIP/filtration/bioconversion.
        homogenization_pressure_bar: Homogenizer pressure (e.g. 150–250 bar).
        stirrer_on: Ageing vat stirrer on (reduces wall residue).
        jacket_flow_L_min: Ageing vat cooling jacket flow (L/min).
        preparation_rpm: Preparation mix agitator RPM.
        preparation_mixing_time_s: Preparation mix duration (s).
        pasteurization_hold_time_s: Isothermal hold at pasteurization outlet (s).
        flavor_syrup_mass_kg: Flavor syrup mass added after ageing (kg).
        inclusion_mass_kg: Particulate inclusions mass (kg).
        coolant_temp_K: SSHE evaporator / coolant temperature (K).
        freezer_residence_time_s: Mean residence time in continuous freezer (s).
        dasher_rpm: Dasher rotational speed.
        barrel_diameter_m: SSHE barrel diameter for power scaling (m).
        package_count: Number of packages for mass allocation.
        volume_fraction_wall_ice: Volume fraction of ice attributed to wall nucleation in SSHE
            (Cook & Hartel; used in wall/bulk volume mean).
        storage_time_s: Post-hardening storage duration for Ostwald ripening (0 skips).
        storage_temp_K: Storage temperature (K) for recrystallization step.
        crystallization_parameters: Optional tuned coefficients for ice kinetics, wall/bulk
            SSHE, storage ripening, Kelvin, and hardness (defaults match built-in physics).
    """
    preset_meta: dict = {}
    if literature_preset_id:
        preset = lit.get_preset(literature_preset_id)
        raw = preset.raw_materials
        flavor_syrup_mass_kg = preset.flavor_syrup_mass_kg
        inclusion_mass_kg = preset.inclusion_mass_kg
        preset_meta = {
            "literature_preset_id": preset.id,
            "literature_citation": preset.citation,
            "literature_paper_pdf": preset.paper_pdf,
            "literature_table_or_section": preset.table_or_section,
            "literature_notes": preset.notes,
        }
    else:
        raw = raw_materials or RawMaterials(
            milk=100.0,
            cream=30.0,
            sugar=25.0,
            stabilizers=1.65,
            emulsifiers_kg=0.35,
            water=43.0,
        )
    total_input_kg = raw.total_mass + max(0.0, flavor_syrup_mass_kg) + max(0.0, inclusion_mass_kg)
    bioconv_impl = bioconversion_model or DefaultBioconversionModel(
        yield_coefficient=bioplastic_yield_coefficient
    )
    cumulative: dict = {"product_kg": 0.0, "energy_consumed": 0.0}
    cparams = crystallization_parameters or DEFAULT_CRYSTALLIZATION_PARAMETERS

    # Industrial chain only: preparation (mixing) → pasteurization → homogenization →
    # cooling → ageing → freezer (aeration) → hardening
    final_product, _batch_after_ageing, cip_residue, ice_cream_volume_L, power_W, stage_results = run_industrial_chain(
        raw,
        tank_surface_area_m2=tank_surface_area_m2,
        homogenization_pressure_bar=homogenization_pressure_bar,
        air_overrun=air_overrun,
        interface_flush_L=interface_flush_L,
        stirrer_on=stirrer_on,
        jacket_flow_L_min=jacket_flow_L_min,
        preparation_rpm=preparation_rpm,
        preparation_mixing_time_s=preparation_mixing_time_s,
        pasteurization_hold_time_s=pasteurization_hold_time_s,
        flavor_syrup_mass_kg=flavor_syrup_mass_kg,
        inclusion_mass_kg=inclusion_mass_kg,
        coolant_temp_K=coolant_temp_K,
        freezer_residence_time_s=freezer_residence_time_s,
        dasher_rpm=dasher_rpm,
        barrel_diameter_m=barrel_diameter_m,
        package_count=package_count,
        volume_fraction_wall_ice=volume_fraction_wall_ice,
        storage_time_s=storage_time_s,
        storage_temp_K=storage_temp_K,
        crystallization_parameters=cparams,
    )
    product_to_freezer_kg = final_product.mass_kg
    residue_kg = cip_residue.metadata.get("prep_kg", 0) + cip_residue.metadata.get("ageing_kg", 0)
    interface_flush_kg = cip_residue.metadata.get("interface_flush_kg", 0)
    product_batch = final_product
    mixer_efficiency = (product_to_freezer_kg / total_input_kg * 100.0) if total_input_kg > 0 else 0.0
    cumulative["product_kg"] = product_to_freezer_kg
    cumulative["energy_consumed"] = power_W
    thermal_conductivity, _ = _thermal_properties_from_composition(product_batch.composition.water)
    specific_heat = phys.specific_heat_mix_J_kgK(product_batch.composition)
    if on_stage_complete:
        mb = MassBalanceState(
            stage="industrial_chain",
            mass_in=total_input_kg,
            mass_out=product_to_freezer_kg + cip_residue.mass_kg,
            energy_consumed=power_W,
            mass_product=product_to_freezer_kg,
            mass_waste=cip_residue.mass_kg,
            metadata={
                "viscosity": product_batch.viscosity_Pa_s,
                "homogenization_pressure_bar": homogenization_pressure_bar,
                "stirrer_on": stirrer_on,
                "ice_cream_volume_L": ice_cream_volume_L,
                "stage_results": stage_results,
            },
        )
        on_stage_complete(
            "industrial_chain",
            StageResult(
                stage_name="industrial_chain",
                mass_balance=mb,
                outputs={
                    "product_to_freezer_kg": product_to_freezer_kg,
                    "ice_cream_volume_L": ice_cream_volume_L,
                    "tank_residue_kg": residue_kg,
                    "interface_flush_kg": interface_flush_kg,
                    "preparation_power_W": power_W,
                    "stages": [s["stage"] for s in stage_results],
                    "stage_results": stage_results,
                },
                model_used="IndustrialChain",
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

    cip_wastewater_snapshot = wastewater

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

    prefiltration_report: dict = {}
    cavitation_report: dict = {}
    bioavailability_factor = 1.0
    if include_cleaning_phase and wastewater.volume_L > 1e-9:
        wastewater_pre_pref = wastewater
        wastewater, prefiltration_report = run_prefiltration(
            wastewater, config=PrefiltrationConfig()
        )
        wastewater_pre_cav = wastewater
        wastewater, cavitation_report = run_hydrodynamic_cavitation(
            wastewater, config=CavitationConfig()
        )
        bioavailability_factor = float(cavitation_report.get("bioavailability_factor", 1.0))

        if on_stage_complete:
            tss_removed = float(prefiltration_report.get("tss_removed_kg", 0.0))
            mb_pre = MassBalanceState(
                stage="prefiltration",
                mass_in=wastewater_pre_pref.mass_kg,
                mass_out=wastewater.mass_kg + tss_removed,
                energy_consumed=0.0,
                mass_product=wastewater.mass_kg,
                mass_waste=tss_removed,
                metadata=prefiltration_report,
            )
            on_stage_complete(
                "prefiltration",
                StageResult(
                    stage_name="prefiltration",
                    mass_balance=mb_pre,
                    outputs=prefiltration_report,
                    model_used="Prefiltration",
                ),
                dict(cumulative),
            )
            mb_cav = MassBalanceState(
                stage="hydrodynamic_cavitation",
                mass_in=wastewater_pre_cav.mass_kg,
                mass_out=wastewater.mass_kg,
                energy_consumed=cavitation_report.get("energy_proxy_kwh", 0.0) * 3.6e6,
                mass_product=wastewater.mass_kg,
                mass_waste=0.0,
                metadata=cavitation_report,
            )
            on_stage_complete(
                "hydrodynamic_cavitation",
                StageResult(
                    stage_name="hydrodynamic_cavitation",
                    mass_balance=mb_cav,
                    outputs=cavitation_report,
                    model_used="HydrodynamicCavitation",
                ),
                dict(cumulative),
            )

    # --- Filtration (after CIP + optional prefiltration + cavitation) ---
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
    bioplastic_out = bioconv_impl.run(
        retentate, bioavailability_factor=bioavailability_factor
    )
    pha_kg = bioplastic_out.mass_kg
    sugar_for_plastic_kg = bioplastic_out.sugar_consumed_kg
    plastic_yield_from_sugar = (
        (pha_kg / sugar_for_plastic_kg * 100.0) if sugar_for_plastic_kg > 0 else 0.0
    )
    plastic_yield_from_total_input = (pha_kg / total_input_kg * 100.0) if total_input_kg > 0 else 0.0

    # Mass balance: raw + flavor + inclusions = packaged product + prep residue + ageing residue + interface flush.
    total_out_kg = product_to_freezer_kg + cip_residue.mass_kg
    mass_balance_closed = abs(total_input_kg - total_out_kg) < 1e-5

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
                "cavitation_bioavailability_factor": bioavailability_factor,
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
            **preset_meta,
            "raw_materials_kg": raw.total_mass,
            "total_mass_including_additives_kg": total_input_kg,
            "tank_surface_area_m2": tank_surface_area_m2,
            "cleaning_water_L": water_volume_L if include_cleaning_phase else 0.0,
            "air_overrun": air_overrun,
            "interface_flush_L": interface_flush_L,
            "include_cleaning_phase": include_cleaning_phase,
            "homogenization_pressure_bar": homogenization_pressure_bar,
            "stirrer_on": stirrer_on,
            "jacket_flow_L_min": jacket_flow_L_min,
            "preparation_rpm": preparation_rpm,
            "preparation_mixing_time_s": preparation_mixing_time_s,
            "pasteurization_hold_time_s": pasteurization_hold_time_s,
            "flavor_syrup_mass_kg": flavor_syrup_mass_kg,
            "inclusion_mass_kg": inclusion_mass_kg,
            "coolant_temp_K": coolant_temp_K,
            "freezer_residence_time_s": freezer_residence_time_s,
            "dasher_rpm": dasher_rpm,
            "barrel_diameter_m": barrel_diameter_m,
            "package_count": package_count,
            "volume_fraction_wall_ice": volume_fraction_wall_ice,
            "storage_time_s": storage_time_s,
            "storage_temp_K": storage_temp_K,
            "crystallization_parameters_name": cparams.name,
            "crystallization_parameters": cparams.model_dump(),
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
        "industrial_chain": {
            "stages": [s["stage"] for s in stage_results],
            "stages_detail": stage_results,
            "homogenization_pressure_bar": homogenization_pressure_bar,
            "stirrer_on": stirrer_on,
            "jacket_flow_L_min": jacket_flow_L_min,
        },
        "cip": {
            "wastewater_volume_L": cip_wastewater_snapshot.volume_L,
            "wastewater_mass_kg": cip_wastewater_snapshot.mass_kg,
            "dissolved_sugar_kg": cip_wastewater_snapshot.dissolved_sugar_kg,
            "tss_mg_L": round(cip_wastewater_snapshot.tss_mg_L, 2),
            "bod_mg_L": round(cip_wastewater_snapshot.bod_mg_L, 2),
            "fog_mg_L": round(cip_wastewater_snapshot.fog_mg_L, 2),
        },
        "prefiltration": prefiltration_report if prefiltration_report else None,
        "hydrodynamic_cavitation": cavitation_report if cavitation_report else None,
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
            "cavitation_bioavailability_factor": bioavailability_factor,
            "plastic_yield_from_sugar_pct": round(plastic_yield_from_sugar, 2),
            "plastic_yield_from_input_pct": round(plastic_yield_from_total_input, 4),
        },
        "wastewater_to_nanofiltration": {
            "volume_L": wastewater.volume_L,
            "tss_mg_L": round(wastewater.tss_mg_L, 2),
            "cod_mg_L": round(wastewater.cod_mg_L, 2),
            "bod_mg_L": round(wastewater.bod_mg_L, 2),
            "fog_mg_L": round(wastewater.fog_mg_L, 2),
        },
        "efficiency_summary": {
            "product_recovery_pct": round(mixer_efficiency, 2),
            "plastic_kg_per_tonne_input": round(
                pha_kg / (total_input_kg / 1000.0), 4
            ) if total_input_kg > 0 else 0.0,
            "maintenance_required": maintenance_flag,
            "mass_balance_closed": mass_balance_closed,
        },
        "quality": _quality_summary(stage_results, product_batch.metadata),
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
    print("Full cycle: Industrial chain → CIP → Prefiltration → Cavitation → Filtration → Bioplastic")
    print("(Mixing at start in preparation; aeration in freezer)")
    print("=" * 60)
    r = report
    inp = r.get("inputs", {})
    print("\n--- INPUTS ---")
    print(f"  Raw materials (kg):     {inp.get('raw_materials_kg', 0):.2f}")
    print(f"  Tank surface area (m²): {inp.get('tank_surface_area_m2', 0):.2f}")
    print(f"  Cleaning water (L):     {inp.get('cleaning_water_L', 0):.2f}")
    print(f"  Air overrun (freezer):  {inp.get('air_overrun', 0.5)}")
    print(f"  Interface flush (L):   {inp.get('interface_flush_L', 0):.2f}")
    print(f"  Include cleaning:      {inp.get('include_cleaning_phase', True)}")
    print(f"  Homogenization (bar):  {inp.get('homogenization_pressure_bar')}  Stirrer: {inp.get('stirrer_on')}  Jacket (L/min): {inp.get('jacket_flow_L_min')}")
    print(f"  Preparation: RPM {inp.get('preparation_rpm')}  time {inp.get('preparation_mixing_time_s')} s")
    print(f"  Pasteurization hold:     {inp.get('pasteurization_hold_time_s')} s")
    print(f"  SSHE: coolant {inp.get('coolant_temp_K')} K  residence {inp.get('freezer_residence_time_s')} s  dasher {inp.get('dasher_rpm')} rpm  barrel {inp.get('barrel_diameter_m')} m")
    print(
        f"  Wall ice vol. frac.:      {inp.get('volume_fraction_wall_ice')}  "
        f"storage {inp.get('storage_time_s')} s @ {inp.get('storage_temp_K')} K"
    )
    print(f"  Packages:                 {inp.get('package_count')}  flavor {inp.get('flavor_syrup_mass_kg')} kg  inclusions {inp.get('inclusion_mass_kg')} kg")
    if inp.get("literature_preset_id"):
        print(f"  Literature preset:        {inp.get('literature_preset_id')}")
        cit = inp.get("literature_citation") or ""
        if len(cit) > 100:
            print(f"  Citation:                 {cit[:100]}…")
        else:
            print(f"  Citation:                 {cit}")

    mix = r.get("mixer", {})
    print("\n--- INDUSTRIAL CHAIN (product out) ---")
    print(f"  Product to freezer (kg): {mix.get('product_to_freezer_kg', 0):.2f}")
    print(f"  Ice cream volume (L):    {mix.get('ice_cream_volume_L', 0):.2f}")
    print(f"  Tank residue (kg):       {mix.get('tank_residue_kg', 0):.2f}")
    print(f"  Interface flush (kg):    {mix.get('interface_flush_kg', 0):.2f}")
    print(f"  Mixing power (W):        {mix.get('mixing_power_W', 0):.2f}")
    print(f"  Viscosity (Pa·s):       {mix.get('viscosity_Pa_s', 0):.4f}")
    print(f"  Thermal cond. (W/(m·K)): {mix.get('thermal_conductivity_W_mK', 0):.3f}")
    print(f"  Specific heat (J/(kg·K)): {mix.get('specific_heat_J_kgK', 0):.0f}")
    print(f"  Mixer efficiency (%):    {mix.get('mixer_efficiency_pct', 0)}")

    q = r.get("quality", {})
    if q:
        print("\n--- QUALITY (physics-based) ---")
        if q.get("log10_pathogen_reduction") is not None:
            print(f"  Log10 pathogen reduction:  {q.get('log10_pathogen_reduction'):.3f}")
        if q.get("fat_globule_d32_um") is not None:
            print(f"  Fat globule d32 (µm):       {q.get('fat_globule_d32_um'):.4f}")
        if q.get("fat_crystallinity_fraction") is not None:
            print(f"  Fat crystallinity:         {q.get('fat_crystallinity_fraction'):.4f}")
        if q.get("ice_crystal_wall_um") is not None:
            print(f"  Ice crystal wall (µm):       {q.get('ice_crystal_wall_um'):.2f}")
        if q.get("ice_crystal_bulk_um") is not None:
            print(f"  Ice crystal bulk (µm):       {q.get('ice_crystal_bulk_um'):.2f}")
        if q.get("ice_crystal_volume_mean_um") is not None:
            print(f"  Ice vol.-mean d (µm):        {q.get('ice_crystal_volume_mean_um'):.2f}")
        if q.get("ice_crystal_primary_um") is not None:
            print(f"  Ice crystal primary (µm):    {q.get('ice_crystal_primary_um'):.2f}")
        if q.get("ice_crystal_mean_um") is not None:
            print(f"  Ice crystal mean (µm):       {q.get('ice_crystal_mean_um'):.2f}")
        if q.get("gompertz_frozen_water_fraction") is not None:
            print(f"  Gompertz frozen H2O frac:   {q.get('gompertz_frozen_water_fraction'):.4f}")
        if q.get("avrami_frozen_water_fraction") is not None:
            print(f"  Avrami frozen H2O frac:     {q.get('avrami_frozen_water_fraction'):.4f}")
        if q.get("frozen_water_fraction_kinetic_blend") is not None:
            print(f"  Kinetic blend (G+A)/2:      {q.get('frozen_water_fraction_kinetic_blend'):.4f}")
        if q.get("storage_time_s"):
            print(
                f"  Storage:                     {q.get('storage_time_s')} s, "
                f"crystal before storage (µm): {q.get('ice_crystal_mean_um_before_storage')}"
            )
        if q.get("initial_freezing_point_mix_C") is not None:
            print(f"  Initial freezing pt mix (°C): {q.get('initial_freezing_point_mix_C'):.3f}")
        if q.get("kelvin_freezing_point_depression_for_mean_crystal_K") is not None:
            print(
                "  Kelvin ΔT mean crystal (K): "
                f"{q.get('kelvin_freezing_point_depression_for_mean_crystal_K'):.6f}"
            )
        if q.get("air_overrun_effective") is not None:
            print(f"  Overrun effective:         {q.get('air_overrun_effective'):.4f}")
        if q.get("dasher_shaft_power_W") is not None:
            print(f"  Dasher shaft power (W):    {q.get('dasher_shaft_power_W'):.4f}")
        if q.get("hardness_proxy_kPa") is not None:
            print(f"  Hardness proxy (kPa):      {q.get('hardness_proxy_kPa'):.2f}")
        if q.get("melt_rate_proxy_per_s") is not None:
            print(f"  Melt rate proxy (1/s):     {q.get('melt_rate_proxy_per_s'):.6f}")

    cip = r.get("cip", {})
    print("\n--- CIP (Wastewater) ---")
    print(f"  Wastewater volume (L):   {cip.get('wastewater_volume_L', 0):.2f}")
    print(f"  Dissolved sugar (kg):    {cip.get('dissolved_sugar_kg', 0):.2f}")
    print(f"  TSS (mg/L):              {cip.get('tss_mg_L', 0)}")
    print(f"  BOD (mg/L):              {cip.get('bod_mg_L', 0)}")
    print(f"  FOG (mg/L):              {cip.get('fog_mg_L', 0)}")

    pre = r.get("prefiltration")
    if pre:
        print("\n--- PREFILTRATION ---")
        print(f"  TSS before (mg/L):       {pre.get('tss_mg_L_before', 0)}")
        print(f"  TSS after (mg/L):        {pre.get('tss_mg_L_after', 0)}")
        print(f"  TSS removed (kg):        {pre.get('tss_removed_kg', 0):.4f}")

    cav = r.get("hydrodynamic_cavitation")
    if cav:
        print("\n--- HYDRODYNAMIC CAVITATION ---")
        print(f"  COD before / after (mg/L): {cav.get('cod_mg_L_before')} → {cav.get('cod_mg_L_after')}")
        print(f"  BOD before / after (mg/L): {cav.get('bod_mg_L_before')} → {cav.get('bod_mg_L_after')}")
        print(f"  Mean MW index (after):   {cav.get('mean_mw_index_after', 0):.3f}")
        print(f"  Bioavailability factor:  {cav.get('bioavailability_factor', 1.0):.3f}")
        print(f"  Energy proxy (kWh):      {cav.get('energy_proxy_kwh', 0):.4f}")

    wtn = r.get("wastewater_to_nanofiltration", {})
    if wtn:
        print("\n--- TO NANOFILTRATION (after HC) ---")
        print(f"  TSS (mg/L):              {wtn.get('tss_mg_L')}")
        print(f"  COD (mg/L):              {wtn.get('cod_mg_L')}")
        print(f"  BOD (mg/L):              {wtn.get('bod_mg_L')}")

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
    if bio.get("cavitation_bioavailability_factor") is not None:
        print(f"  Cavitation bioavail.:    {bio.get('cavitation_bioavailability_factor')}")
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
