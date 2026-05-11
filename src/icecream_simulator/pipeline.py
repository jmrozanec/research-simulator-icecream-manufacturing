"""
Simplified ice-cream production + CIP wastewater + filtration + bioplastic pipeline.

~10 closed-form steps; see docs/SIMPLIFIED_PIPELINE_REPORT.md for symbols and assumptions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from icecream_simulator import constants as C
from icecream_simulator.domain import (
    BioplasticOutput,
    Composition,
    FilterState,
    LiteratureRecipePreset,
    MassBalanceState,
    MaterialBatchCycleReport,
    PermeateStream,
    RawMaterials,
    RetentateStream,
    StageResult,
    TankResidue,
    WastewaterStream,
)

# --- Literature presets (compact) ---
LITERATURE_PRESETS: dict[str, LiteratureRecipePreset] = {
    "HARFOUSH_2024_BASELINE": LiteratureRecipePreset(
        id="HARFOUSH_2024_BASELINE",
        citation="Harfoush et al. (baseline mix; illustrative).",
        raw_materials=RawMaterials(
            milk=56.0,
            cream=14.0,
            sugar=15.0,
            stabilizers=0.4,
            emulsifiers_kg=0.3,
            water=14.3,
            cocoa_powder_kg=0.0,
            egg_yolk_kg=0.0,
            vanilla_extract_kg=0.0,
            vanillin_kg=0.0,
        ),
    ),
    "GIUDICI_2021_INDUSTRIAL": LiteratureRecipePreset(
        id="GIUDICI_2021_INDUSTRIAL",
        citation="Giudici et al. — industrial-style recipe (illustrative).",
        raw_materials=RawMaterials(
            milk=120.0,
            cream=40.0,
            sugar=30.0,
            stabilizers=2.0,
            emulsifiers_kg=0.8,
            water=17.2,
            cocoa_powder_kg=0.0,
            egg_yolk_kg=0.0,
            vanilla_extract_kg=0.0,
            vanillin_kg=0.0,
        ),
    ),
    "KONSTANTAS_2019_VANILLA_PREMIUM": LiteratureRecipePreset(
        id="KONSTANTAS_2019_VANILLA_PREMIUM",
        citation="Konstantas et al. — premium vanilla (illustrative).",
        raw_materials=RawMaterials(
            milk=49.1,
            cream=13.0,
            sugar=15.0,
            stabilizers=0.41,
            emulsifiers_kg=0.49,
            water=11.84,
            egg_yolk_kg=1.65,
            vanilla_extract_kg=0.33,
            vanillin_kg=0.03,
            cocoa_powder_kg=0.0,
        ),
        flavor_syrup_mass_kg=0.0,
        inclusion_mass_kg=0.0,
    ),
}


def list_preset_ids() -> list[str]:
    return sorted(LITERATURE_PRESETS.keys())


def get_preset(preset_id: str) -> LiteratureRecipePreset:
    if preset_id not in LITERATURE_PRESETS:
        raise KeyError(f"Unknown preset {preset_id!r}; valid: {list_preset_ids()}")
    return LITERATURE_PRESETS[preset_id]


def composition_from_raw_materials(rm: RawMaterials) -> tuple[float, float, float, float]:
    """Return mass fractions (fat, sugar, water, solids) — Formula (2) in report."""
    total = rm.total_mass
    if total <= 0:
        return 0.0, 0.0, 0.0, 0.0
    egg_fat = rm.egg_yolk_kg * C.EGG_YOLK_FAT_FRACTION
    egg_solid = rm.egg_yolk_kg * C.EGG_YOLK_SOLIDS_FRACTION
    egg_water = rm.egg_yolk_kg * C.EGG_YOLK_WATER_FRACTION
    ve_water = rm.vanilla_extract_kg * C.VANILLA_EXTRACT_WATER_FRACTION
    ve_solid = rm.vanilla_extract_kg * C.VANILLA_EXTRACT_SOLIDS_FRACTION
    fat_mass = rm.milk * C.MILK_FAT_FRACTION + rm.cream * C.CREAM_FAT_FRACTION + egg_fat
    solids_mass = (
        rm.milk * C.MILK_MSNF_FRACTION
        + rm.stabilizers
        + rm.emulsifiers_kg
        + rm.cocoa_powder_kg
        + egg_solid
        + ve_solid
        + rm.vanillin_kg
    )
    water_mass = rm.water + egg_water + ve_water
    sugar_mass = rm.sugar
    return (
        fat_mass / total,
        sugar_mass / total,
        water_mass / total,
        solids_mass / total,
    )


def wash_efficiency(detergent_type: str) -> float:
    return C.WASH_EFFICIENCY.get(detergent_type.lower(), C.WASH_EFFICIENCY_DEFAULT)


def run_cip_wastewater(
    residue: TankResidue,
    water_volume_L: float,
    water_temperature_K: float,
    detergent_type: str,
) -> WastewaterStream:
    """CIP dilution model — Formulas (4)–(7)."""
    water_L = max(0.0, water_volume_L)
    water_mass_kg = water_L * C.WATER_DENSITY_KG_L
    eff = wash_efficiency(detergent_type)
    residue_into_water_kg = residue.mass_kg * eff
    w_fat = residue.composition.fat
    w_sugar = residue.composition.sugar
    w_water = residue.composition.water
    dissolved_sugar_kg = residue_into_water_kg * w_sugar
    solids_kg = residue_into_water_kg * (1.0 - w_water)
    total_mass_kg = water_mass_kg + residue_into_water_kg
    total_volume_L = water_L + residue_into_water_kg / C.WATER_DENSITY_KG_L
    if total_volume_L <= 0:
        total_volume_L = C.VOLUME_EPS_L
    tss_mg_L = (solids_kg * C.MG_PER_KG) / total_volume_L
    bod_kg = dissolved_sugar_kg * C.BOD_SUGAR_COEFFICIENT + residue_into_water_kg * w_fat * C.BOD_FAT_COEFFICIENT
    cod_kg = bod_kg * C.COD_TO_BOD_RATIO
    bod_mg_L = (bod_kg * C.MG_PER_KG) / total_volume_L
    cod_mg_L = (cod_kg * C.MG_PER_KG) / total_volume_L
    fat_into_water_kg = residue_into_water_kg * w_fat
    fog_mg_L = (fat_into_water_kg * C.MG_PER_KG) / total_volume_L if total_volume_L > 0 else 0.0
    return WastewaterStream(
        volume_L=total_volume_L,
        mass_kg=total_mass_kg,
        temperature_K=water_temperature_K,
        tss_mg_L=tss_mg_L,
        dissolved_sugar_kg=dissolved_sugar_kg,
        cod_mg_L=cod_mg_L,
        bod_mg_L=bod_mg_L,
        fog_mg_L=fog_mg_L,
        metadata={"wash_efficiency": eff, "detergent": detergent_type},
    )


def run_prefiltration(ww: WastewaterStream, removal_fraction: float) -> tuple[WastewaterStream, dict[str, float]]:
    """Formula (8)."""
    r = max(0.0, min(1.0, removal_fraction))
    tss_new = ww.tss_mg_L * (1.0 - r)
    tss_removed_kg = (ww.tss_mg_L - tss_new) * C.KG_PER_MG * ww.volume_L
    out = ww.model_copy(update={"tss_mg_L": tss_new})
    return out, {"tss_removed_kg": tss_removed_kg, "removal_fraction": r}


def run_cavitation_simplified(ww: WastewaterStream) -> tuple[WastewaterStream, float, dict[str, float]]:
    """Formula (9)."""
    p_in = C.CAVITATION_INLET_PRESSURE_BAR
    p_t = C.CAVITATION_THROAT_PRESSURE_BAR
    p_ref = max(C.VOLUME_EPS_L, C.CAVITATION_PRESSURE_REF_BAR)
    intensity = min(1.0, max(0.0, (p_in - p_t) / p_ref))
    f_bod = intensity * C.CAVITATION_BOD_REMOVAL_MAX
    f_cod = intensity * C.CAVITATION_COD_REMOVAL_MAX
    bod_new = ww.bod_mg_L * (1.0 - f_bod)
    cod_new = ww.cod_mg_L * (1.0 - f_cod)
    bioavailability = 1.0 + C.CAVITATION_BIOAVAILABILITY_GAIN * intensity
    out = ww.model_copy(update={"bod_mg_L": bod_new, "cod_mg_L": cod_new})
    meta = {
        "intensity": intensity,
        "bioavailability_factor": bioavailability,
        "bod_removal_fraction": f_bod,
        "cod_removal_fraction": f_cod,
    }
    return out, bioavailability, meta


def saturation_fraction(mass_acc: float, max_mass: float) -> float:
    if max_mass <= 0:
        return 0.0
    return min(1.0, mass_acc / max_mass)


def darcy_R(R_base: float, mass_acc: float, k_f: float) -> float:
    return R_base + k_f * mass_acc


def run_filtration(
    ww: WastewaterStream,
    initial_filter_state: Optional[FilterState] = None,
) -> tuple[PermeateStream, RetentateStream, FilterState]:
    """Formula (10)."""
    state = initial_filter_state or FilterState()
    fv_p = C.PERMEATE_VOLUME_FRACTION
    fv_r = 1.0 - fv_p
    permeate_volume_L = ww.volume_L * fv_p
    retentate_mass_kg = ww.mass_kg * fv_r
    permeate_mass_kg = ww.mass_kg * fv_p
    sugar_r = ww.dissolved_sugar_kg * C.SUGAR_FRACTION_TO_RETENTATE
    total_solids_kg = ww.tss_mg_L * C.KG_PER_MG * ww.volume_L
    solids_r = total_solids_kg * C.SOLIDS_REJECTION_TO_RETENTATE
    solids_frac = (solids_r / retentate_mass_kg) if retentate_mass_kg > 0 else 0.0

    new_acc = state.mass_accumulated_kg + retentate_mass_kg * C.FILTER_FOULING_MASS_FRACTION
    sat = saturation_fraction(new_acc, C.FILTER_MAX_ACCUMULATED_MASS_KG)
    maintenance = sat >= C.FILTER_SATURATION_MAINTENANCE_THRESHOLD
    r_val = darcy_R(C.FILTER_BASE_RESISTANCE_M_1, new_acc, C.FILTER_FOULING_COEFFICIENT)
    new_state = FilterState(
        mass_accumulated_kg=new_acc,
        saturation_fraction=sat,
        maintenance_required=maintenance,
        metadata={"resistance_m_1": r_val},
    )
    permeate = PermeateStream(
        volume_L=permeate_volume_L,
        mass_kg=permeate_mass_kg,
        tss_mg_L=ww.tss_mg_L * C.PERMEATE_TSS_PASSAGE,
    )
    retentate = RetentateStream(
        mass_kg=retentate_mass_kg,
        sugar_mass_kg=sugar_r,
        solids_fraction=min(1.0, solids_frac),
    )
    return permeate, retentate, new_state


def run_bioconversion(
    retentate: RetentateStream, yield_coefficient: float, bioavailability: float
) -> BioplasticOutput:
    """Formula (11)."""
    sugar_kg = retentate.sugar_mass_kg
    pha_kg = sugar_kg * yield_coefficient * bioavailability
    y_eff = yield_coefficient * bioavailability
    return BioplasticOutput(
        mass_kg=pha_kg,
        sugar_consumed_kg=sugar_kg,
        yield_coefficient=y_eff,
        metadata={"pathway": "PHA", "retentate_mass_kg": retentate.mass_kg},
    )


def run_literature_suite(*, include_cleaning_phase: bool = True) -> list[dict[str, Any]]:
    rows = []
    for pid in list_preset_ids():
        r = run_full_cycle(literature_preset_id=pid, include_cleaning_phase=include_cleaning_phase)
        rows.append(
            {
                "preset_id": pid,
                "product_kg": r["production"]["product_mass_kg"],
                "bioplastic_kg": r["bioconversion"]["bioplastic_mass_kg"],
                "mass_balance_closed": r["summary"]["mass_balance_closed"],
            }
        )
    return rows


def run_full_cycle(
    raw_materials: Optional[RawMaterials] = None,
    literature_preset_id: Optional[str] = None,
    residue_mass_fraction: float = C.DEFAULT_RESIDUE_MASS_FRACTION,
    flavor_syrup_mass_kg: float = 0.0,
    inclusion_mass_kg: float = 0.0,
    air_overrun: float = 0.5,
    water_volume_L: float = C.CIP_DEFAULT_WATER_VOLUME_L,
    cip_water_temperature_K: float = C.CIP_DEFAULT_WATER_TEMP_K,
    detergent_type: str = C.CIP_DEFAULT_DETERGENT_TYPE,
    include_cleaning_phase: bool = True,
    bioplastic_yield_coefficient: float = C.DEFAULT_YIELD_COEFFICIENT,
    initial_filter_state: Optional[FilterState] = None,
    on_stage_complete: Optional[Callable[[str, StageResult, dict], None]] = None,
) -> dict[str, Any]:
    """
    Production split → CIP → prefiltration → cavitation → filtration → bioplastic.

    Composition of the residue is taken from **raw materials only** (Formula 2);
    flavor and inclusions add to Formula (1) total mass but not to those fractions
    (documented assumption).
    """
    preset_meta: dict[str, Any] = {}
    if literature_preset_id:
        preset = get_preset(literature_preset_id)
        raw = preset.raw_materials
        flavor_syrup_mass_kg = preset.flavor_syrup_mass_kg
        inclusion_mass_kg = preset.inclusion_mass_kg
        preset_meta = {
            "literature_preset_id": preset.id,
            "literature_citation": preset.citation,
        }
    else:
        raw = raw_materials or RawMaterials(**C.DEFAULT_RAW_MATERIALS_KG)

    wf, ws, ww, wsol = composition_from_raw_materials(raw)
    comp = Composition(fat=wf, sugar=ws, water=ww, solids=wsol)

    m_raw = raw.total_mass
    m_add = max(0.0, flavor_syrup_mass_kg) + max(0.0, inclusion_mass_kg)
    m_in = m_raw + m_add

    phi = max(0.0, min(1.0, residue_mass_fraction))
    m_res = phi * m_in
    m_prod = m_in - m_res
    residue = TankResidue(mass_kg=m_res, composition=comp, metadata={"residue_mass_fraction": phi})

    rho = C.RHO_MIX_KG_L
    ice_volume_L = (m_prod / rho) * (1.0 + max(0.0, air_overrun))

    cumulative: dict[str, Any] = {"product_kg": m_prod, "bioplastic_kg": 0.0}

    if on_stage_complete:
        mb = MassBalanceState(
            stage="production",
            mass_in=m_in,
            mass_out=m_prod + m_res,
            mass_product=m_prod,
            mass_waste=m_res,
            metadata={"residue_mass_fraction": phi, "ice_cream_volume_L": ice_volume_L},
        )
        on_stage_complete(
            "production",
            StageResult(
                stage_name="production",
                mass_balance=mb,
                outputs={
                    "product_mass_kg": m_prod,
                    "residue_mass_kg": m_res,
                    "ice_cream_volume_L": ice_volume_L,
                    "air_overrun": air_overrun,
                },
                model_used="SimplifiedSplit",
            ),
            dict(cumulative),
        )

    pre_report: dict[str, Any] = {}
    cav_report: dict[str, Any] = {}
    bioavailability = 1.0

    if include_cleaning_phase and water_volume_L > 0:
        wastewater = run_cip_wastewater(residue, water_volume_L, cip_water_temperature_K, detergent_type)
    else:
        wastewater = WastewaterStream(
            volume_L=0.0,
            mass_kg=0.0,
            temperature_K=cip_water_temperature_K,
            tss_mg_L=0.0,
            dissolved_sugar_kg=0.0,
            cod_mg_L=0.0,
            bod_mg_L=0.0,
            fog_mg_L=0.0,
        )

    cip_snapshot = wastewater.model_dump()
    if on_stage_complete and include_cleaning_phase and wastewater.volume_L > 0:
        mb_c = MassBalanceState(
            stage="cip",
            mass_in=water_volume_L * C.WATER_DENSITY_KG_L + residue.mass_kg,
            mass_out=wastewater.mass_kg,
            mass_waste=wastewater.mass_kg,
            metadata={"tss_mg_L": wastewater.tss_mg_L},
        )
        on_stage_complete(
            "cip",
            StageResult(stage_name="cip", mass_balance=mb_c, outputs=cip_snapshot, model_used="CIP"),
            dict(cumulative),
        )

    if include_cleaning_phase and wastewater.volume_L > C.VOLUME_EPS_L:
        wastewater, pre_report = run_prefiltration(wastewater, C.TSS_REMOVAL_FRACTION)
        wastewater, bioavailability, cav_report = run_cavitation_simplified(wastewater)

    permeate, retentate, filter_state = run_filtration(wastewater, initial_filter_state)
    bio = run_bioconversion(retentate, bioplastic_yield_coefficient, bioavailability)
    cumulative["bioplastic_kg"] = bio.mass_kg

    if on_stage_complete:
        mb_f = MassBalanceState(
            stage="filtration",
            mass_in=wastewater.mass_kg,
            mass_out=permeate.mass_kg + retentate.mass_kg,
            mass_product=permeate.mass_kg,
            mass_waste=retentate.mass_kg,
        )
        on_stage_complete(
            "filtration",
            StageResult(
                stage_name="filtration",
                mass_balance=mb_f,
                outputs={
                    "retentate_sugar_kg": retentate.sugar_mass_kg,
                    "filter_saturation_pct": filter_state.saturation_fraction * C.PERCENT,
                },
                model_used="Filtration",
            ),
            dict(cumulative),
        )
        mb_b = MassBalanceState(
            stage="bioconversion",
            mass_in=retentate.sugar_mass_kg,
            mass_out=bio.mass_kg,
            mass_product=bio.mass_kg,
        )
        on_stage_complete(
            "bioconversion",
            StageResult(stage_name="bioconversion", mass_balance=mb_b, outputs=bio.model_dump(), model_used="PHAyield"),
            dict(cumulative),
        )

    total_out = m_prod + m_res
    mass_ok = abs(m_in - total_out) < C.MASS_BALANCE_TOLERANCE_KG

    report: dict[str, Any] = {
        "inputs": {
            **preset_meta,
            "raw_materials_kg": m_raw,
            "additives_kg": m_add,
            "total_batch_mass_kg": m_in,
            "residue_mass_fraction": phi,
            "air_overrun": air_overrun,
            "cleaning_water_L": water_volume_L if include_cleaning_phase else 0.0,
            "include_cleaning_phase": include_cleaning_phase,
            "detergent_type": detergent_type,
            "bioplastic_yield_coefficient": bioplastic_yield_coefficient,
        },
        "production": {
            "product_mass_kg": m_prod,
            "residue_mass_kg": m_res,
            "ice_cream_volume_L": ice_volume_L,
            "composition_mass_fractions": {"fat": wf, "sugar": ws, "water": ww, "solids": wsol},
        },
        "cip": {
            "wastewater_volume_L": wastewater.volume_L,
            "wastewater_mass_kg": wastewater.mass_kg,
            "dissolved_sugar_kg": wastewater.dissolved_sugar_kg,
            "tss_mg_L": round(wastewater.tss_mg_L, 2),
            "bod_mg_L": round(wastewater.bod_mg_L, 2),
            "cod_mg_L": round(wastewater.cod_mg_L, 2),
            "fog_mg_L": round(wastewater.fog_mg_L, 2),
        },
        "prefiltration": pre_report or None,
        "cavitation": cav_report or None,
        "filtration": {
            "permeate_volume_L": permeate.volume_L,
            "retentate_mass_kg": retentate.mass_kg,
            "retentate_sugar_kg": retentate.sugar_mass_kg,
            "filter_saturation_pct": round(filter_state.saturation_fraction * C.PERCENT, 2),
            "maintenance_required": filter_state.maintenance_required,
        },
        "bioconversion": {
            "bioplastic_mass_kg": bio.mass_kg,
            "sugar_consumed_kg": bio.sugar_consumed_kg,
            "effective_yield_coefficient": bio.yield_coefficient,
            "cavitation_bioavailability_factor": bioavailability,
        },
        "summary": {
            "mass_balance_closed": mass_ok,
            "product_recovery_pct": round((m_prod / m_in) * C.PERCENT, 2) if m_in > 0 else 0.0,
            "plastic_kg_per_tonne_input": round(
                bio.mass_kg / (m_in / C.KG_PER_TONNE), 4
            )
            if m_in > 0
            else 0.0,
        },
        "typed_report": MaterialBatchCycleReport(
            raw_materials_kg=m_in,
            product_kg=m_prod,
            ice_cream_volume_L=ice_volume_L,
            total_wastewater_mass_kg=wastewater.mass_kg,
            total_bioplastic_mass_kg=bio.mass_kg,
            mass_balance_closed=mass_ok,
            report_dict={},
        ),
    }
    report["typed_report"] = report["typed_report"].model_copy(
        update={"report_dict": {k: v for k, v in report.items() if k != "typed_report"}}
    )
    return report


def print_report(report: dict[str, Any]) -> None:
    """Compact stdout summary."""
    print("=" * 60)
    print("ICE CREAM + WASTEWATER → BIOPLASTIC (simplified pipeline)")
    print("=" * 60)
    inp = report.get("inputs", {})
    if inp.get("literature_preset_id"):
        print(f"Preset: {inp.get('literature_preset_id')}")
    print(f"Batch mass in:       {inp.get('total_batch_mass_kg', 0):.2f} kg")
    print(f"Product mass:        {report['production']['product_mass_kg']:.2f} kg")
    print(f"Ice cream volume:    {report['production']['ice_cream_volume_L']:.2f} L (overrun + ρ)")
    print(f"Residue (CIP feed): {report['production']['residue_mass_kg']:.2f} kg")
    print(f"Cleaning included:   {inp.get('include_cleaning_phase', True)}")
    c = report.get("cip", {})
    print(f"Wastewater:          {c.get('wastewater_volume_L', 0):.2f} L, sugar {c.get('dissolved_sugar_kg', 0):.3f} kg")
    print(f"Bioplastic:          {report['bioconversion']['bioplastic_mass_kg']:.4f} kg")
    print(f"Mass balance OK:     {report['summary']['mass_balance_closed']}")
    print("=" * 60)
