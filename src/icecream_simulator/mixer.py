"""
Module 1: The Mixer — Rheology & Residue Model.

Inputs: Raw ingredients (Milk, Cream, Sugar, Stabilizers), Mixer Geometry
(Tank Surface Area), RPM, Mixing Time.

Simulation logic:
- Viscosity model (e.g. Power Law fluid): viscosity increases as stabilizers
  hydrate and temperature drops.
- Power: P = K·μ·N²·D³ (torque/resistance on blades).
- Loss model: ResidueMass = f(viscosity, surface area); higher viscosity
  => more stickiness/waste.

Outputs: ProductBatch (to freezer), TankResidue (for cleaning).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from icecream_simulator.schemas import RawMaterials
from icecream_simulator.batch_models import (
    ProductBatch,
    TankResidue,
    Composition,
)


class MixerGeometry(BaseModel):
    """Mixer tank and impeller geometry for power and residue calculations."""

    tank_surface_area_m2: float = Field(ge=0, default=10.0)
    impeller_diameter_m: float = Field(ge=0, default=0.5)


class MixerInput:
    """Input bundle for the mixer stage."""

    def __init__(
        self,
        raw_materials: RawMaterials,
        tank_surface_area_m2: float = 10.0,
        impeller_diameter_m: float = 0.5,
        rpm: float = 60.0,
        mixing_time_s: float = 300.0,
        initial_temperature_K: float = 278.0,
    ):
        self.raw_materials = raw_materials
        self.tank_surface_area_m2 = tank_surface_area_m2
        self.impeller_diameter_m = impeller_diameter_m
        self.rpm = rpm
        self.mixing_time_s = mixing_time_s
        self.initial_temperature_K = initial_temperature_K


def _composition_from_raw_materials(rm: RawMaterials) -> Composition:
    """Derive composition (mass fractions) from raw materials."""
    total = rm.total_mass
    if total <= 0:
        return Composition(fat=0, sugar=0, water=0, solids=0)
    fat_mass = rm.milk * 0.04 + rm.cream * 0.36
    return Composition(
        fat=fat_mass / total,
        sugar=rm.sugar / total,
        water=rm.water / total,
        solids=(rm.milk * 0.09 + rm.stabilizers) / total,  # MSNF + stabilizers
    )


def viscosity_power_law(
    temperature_K: float,
    shear_rate_1_s: float,
    stabilizer_fraction: float,
    sugar_fraction: float,
    k_consistency: float = 1.0,
    n_power: float = 0.5,
    temp_coeff: float = -0.02,
    T_ref: float = 293.0,
) -> float:
    """
    Power Law fluid viscosity: μ = k * (shear_rate)^(n-1) with temperature
    and composition effects.

    PLUG-IN: Replace this with your own viscosity model (e.g. Arrhenius,
    Carreau-Yasuda, or an ML/PIML surrogate trained on rheometer data).
    Default: shear-thinning (n < 1), viscosity increases as T drops and
    stabilizers/sugar increase.
    """
    # Shear-thinning: apparent viscosity decreases with shear rate
    shear_term = max(1e-6, shear_rate_1_s) ** (n_power - 1.0)
    # Temperature: viscosity increases as T decreases (temp_coeff < 0)
    temp_factor = 1.0 + temp_coeff * (temperature_K - T_ref)
    temp_factor = max(0.1, temp_factor)
    # Composition: stabilizers and sugar increase viscosity
    comp_factor = 1.0 + 2.0 * stabilizer_fraction + 0.5 * sugar_fraction
    return k_consistency * shear_term * temp_factor * comp_factor


def mixing_power(W: float, mu: float, N_rps: float, D_m: float) -> float:
    """
    Power draw (W) for agitated vessel: P = K·μ·N²·D³.

    PLUG-IN: Replace K or the whole formula with your power number /
    correlation (e.g. from impeller type, Re, or CFD).
    """
    K = 2.0  # Power number ~2 for typical radial impeller in laminar regime
    return K * mu * (N_rps**2) * (D_m**3)


def residue_mass_kg(
    viscosity_Pa_s: float,
    tank_surface_area_m2: float,
    reference_viscosity: float = 1.0,
    reference_area_m2: float = 10.0,
    base_residue_per_m2_kg: float = 0.05,
) -> float:
    """
    Residue mass stuck to tank walls: function of viscosity and surface area.
    Higher viscosity => more stickiness => more waste.

    PLUG-IN: Replace with your own loss/fouling model (e.g. empirical,
    CFD adhesion, or ML-predicted residue from viscosity + geometry).
    """
    viscosity_factor = (viscosity_Pa_s / reference_viscosity) ** 0.5
    area_factor = tank_surface_area_m2 / reference_area_m2
    return base_residue_per_m2_kg * viscosity_factor * area_factor * tank_surface_area_m2


def run_mixer(inputs: MixerInput) -> tuple[ProductBatch, TankResidue, float]:
    """
    Run the mixer stage: rheology, power, residue split.

    Returns:
        (product_batch, tank_residue, power_W)
    """
    rm = inputs.raw_materials
    total_mass = rm.total_mass
    if total_mass <= 0:
        comp = Composition(fat=0, sugar=0, water=0, solids=0)
        return (
            ProductBatch(
                mass_kg=0, temperature_K=inputs.initial_temperature_K,
                viscosity_Pa_s=0, composition=comp,
            ),
            TankResidue(mass_kg=0, composition=comp, viscosity_Pa_s=0),
            0.0,
        )

    comp = _composition_from_raw_materials(rm)
    T = inputs.initial_temperature_K
    # Shear rate from RPM and diameter (simplified): gamma ~ N * D / gap
    N_rps = inputs.rpm / 60.0
    shear_rate = N_rps * inputs.impeller_diameter_m * 10.0  # 1/s, insert custom formula here

    # --- Insert custom viscosity formula here ---
    mu = viscosity_power_law(
        temperature_K=T,
        shear_rate_1_s=shear_rate,
        stabilizer_fraction=comp.solids,
        sugar_fraction=comp.sugar,
    )

    # --- Insert custom power formula here ---
    power_W = mixing_power(
        W=0, mu=mu, N_rps=N_rps, D_m=inputs.impeller_diameter_m
    )

    # Residue: mass lost to walls
    residue_kg = residue_mass_kg(
        viscosity_Pa_s=mu,
        tank_surface_area_m2=inputs.tank_surface_area_m2,
    )
    residue_kg = min(residue_kg, total_mass * 0.15)  # Cap at 15% of batch
    product_kg = total_mass - residue_kg

    product_batch = ProductBatch(
        mass_kg=product_kg,
        temperature_K=T,
        viscosity_Pa_s=mu,
        composition=comp,
    )
    tank_residue = TankResidue(
        mass_kg=residue_kg,
        composition=comp,
        viscosity_Pa_s=mu,
    )
    return product_batch, tank_residue, power_W
