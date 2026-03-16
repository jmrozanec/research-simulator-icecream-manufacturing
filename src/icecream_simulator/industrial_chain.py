"""
Industrial ice cream manufacturing chain.

Flow: Preparation mix (hot) → Pasteurization (PHE) → Homogenization →
Cooling (PHE, two-stage) → Ageing vat (jacketed, stirrer) →
Freezer (overrun) → Hardening.

- Mixing (blending of ingredients) happens only in step 1 (preparation mix, hot).
  No air is added there; sugar/stabilizers dissolve and fat is liquid for homogenization.
- Aeration (overrun) is done only in step 6 (continuous freezer): air is incorporated
  there into the cold mix. So: mix first (liquid), then pasteurize, homogenize, cool,
  age, then freeze + aerate, then harden.

MaterialBatch flows through each stage; residue from preparation and ageing
is aggregated for CIP.
"""

from __future__ import annotations

from typing import Optional

from icecream_simulator.schemas import RawMaterials
from icecream_simulator.batch_models import MaterialBatch, TankResidue, Composition
from icecream_simulator.mixer import MixerInput, run_mixer

# Temperatures (K): preparation hot, pasteurization, after cooling, ageing, after freezer, hardening
T_PREP_K = 328.0       # ~55 °C preparation mix
T_PASTEUR_K = 353.15   # ~80 °C pasteurization
T_AFTER_COOL_K = 278.15  # ~5 °C after PHE cooling
T_AGEING_K = 277.15    # ~4 °C ageing vat
T_AFTER_FREEZER_K = 268.15  # ~-5 °C soft ice cream
T_HARDENING_K = 243.15  # ~-30 °C hardened

MIX_DENSITY_KG_L = 1.05
# Specific heat for heat-duty calculations (J/(kg·K)); PLUG-IN: replace with composition-based if needed
CP_MIX_J_KGK = 3800.0


def run_preparation_mix(
    raw_materials: RawMaterials,
    tank_surface_area_m2: float = 10.0,
    rpm: float = 60.0,
    mixing_time_s: float = 300.0,
) -> tuple[MaterialBatch, TankResidue, float]:
    """
    Step 1: High-shear preparation mix at ~50–60 °C.
    Only blending step: dissolves sugar/stabilizers, melts fat. No aeration;
    air is incorporated later in the freezer. Output: hot mix + tank residue.
    """
    inp = MixerInput(
        raw_materials=raw_materials,
        tank_surface_area_m2=tank_surface_area_m2,
        rpm=rpm,
        mixing_time_s=mixing_time_s,
        initial_temperature_K=T_PREP_K,
    )
    product_batch, tank_residue, power_W = run_mixer(inp)
    out = MaterialBatch(
        mass_kg=product_batch.mass_kg,
        temperature_K=product_batch.temperature_K,
        viscosity_Pa_s=product_batch.viscosity_Pa_s,
        composition=product_batch.composition,
        metadata={**product_batch.metadata, "stage": "preparation_mix"},
    )
    return out, tank_residue, power_W


def run_pasteurization(batch: MaterialBatch, outlet_temp_K: float = T_PASTEUR_K) -> MaterialBatch:
    """
    Step 2: Plate heat exchanger (PHE) — heat to pasteurization temperature.
    No mass loss. Heat duty: Q = m * cp * (T_out - T_in).
    """
    T_in = batch.temperature_K
    heat_duty_J = batch.mass_kg * CP_MIX_J_KGK * (outlet_temp_K - T_in)
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
            "T_in_K": T_in,
        },
    )


def run_homogenization(
    batch: MaterialBatch,
    pressure_bar: float = 200.0,
    reference_pressure_bar: float = 150.0,
) -> MaterialBatch:
    """
    Step 3: High-pressure homogenizer — fat droplets <1 μm.
    Higher pressure → finer emulsion → lower apparent viscosity.
    mu_new = mu * (p_ref / p)^alpha (alpha ~ 0.1–0.2).
    """
    # PLUG-IN: replace with droplet-size or empirical model
    if pressure_bar <= 0:
        pressure_bar = reference_pressure_bar
    alpha = 0.15
    viscosity_factor = (reference_pressure_bar / pressure_bar) ** alpha
    mu_new = batch.viscosity_Pa_s * viscosity_factor
    mu_new = max(mu_new, batch.viscosity_Pa_s * 0.5)  # cap reduction
    return MaterialBatch(
        mass_kg=batch.mass_kg,
        temperature_K=batch.temperature_K,
        viscosity_Pa_s=mu_new,
        composition=batch.composition,
        metadata={
            **batch.metadata,
            "stage": "homogenization",
            "homogenization_pressure_bar": pressure_bar,
            "viscosity_factor": viscosity_factor,
        },
    )


def run_cooling_phe(
    batch: MaterialBatch,
    temp_after_stage1_K: float = 303.15,  # ~30 °C after tower water
    temp_out_K: float = T_AFTER_COOL_K,   # ~5 °C after chilled/glycol
) -> MaterialBatch:
    """
    Step 4: Two-stage PHE cooling.
    Stage 1: tower water (e.g. 80°C → 30°C). Stage 2: chilled/glycol (30°C → 5°C).
    Heat removed each stage: Q = m * cp * |delta_T|.
    """
    T_in = batch.temperature_K
    Q1_J = batch.mass_kg * CP_MIX_J_KGK * (T_in - temp_after_stage1_K)
    Q2_J = batch.mass_kg * CP_MIX_J_KGK * (temp_after_stage1_K - temp_out_K)
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
        },
    )


def run_ageing_vat(
    batch: MaterialBatch,
    tank_surface_area_m2: float = 10.0,
    hold_temp_K: float = T_AGEING_K,
    stirrer_on: bool = True,
    jacket_flow_rate_L_min: float = 20.0,
    ageing_time_h: float = 4.0,
) -> tuple[MaterialBatch, TankResidue]:
    """
    Step 5: Jacketed ageing vat — cool hold with slow agitation.
    Fat crystallization, protein coating. Residue: cold mix sticks to walls;
    if stirrer is off, more residue (poor sweep). Viscosity increases when cold.
    """
    comp = batch.composition
    mu_cold = batch.viscosity_Pa_s * 1.2  # colder = higher viscosity
    # Residue = f(area, viscosity, stirrer): base per m², higher mu => more; stirrer off => more
    base_per_m2 = 0.02
    viscosity_factor = (mu_cold / 0.5) ** 0.5 if mu_cold > 0 else 1.0
    residue_kg = base_per_m2 * tank_surface_area_m2 * viscosity_factor
    if not stirrer_on:
        residue_kg *= 1.5  # poor sweep when stirrer off
    residue_kg = min(residue_kg, batch.mass_kg * 0.03)  # cap ~3%
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
        },
    )
    residue = TankResidue(
        mass_kg=residue_kg,
        composition=comp,
        viscosity_Pa_s=mu_cold,
        metadata={"stage": "ageing_vat"},
    )
    return product_batch, residue


def run_freezer(
    batch: MaterialBatch,
    air_overrun: float = 0.5,
    exit_temp_K: float = T_AFTER_FREEZER_K,
) -> tuple[MaterialBatch, float]:
    """
    Step 6: Continuous freezer (scraped surface). This is where aeration happens:
    overrun (air incorporation) is applied here; the preparation mix had no air.
    Also ice crystallization. Returns (batch same mass, metadata has overrun),
    ice_cream_volume_L. PLUG-IN: dasher load f(viscosity, temp).
    """
    volume_L = batch.mass_kg / MIX_DENSITY_KG_L
    ice_cream_volume_L = volume_L * (1.0 + air_overrun)
    out = MaterialBatch(
        mass_kg=batch.mass_kg,
        temperature_K=exit_temp_K,
        viscosity_Pa_s=batch.viscosity_Pa_s,
        composition=batch.composition,
        metadata={
            **batch.metadata,
            "stage": "freezer",
            "air_overrun": air_overrun,
            "ice_cream_volume_L": ice_cream_volume_L,
        },
    )
    return out, ice_cream_volume_L


def run_hardening(batch: MaterialBatch, final_temp_K: float = T_HARDENING_K) -> MaterialBatch:
    """
    Step 7: Hardening tunnel / blast freezer — deep freeze to ~-30 °C.
    Heat removed: Q = m * cp * (T_in - T_out) (sensible; latent of ice already in freezer).
    """
    Q_removed_J = batch.mass_kg * CP_MIX_J_KGK * (batch.temperature_K - final_temp_K)
    return MaterialBatch(
        mass_kg=batch.mass_kg,
        temperature_K=final_temp_K,
        viscosity_Pa_s=batch.viscosity_Pa_s,
        composition=batch.composition,
        metadata={
            **batch.metadata,
            "stage": "hardening",
            "final_temp_K": final_temp_K,
            "heat_removed_J": Q_removed_J,
        },
    )


def run_industrial_chain(
    raw_materials: RawMaterials,
    tank_surface_area_m2: float = 10.0,
    homogenization_pressure_bar: float = 200.0,
    air_overrun: float = 0.5,
    interface_flush_L: float = 5.0,
    stirrer_on: bool = True,
    jacket_flow_L_min: float = 20.0,
    preparation_rpm: float = 60.0,
    preparation_mixing_time_s: float = 300.0,
) -> tuple[MaterialBatch, MaterialBatch, TankResidue, float, float, list[dict]]:
    """
    Run full industrial chain: preparation → pasteurization → homogenization →
    cooling → ageing → freezer → hardening.

    Returns:
        final_product: batch after hardening (for reporting).
        batch_after_ageing: batch after ageing (before freezer; used for interface flush).
        cip_residue: combined residue (preparation + ageing + interface flush) for CIP.
        ice_cream_volume_L: volume after overrun (aeration in freezer).
        total_preparation_power_W: power from preparation mix stage.
        stage_results: list of dicts, one per stage (mass_kg, temp_in_K, temp_out_K, etc.).
    """
    stage_results: list[dict] = []
    total_input_kg = raw_materials.total_mass
    if total_input_kg <= 0:
        comp = Composition(fat=0, sugar=0, water=0, solids=0)
        empty = MaterialBatch(mass_kg=0, temperature_K=T_AGEING_K, viscosity_Pa_s=0, composition=comp)
        empty_residue = TankResidue(mass_kg=0, composition=comp, viscosity_Pa_s=0)
        return empty, empty, empty_residue, 0.0, 0.0, stage_results

    # 1. Preparation mix (hot) — only blending; no aeration
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
    # 2. Pasteurization
    t_in = batch.temperature_K
    batch = run_pasteurization(batch)
    stage_results.append({
        "stage": "pasteurization",
        "mass_kg": batch.mass_kg,
        "temp_in_K": t_in,
        "temp_out_K": batch.temperature_K,
        "heat_duty_J": batch.metadata.get("heat_duty_J"),
    })
    # 3. Homogenization
    batch = run_homogenization(batch, pressure_bar=homogenization_pressure_bar)
    stage_results.append({
        "stage": "homogenization",
        "mass_kg": batch.mass_kg,
        "temp_out_K": batch.temperature_K,
        "viscosity_Pa_s": batch.viscosity_Pa_s,
        "pressure_bar": homogenization_pressure_bar,
    })
    # 4. Cooling PHE
    batch = run_cooling_phe(batch)
    stage_results.append({
        "stage": "cooling_phe",
        "mass_kg": batch.mass_kg,
        "temp_out_K": batch.temperature_K,
        "heat_removed_stage1_J": batch.metadata.get("heat_removed_stage1_J"),
        "heat_removed_stage2_J": batch.metadata.get("heat_removed_stage2_J"),
    })
    # 5. Ageing vat
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
    })
    # Interface flush: subtract from product, add to CIP feed
    interface_flush_kg = min(interface_flush_L * MIX_DENSITY_KG_L, batch_after_ageing.mass_kg)
    product_kg = batch_after_ageing.mass_kg - interface_flush_kg
    batch_to_freezer = MaterialBatch(
        mass_kg=product_kg,
        temperature_K=batch_after_ageing.temperature_K,
        viscosity_Pa_s=batch_after_ageing.viscosity_Pa_s,
        composition=batch_after_ageing.composition,
        metadata=batch_after_ageing.metadata,
    )
    # 6. Freezer — aeration (overrun) applied here
    batch_after_freezer, ice_cream_volume_L = run_freezer(batch_to_freezer, air_overrun=air_overrun)
    stage_results.append({
        "stage": "freezer",
        "mass_kg": batch_after_freezer.mass_kg,
        "temp_out_K": batch_after_freezer.temperature_K,
        "air_overrun": air_overrun,
        "ice_cream_volume_L": ice_cream_volume_L,
    })
    # 7. Hardening
    batch = run_hardening(batch_after_freezer)
    stage_results.append({
        "stage": "hardening",
        "mass_kg": batch.mass_kg,
        "temp_out_K": batch.temperature_K,
        "heat_removed_J": batch.metadata.get("heat_removed_J"),
    })
    final_product = batch

    # Combined residue for CIP: preparation + ageing + interface flush (same composition as ageing)
    cip_residue_mass = prep_residue.mass_kg + ageing_residue.mass_kg + interface_flush_kg
    cip_residue = TankResidue(
        mass_kg=cip_residue_mass,
        composition=batch_after_ageing.composition,
        viscosity_Pa_s=batch_after_ageing.viscosity_Pa_s,
        metadata={"prep_kg": prep_residue.mass_kg, "ageing_kg": ageing_residue.mass_kg, "interface_flush_kg": interface_flush_kg},
    )

    return final_product, batch_after_ageing, cip_residue, ice_cream_volume_L, power_W, stage_results
