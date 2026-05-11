"""
Industrial ice cream manufacturing chain.

Preparation mix → Pasteurization (hold + lethality) → Homogenization (d32, μ) →
Cooling (two-stage PHE) → Ageing (fat crystallinity) → Flavor & inclusions →
Interface flush → Freezer (SSHE: overrun, ice crystals, dasher power) →
Hardening (hardness / melt proxies) → Packaging accounting.

Mixing only in preparation (no air). Aeration in continuous freezer.
"""

from __future__ import annotations

from icecream_simulator.schemas import RawMaterials
from icecream_simulator.crystallization_parameters import (
    DEFAULT_CRYSTALLIZATION_PARAMETERS,
    CrystallizationParameters,
)
from icecream_simulator.batch_models import MaterialBatch, TankResidue, Composition
from icecream_simulator.mixer import MixerInput, run_mixer
from icecream_simulator import industrial_physics as phys
from icecream_simulator import constants as C


def run_preparation_mix(
    raw_materials: RawMaterials,
    tank_surface_area_m2: float = C.DEFAULT_TANK_SURFACE_AREA_M2,
    rpm: float = C.DEFAULT_RPM,
    mixing_time_s: float = C.DEFAULT_MIXING_TIME_S,
) -> tuple[MaterialBatch, TankResidue, float]:
    """Step 1: High-shear preparation mix at ~55 °C; blending only, no aeration."""
    inp = MixerInput(
        raw_materials=raw_materials,
        tank_surface_area_m2=tank_surface_area_m2,
        rpm=rpm,
        mixing_time_s=mixing_time_s,
        initial_temperature_K=C.T_PREP_K,
    )
    product_batch, tank_residue, power_W = run_mixer(inp)
    out = MaterialBatch(
        mass_kg=product_batch.mass_kg,
        temperature_K=product_batch.temperature_K,
        viscosity_Pa_s=product_batch.viscosity_Pa_s,
        composition=product_batch.composition,
        metadata={**getattr(product_batch, "metadata", {}), "stage": "preparation_mix"},
    )
    return out, tank_residue, power_W


def run_pasteurization(
    batch: MaterialBatch,
    outlet_temp_K: float = C.T_PASTEUR_K,
    hold_time_s: float = C.DEFAULT_PASTEURIZATION_HOLD_TIME_S,
) -> MaterialBatch:
    """Step 2: PHE heat to pasteurization T, isothermal hold, lethality, heat duty with composition-based cp."""
    T_in = batch.temperature_K
    cp = phys.specific_heat_mix_J_kgK(batch.composition)
    heat_duty_J = batch.mass_kg * cp * (outlet_temp_K - T_in)
    T_c = outlet_temp_K - C.KELVIN_TO_CELSIUS_OFFSET
    log10_reduction = phys.pasteurization_log10_reduction(hold_time_s, T_c)
    d_at_t = phys.pasteurization_d_value_minutes_at_T_C(
        T_c, C.PASTEUR_D_REF_MIN, C.PASTEUR_T_REF_C, C.PASTEUR_Z_C
    )
    return MaterialBatch(
        mass_kg=batch.mass_kg,
        temperature_K=outlet_temp_K,
        viscosity_Pa_s=batch.viscosity_Pa_s,
        composition=batch.composition,
        metadata={
            **batch.metadata,
            "stage": "pasteurization",
            "phe_out_K": outlet_temp_K,
            "heat_duty_J": heat_duty_J,
            "cp_mix_J_kgK": cp,
            "T_in_K": T_in,
            "hold_time_s": hold_time_s,
            "log10_pathogen_reduction": log10_reduction,
            "d_value_minutes_at_hold_T": d_at_t,
        },
    )


def run_homogenization(
    batch: MaterialBatch,
    pressure_bar: float = C.HOMOG_DEFAULT_PRESSURE_BAR,
    d32_initial_um: float = C.HOMOG_D32_INITIAL_UM,
) -> MaterialBatch:
    """Step 3: Homogenizer — fat globule d32 (Walstra scaling) and apparent viscosity (Pal–Rhodes-type)."""
    p = max(pressure_bar, C.HOMOG_PRESSURE_FLOOR_BAR)
    d32_um = phys.homogenization_fat_globule_d32_um(p)
    mu_new = phys.homogenization_apparent_viscosity_Pa_s(batch.viscosity_Pa_s, d32_um, d32_initial_um)
    return MaterialBatch(
        mass_kg=batch.mass_kg,
        temperature_K=batch.temperature_K,
        viscosity_Pa_s=mu_new,
        composition=batch.composition,
        metadata={
            **batch.metadata,
            "stage": "homogenization",
            "homogenization_pressure_bar": pressure_bar,
            "fat_globule_d32_um": d32_um,
            "fat_globule_d32_initial_um": d32_initial_um,
        },
    )


def run_cooling_phe(
    batch: MaterialBatch,
    temp_after_stage1_K: float = C.T_AFTER_COOL_STAGE1_K,
    temp_out_K: float = C.T_AFTER_COOL_K,
) -> MaterialBatch:
    """Step 4: Two-stage PHE cooling with composition-based cp."""
    cp = phys.specific_heat_mix_J_kgK(batch.composition)
    T_in = batch.temperature_K
    Q1_J = batch.mass_kg * cp * (T_in - temp_after_stage1_K)
    Q2_J = batch.mass_kg * cp * (temp_after_stage1_K - temp_out_K)
    return MaterialBatch(
        mass_kg=batch.mass_kg,
        temperature_K=temp_out_K,
        viscosity_Pa_s=batch.viscosity_Pa_s,
        composition=batch.composition,
        metadata={
            **batch.metadata,
            "stage": "cooling_phe",
            "cooling_stage1_out_K": temp_after_stage1_K,
            "cooling_stage2_out_K": temp_out_K,
            "heat_removed_stage1_J": Q1_J,
            "heat_removed_stage2_J": Q2_J,
            "cp_mix_J_kgK": cp,
        },
    )


def run_ageing_vat(
    batch: MaterialBatch,
    tank_surface_area_m2: float = C.DEFAULT_TANK_SURFACE_AREA_M2,
    hold_temp_K: float = C.T_AGEING_K,
    stirrer_on: bool = C.DEFAULT_STIRRER_ON,
    jacket_flow_rate_L_min: float = C.AGEING_DEFAULT_JACKET_FLOW_L_MIN,
    ageing_time_h: float = C.AGEING_TIME_H_DEFAULT,
) -> tuple[MaterialBatch, TankResidue]:
    """Step 5: Ageing with fat crystallinity (Hartel-type kinetics) and wall residue."""
    comp = batch.composition
    x_cryst = phys.ageing_fat_crystallinity_fraction(ageing_time_h, hold_temp_K)
    mu_cold = phys.ageing_viscosity_after_crystallinity(
        batch.viscosity_Pa_s * C.AGEING_VISCOSITY_COLD_MULTIPLIER, x_cryst
    )
    viscosity_factor = (
        (mu_cold / C.AGEING_RESIDUE_REF_VISCOSITY_PA_S) ** C.AGEING_RESIDUE_VISCOSITY_EXPONENT
        if mu_cold > 0
        else 1.0
    )
    residue_kg = C.AGEING_RESIDUE_BASE_PER_M2 * tank_surface_area_m2 * viscosity_factor
    if not stirrer_on:
        residue_kg *= C.AGEING_NO_STIRRER_MULTIPLIER
    residue_kg = min(residue_kg, batch.mass_kg * C.AGEING_RESIDUE_MAX_FRACTION_OF_BATCH)
    product_kg = batch.mass_kg - residue_kg
    product_batch = MaterialBatch(
        mass_kg=product_kg,
        temperature_K=hold_temp_K,
        viscosity_Pa_s=mu_cold,
        composition=comp,
        metadata={
            **batch.metadata,
            "stage": "ageing_vat",
            "stirrer_on": stirrer_on,
            "jacket_flow_L_min": jacket_flow_rate_L_min,
            "ageing_time_h": ageing_time_h,
            "fat_crystallinity_fraction": x_cryst,
        },
    )
    residue = TankResidue(
        mass_kg=residue_kg,
        composition=comp,
        viscosity_Pa_s=mu_cold,
        metadata={"stage": "ageing_vat"},
    )
    return product_batch, residue


def run_flavor_and_inclusions(
    batch: MaterialBatch,
    flavor_syrup_mass_kg: float,
    inclusion_mass_kg: float,
    flavor_sugar_mass_fraction: float = C.FLAVOR_SUGAR_MASS_FRACTION,
    inclusion_solids_mass_fraction: float = C.INCLUSION_SOLIDS_MASS_FRACTION,
) -> MaterialBatch:
    """
    Step 6: Flavor syrup and particulate inclusions before freezer (mass-balanced composition).

    Syrup contributes sugar + water; inclusions contribute largely solids (fruit, chocolate chips).
    """
    m0 = batch.mass_kg
    m_f = max(0.0, flavor_syrup_mass_kg)
    m_i = max(0.0, inclusion_mass_kg)
    c = batch.composition
    m_new = m0 + m_f + m_i
    if m_new <= 0:
        return batch
    sugar_f = m_f * flavor_sugar_mass_fraction
    water_f = m_f * (1.0 - flavor_sugar_mass_fraction)
    solids_i = m_i * inclusion_solids_mass_fraction
    sugar_i = m_i * C.INCLUSION_SUGAR_MASS_FRACTION
    fat_new = (m0 * c.fat) / m_new
    sugar_new = (m0 * c.sugar + sugar_f + sugar_i) / m_new
    water_new = (m0 * c.water + water_f * (m_f > 0)) / m_new
    solids_new = (m0 * c.solids + solids_i) / m_new
    s = fat_new + sugar_new + water_new + solids_new
    if s > C.COMPOSITION_RENORM_THRESHOLD:
        fat_new /= s
        sugar_new /= s
        water_new /= s
        solids_new /= s
    comp = Composition(fat=fat_new, sugar=sugar_new, water=water_new, solids=solids_new)
    return MaterialBatch(
        mass_kg=m_new,
        temperature_K=batch.temperature_K,
        viscosity_Pa_s=batch.viscosity_Pa_s
        * (1.0 + C.INCLUSION_VISCOSITY_BOOST_COEFF * m_i / max(m0, C.MASS_EPSILON_KG)),
        composition=comp,
        metadata={
            **batch.metadata,
            "stage": "flavor_inclusions",
            "flavor_syrup_mass_kg": m_f,
            "inclusion_mass_kg": m_i,
        },
    )


def run_freezer(
    batch: MaterialBatch,
    air_overrun: float = C.DEFAULT_AIR_OVERRUN,
    exit_temp_K: float = C.T_AFTER_FREEZER_K,
    coolant_temp_K: float = C.T_FREEZER_COOLANT_K,
    residence_time_s: float = C.FREEZER_DEFAULT_RESIDENCE_TIME_S,
    dasher_rpm: float = C.FREEZER_DEFAULT_DASHER_RPM,
    barrel_diameter_m: float = C.FREEZER_DEFAULT_BARREL_DIAMETER_M,
    volume_fraction_wall_ice: float = C.FREEZER_VOLUME_FRACTION_WALL_ICE,
    crystallization_parameters: CrystallizationParameters | None = None,
) -> tuple[MaterialBatch, float]:
    """Step 7: SSHE — wall vs bulk ice populations, Gompertz + Avrami kinetics, barrel recrystallization."""
    cparams = crystallization_parameters or DEFAULT_CRYSTALLIZATION_PARAMETERS
    eff_over = phys.freezer_effective_overrun(air_overrun, dasher_rpm, residence_time_s)
    w_h = float(batch.metadata.get("w_hydrocolloid_mass_fraction", 0.0))
    w_e = float(batch.metadata.get("w_emulsifier_mass_fraction", 0.0))
    d_wall, d_bulk, d_vol_mean = phys.ice_crystal_volume_mean_um_sshe(
        residence_time_s,
        coolant_temp_K,
        dasher_rpm,
        exit_temp_K,
        w_h,
        w_e,
        volume_fraction_wall_ice=volume_fraction_wall_ice,
        params=cparams,
    )
    d_ice = phys.ice_crystal_mean_um_after_recrystallization(d_vol_mean, residence_time_s, params=cparams)
    p_dasher = phys.freezer_dasher_shaft_power_W(batch.viscosity_Pa_s, dasher_rpm, barrel_diameter_m)
    t_ifp_c = phys.initial_freezing_point_mix_celsius(batch.composition, params=cparams)
    exit_c = exit_temp_K - C.KELVIN_TO_CELSIUS_OFFSET
    gompertz_frozen_frac = phys.gompertz_frozen_water_fraction_sshe(residence_time_s, t_ifp_c, exit_c, params=cparams)
    avrami_frozen_frac = phys.avrami_frozen_water_fraction_sshe(residence_time_s, t_ifp_c, exit_c, params=cparams)
    frozen_blend = phys.blended_frozen_water_fraction_kinetics(
        gompertz_frozen_frac, avrami_frozen_frac, params=cparams
    )
    kelvin_dt_k = phys.kelvin_freezing_point_depression_K_for_ice_sphere_um(d_ice, params=cparams)
    volume_L = batch.mass_kg / C.MIX_DENSITY_KG_L
    ice_cream_volume_L = volume_L * (1.0 + eff_over)
    out = MaterialBatch(
        mass_kg=batch.mass_kg,
        temperature_K=exit_temp_K,
        viscosity_Pa_s=batch.viscosity_Pa_s * C.FREEZER_VISCOSITY_EXIT_MULTIPLIER,
        composition=batch.composition,
        metadata={
            **batch.metadata,
            "stage": "freezer",
            "air_overrun_requested": air_overrun,
            "air_overrun_effective": eff_over,
            "ice_cream_volume_L": ice_cream_volume_L,
            "ice_crystal_wall_um": d_wall,
            "ice_crystal_bulk_um": d_bulk,
            "ice_crystal_volume_mean_um": d_vol_mean,
            "volume_fraction_wall_ice": volume_fraction_wall_ice,
            "ice_crystal_primary_um": d_vol_mean,
            "ice_crystal_mean_um": d_ice,
            "gompertz_frozen_water_fraction": gompertz_frozen_frac,
            "avrami_frozen_water_fraction": avrami_frozen_frac,
            "frozen_water_fraction_kinetic_blend": frozen_blend,
            "initial_freezing_point_mix_C": t_ifp_c,
            "kelvin_freezing_point_depression_for_mean_crystal_K": kelvin_dt_k,
            "coolant_temp_K": coolant_temp_K,
            "residence_time_s": residence_time_s,
            "dasher_rpm": dasher_rpm,
            "dasher_shaft_power_W": p_dasher,
            "barrel_diameter_m": barrel_diameter_m,
            "crystallization_parameters_name": cparams.name,
        },
    )
    return out, ice_cream_volume_L


def run_storage_recrystallization(
    batch: MaterialBatch,
    storage_time_s: float,
    storage_temp_K: float,
    crystallization_parameters: CrystallizationParameters | None = None,
) -> MaterialBatch:
    """
    Post-hardening distribution / deep-freeze storage — Ostwald ripening of ice (Hartel).

    Updates mean crystal size, Kelvin ΔT, hardness and melt proxies at ``storage_temp_K``.
    Skip with ``storage_time_s <= 0``.
    """
    if storage_time_s <= 0:
        return batch
    cparams = crystallization_parameters or DEFAULT_CRYSTALLIZATION_PARAMETERS
    w_h = float(batch.metadata.get("w_hydrocolloid_mass_fraction", 0.0))
    w_e = float(batch.metadata.get("w_emulsifier_mass_fraction", 0.0))
    d_before = float(batch.metadata.get("ice_crystal_mean_um", C.FREEZER_DEFAULT_ICE_CRYSTAL_MEAN_UM))
    d_out = phys.storage_recrystallized_mean_um(
        d_before, storage_time_s, storage_temp_K, w_h, w_e, params=cparams
    )
    kelvin_dt_k = phys.kelvin_freezing_point_depression_K_for_ice_sphere_um(d_out, params=cparams)
    ov = float(batch.metadata.get("air_overrun_effective", batch.metadata.get("air_overrun", C.DEFAULT_AIR_OVERRUN)))
    blend = batch.metadata.get("frozen_water_fraction_kinetic_blend")
    gompertz = batch.metadata.get("gompertz_frozen_water_fraction")
    avrami = batch.metadata.get("avrami_frozen_water_fraction")
    if blend is not None:
        fw = float(blend)
    elif gompertz is not None and avrami is not None:
        fw = phys.blended_frozen_water_fraction_kinetics(float(gompertz), float(avrami), params=cparams)
    elif gompertz is not None:
        fw = float(gompertz)
    else:
        fw = None
    hard = phys.hardness_proxy_kPa(d_out, ov, storage_temp_K, frozen_water_fraction=fw, params=cparams)
    melt = phys.melt_rate_proxy_per_s(hard)
    return MaterialBatch(
        mass_kg=batch.mass_kg,
        temperature_K=storage_temp_K,
        viscosity_Pa_s=batch.viscosity_Pa_s,
        composition=batch.composition,
        metadata={
            **batch.metadata,
            "stage": "storage_recrystallization",
            "storage_time_s": storage_time_s,
            "storage_temp_K": storage_temp_K,
            "ice_crystal_mean_um_before_storage": d_before,
            "ice_crystal_mean_um": d_out,
            "kelvin_freezing_point_depression_for_mean_crystal_K": kelvin_dt_k,
            "hardness_proxy_kPa": hard,
            "melt_rate_proxy_per_s": melt,
        },
    )


def run_hardening(
    batch: MaterialBatch,
    final_temp_K: float = C.T_HARDENING_K,
    crystallization_parameters: CrystallizationParameters | None = None,
) -> MaterialBatch:
    """Step 8: Hardening tunnel — sensible heat removal, hardness and melt-rate proxies."""
    cparams = crystallization_parameters or DEFAULT_CRYSTALLIZATION_PARAMETERS
    cp = phys.specific_heat_mix_J_kgK(batch.composition)
    Q_removed_J = batch.mass_kg * cp * (batch.temperature_K - final_temp_K)
    ov = float(batch.metadata.get("air_overrun_effective", batch.metadata.get("air_overrun", C.DEFAULT_AIR_OVERRUN)))
    d_ice = float(batch.metadata.get("ice_crystal_mean_um", C.FREEZER_DEFAULT_ICE_CRYSTAL_MEAN_UM))
    blend = batch.metadata.get("frozen_water_fraction_kinetic_blend")
    gompertz = batch.metadata.get("gompertz_frozen_water_fraction")
    avrami = batch.metadata.get("avrami_frozen_water_fraction")
    if blend is not None:
        fw = float(blend)
    elif gompertz is not None and avrami is not None:
        fw = phys.blended_frozen_water_fraction_kinetics(float(gompertz), float(avrami), params=cparams)
    elif gompertz is not None:
        fw = float(gompertz)
    else:
        fw = None
    hard = phys.hardness_proxy_kPa(
        d_ice,
        ov,
        final_temp_K,
        frozen_water_fraction=fw,
        params=cparams,
    )
    melt = phys.melt_rate_proxy_per_s(hard)
    return MaterialBatch(
        mass_kg=batch.mass_kg,
        temperature_K=final_temp_K,
        viscosity_Pa_s=batch.viscosity_Pa_s * C.HARDENING_VISCOSITY_MULTIPLIER,
        composition=batch.composition,
        metadata={
            **batch.metadata,
            "stage": "hardening",
            "final_temp_K": final_temp_K,
            "heat_removed_J": Q_removed_J,
            "cp_mix_J_kgK": cp,
            "hardness_proxy_kPa": hard,
            "melt_rate_proxy_per_s": melt,
        },
    )


def run_packaging(
    batch: MaterialBatch,
    package_count: int,
) -> MaterialBatch:
    """Step 9: Allocate hardened mass to discrete packages (mass-balanced accounting)."""
    n = max(1, int(package_count))
    kg_each = batch.mass_kg / n
    return MaterialBatch(
        mass_kg=batch.mass_kg,
        temperature_K=batch.temperature_K,
        viscosity_Pa_s=batch.viscosity_Pa_s,
        composition=batch.composition,
        metadata={
            **batch.metadata,
            "stage": "packaging",
            "package_count": n,
            "net_mass_kg_per_package": kg_each,
        },
    )


def run_industrial_chain(
    raw_materials: RawMaterials,
    tank_surface_area_m2: float = C.DEFAULT_TANK_SURFACE_AREA_M2,
    homogenization_pressure_bar: float = C.HOMOG_DEFAULT_PRESSURE_BAR,
    air_overrun: float = C.DEFAULT_AIR_OVERRUN,
    interface_flush_L: float = C.DEFAULT_INTERFACE_FLUSH_L,
    stirrer_on: bool = C.DEFAULT_STIRRER_ON,
    jacket_flow_L_min: float = C.AGEING_DEFAULT_JACKET_FLOW_L_MIN,
    preparation_rpm: float = C.DEFAULT_RPM,
    preparation_mixing_time_s: float = C.DEFAULT_MIXING_TIME_S,
    pasteurization_hold_time_s: float = C.DEFAULT_PASTEURIZATION_HOLD_TIME_S,
    flavor_syrup_mass_kg: float = C.DEFAULT_FLAVOR_SYRUP_MASS_KG,
    inclusion_mass_kg: float = C.DEFAULT_INCLUSION_MASS_KG,
    coolant_temp_K: float = C.T_FREEZER_COOLANT_K,
    freezer_residence_time_s: float = C.FREEZER_DEFAULT_RESIDENCE_TIME_S,
    dasher_rpm: float = C.FREEZER_DEFAULT_DASHER_RPM,
    barrel_diameter_m: float = C.FREEZER_DEFAULT_BARREL_DIAMETER_M,
    package_count: int = C.DEFAULT_PACKAGE_COUNT,
    volume_fraction_wall_ice: float = C.FREEZER_VOLUME_FRACTION_WALL_ICE,
    storage_time_s: float = C.DEFAULT_STORAGE_TIME_S,
    storage_temp_K: float = C.T_STORAGE_DEFAULT_K,
    crystallization_parameters: CrystallizationParameters | None = None,
) -> tuple[MaterialBatch, MaterialBatch, TankResidue, float, float, list[dict]]:
    """
    Full chain including flavor/inclusions, SSHE parameters, packaging.

    Returns final packaged product batch (same total mass as after hardening),
    batch_after_ageing, cip_residue, ice_cream_volume_L, preparation_power_W, stage_results.
    """
    stage_results: list[dict] = []
    total_input_kg = raw_materials.total_mass
    if total_input_kg <= 0:
        comp = Composition(fat=0, sugar=0, water=0, solids=0)
        empty = MaterialBatch(mass_kg=0, temperature_K=C.T_AGEING_K, viscosity_Pa_s=0, composition=comp)
        empty_residue = TankResidue(mass_kg=0, composition=comp, viscosity_Pa_s=0)
        return empty, empty, empty_residue, 0.0, 0.0, stage_results

    batch, prep_residue, power_W = run_preparation_mix(
        raw_materials,
        tank_surface_area_m2=tank_surface_area_m2,
        rpm=preparation_rpm,
        mixing_time_s=preparation_mixing_time_s,
    )
    stage_results.append({
        "stage": "preparation_mix",
        "mass_kg": batch.mass_kg,
        "temp_out_K": batch.temperature_K,
        "viscosity_Pa_s": batch.viscosity_Pa_s,
        "residue_kg": prep_residue.mass_kg,
        "power_W": power_W,
    })

    t_in = batch.temperature_K
    batch = run_pasteurization(batch, hold_time_s=pasteurization_hold_time_s)
    stage_results.append({
        "stage": "pasteurization",
        "mass_kg": batch.mass_kg,
        "temp_in_K": t_in,
        "temp_out_K": batch.temperature_K,
        "heat_duty_J": batch.metadata.get("heat_duty_J"),
        "hold_time_s": pasteurization_hold_time_s,
        "log10_pathogen_reduction": batch.metadata.get("log10_pathogen_reduction"),
        "d_value_minutes_at_hold_T": batch.metadata.get("d_value_minutes_at_hold_T"),
    })

    d32_pre = C.HOMOG_D32_INITIAL_UM
    batch = run_homogenization(batch, pressure_bar=homogenization_pressure_bar, d32_initial_um=d32_pre)
    stage_results.append({
        "stage": "homogenization",
        "mass_kg": batch.mass_kg,
        "temp_out_K": batch.temperature_K,
        "viscosity_Pa_s": batch.viscosity_Pa_s,
        "pressure_bar": homogenization_pressure_bar,
        "fat_globule_d32_um": batch.metadata.get("fat_globule_d32_um"),
    })

    batch = run_cooling_phe(batch)
    stage_results.append({
        "stage": "cooling_phe",
        "mass_kg": batch.mass_kg,
        "temp_out_K": batch.temperature_K,
        "heat_removed_stage1_J": batch.metadata.get("heat_removed_stage1_J"),
        "heat_removed_stage2_J": batch.metadata.get("heat_removed_stage2_J"),
    })

    batch_after_ageing, ageing_residue = run_ageing_vat(
        batch,
        tank_surface_area_m2=tank_surface_area_m2,
        stirrer_on=stirrer_on,
        jacket_flow_rate_L_min=jacket_flow_L_min,
    )
    stage_results.append({
        "stage": "ageing_vat",
        "mass_kg": batch_after_ageing.mass_kg,
        "temp_out_K": batch_after_ageing.temperature_K,
        "residue_kg": ageing_residue.mass_kg,
        "stirrer_on": stirrer_on,
        "fat_crystallinity_fraction": batch_after_ageing.metadata.get("fat_crystallinity_fraction"),
    })

    batch = run_flavor_and_inclusions(
        batch_after_ageing,
        flavor_syrup_mass_kg=flavor_syrup_mass_kg,
        inclusion_mass_kg=inclusion_mass_kg,
    )
    stage_results.append({
        "stage": "flavor_inclusions",
        "mass_kg": batch.mass_kg,
        "flavor_syrup_mass_kg": flavor_syrup_mass_kg,
        "inclusion_mass_kg": inclusion_mass_kg,
    })

    interface_flush_kg = min(interface_flush_L * C.MIX_DENSITY_KG_L, batch.mass_kg)
    product_kg = batch.mass_kg - interface_flush_kg
    batch_to_freezer = MaterialBatch(
        mass_kg=product_kg,
        temperature_K=batch.temperature_K,
        viscosity_Pa_s=batch.viscosity_Pa_s,
        composition=batch.composition,
        metadata=batch.metadata,
    )

    batch_after_freezer, ice_cream_volume_L = run_freezer(
        batch_to_freezer,
        air_overrun=air_overrun,
        coolant_temp_K=coolant_temp_K,
        residence_time_s=freezer_residence_time_s,
        dasher_rpm=dasher_rpm,
        barrel_diameter_m=barrel_diameter_m,
        volume_fraction_wall_ice=volume_fraction_wall_ice,
        crystallization_parameters=crystallization_parameters,
    )
    stage_results.append({
        "stage": "freezer",
        "mass_kg": batch_after_freezer.mass_kg,
        "temp_out_K": batch_after_freezer.temperature_K,
        "air_overrun_effective": batch_after_freezer.metadata.get("air_overrun_effective"),
        "ice_cream_volume_L": ice_cream_volume_L,
        "ice_crystal_wall_um": batch_after_freezer.metadata.get("ice_crystal_wall_um"),
        "ice_crystal_bulk_um": batch_after_freezer.metadata.get("ice_crystal_bulk_um"),
        "ice_crystal_volume_mean_um": batch_after_freezer.metadata.get("ice_crystal_volume_mean_um"),
        "ice_crystal_primary_um": batch_after_freezer.metadata.get("ice_crystal_primary_um"),
        "ice_crystal_mean_um": batch_after_freezer.metadata.get("ice_crystal_mean_um"),
        "gompertz_frozen_water_fraction": batch_after_freezer.metadata.get("gompertz_frozen_water_fraction"),
        "avrami_frozen_water_fraction": batch_after_freezer.metadata.get("avrami_frozen_water_fraction"),
        "frozen_water_fraction_kinetic_blend": batch_after_freezer.metadata.get(
            "frozen_water_fraction_kinetic_blend"
        ),
        "initial_freezing_point_mix_C": batch_after_freezer.metadata.get("initial_freezing_point_mix_C"),
        "kelvin_freezing_point_depression_for_mean_crystal_K": batch_after_freezer.metadata.get(
            "kelvin_freezing_point_depression_for_mean_crystal_K"
        ),
        "dasher_shaft_power_W": batch_after_freezer.metadata.get("dasher_shaft_power_W"),
        "coolant_temp_K": coolant_temp_K,
        "residence_time_s": freezer_residence_time_s,
        "dasher_rpm": dasher_rpm,
        "crystallization_parameters_name": batch_after_freezer.metadata.get("crystallization_parameters_name"),
    })

    batch = run_hardening(batch_after_freezer, crystallization_parameters=crystallization_parameters)
    stage_results.append({
        "stage": "hardening",
        "mass_kg": batch.mass_kg,
        "temp_out_K": batch.temperature_K,
        "heat_removed_J": batch.metadata.get("heat_removed_J"),
        "hardness_proxy_kPa": batch.metadata.get("hardness_proxy_kPa"),
        "melt_rate_proxy_per_s": batch.metadata.get("melt_rate_proxy_per_s"),
    })

    batch = run_storage_recrystallization(
        batch,
        storage_time_s=storage_time_s,
        storage_temp_K=storage_temp_K,
        crystallization_parameters=crystallization_parameters,
    )
    if storage_time_s > 0:
        stage_results.append({
            "stage": "storage_recrystallization",
            "mass_kg": batch.mass_kg,
            "temp_out_K": batch.temperature_K,
            "storage_time_s": batch.metadata.get("storage_time_s"),
            "storage_temp_K": batch.metadata.get("storage_temp_K"),
            "ice_crystal_mean_um_before_storage": batch.metadata.get("ice_crystal_mean_um_before_storage"),
            "ice_crystal_mean_um": batch.metadata.get("ice_crystal_mean_um"),
            "kelvin_freezing_point_depression_for_mean_crystal_K": batch.metadata.get(
                "kelvin_freezing_point_depression_for_mean_crystal_K"
            ),
            "hardness_proxy_kPa": batch.metadata.get("hardness_proxy_kPa"),
            "melt_rate_proxy_per_s": batch.metadata.get("melt_rate_proxy_per_s"),
        })

    final_product = run_packaging(batch, package_count=package_count)
    stage_results.append({
        "stage": "packaging",
        "mass_kg": final_product.mass_kg,
        "package_count": final_product.metadata.get("package_count"),
        "net_mass_kg_per_package": final_product.metadata.get("net_mass_kg_per_package"),
    })

    cip_residue_mass = prep_residue.mass_kg + ageing_residue.mass_kg + interface_flush_kg
    cip_residue = TankResidue(
        mass_kg=cip_residue_mass,
        composition=batch_after_ageing.composition,
        viscosity_Pa_s=batch_after_ageing.viscosity_Pa_s,
        metadata={
            "prep_kg": prep_residue.mass_kg,
            "ageing_kg": ageing_residue.mass_kg,
            "interface_flush_kg": interface_flush_kg,
        },
    )

    return final_product, batch_after_ageing, cip_residue, ice_cream_volume_L, power_W, stage_results
