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

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from icecream_simulator.schemas import RawMaterials
from icecream_simulator.batch_models import (
    ProductBatch,
    TankResidue,
    Composition,
)


# ---------------------------------------------------------------------------
# Pluggable mixer model (extensibility)
# ---------------------------------------------------------------------------


class MixerModelBase(ABC):
    """
    Abstract base for mixer stage in the MaterialBatch pipeline.
    Provide your own implementation for custom rheology, power, or residue models.
    """

    @property
    def model_name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def run(self, inputs: MixerInput) -> tuple[ProductBatch, TankResidue, float]:
        """
        Run the mixer stage.
        Returns:
            (product_batch, tank_residue, power_W)
        """
        ...


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
    # Egg yolk: ~25% fat, ~10% solids (protein), remainder water (handbook splits).
    egg_fat = rm.egg_yolk_kg * 0.25
    egg_solid = rm.egg_yolk_kg * 0.10
    egg_water = rm.egg_yolk_kg * 0.65
    # Vanilla extract: approximate as dilute aqueous ethanol extract.
    ve_water = rm.vanilla_extract_kg * 0.65
    ve_solid = rm.vanilla_extract_kg * 0.35
    fat_mass = rm.milk * 0.04 + rm.cream * 0.36 + egg_fat
    solids_mass = (
        rm.milk * 0.09
        + rm.stabilizers
        + rm.emulsifiers_kg
        + rm.cocoa_powder_kg
        + egg_solid
        + ve_solid
        + rm.vanillin_kg
    )
    water_mass = rm.water + egg_water + ve_water
    return Composition(
        fat=fat_mass / total,
        sugar=rm.sugar / total,
        water=water_mass / total,
        solids=solids_mass / total,
    )


def viscosity_power_law(
    temperature_K: float,
    shear_rate_1_s: float,
    stabilizer_fraction: float,
    sugar_fraction: float,
    hydrocolloid_fraction: float | None = None,
    emulsifier_fraction: float | None = None,
    k_consistency: float = 1.0,
    n_power: float = 0.5,
    temp_coeff: float = -0.02,
    T_ref: float = 293.0,
) -> float:
    """
    Power Law fluid viscosity: μ = k * (shear_rate)^(n-1) with temperature
    and composition effects.

    Hydrocolloids (``hydrocolloid_fraction``) raise viscosity strongly; emulsifiers
    (``emulsifier_fraction``) add a smaller contribution. If not given, legacy
    ``stabilizer_fraction`` is treated as total hydrocolloid-like solids.
    """
    shear_term = max(1e-6, shear_rate_1_s) ** (n_power - 1.0)
    temp_factor = 1.0 + temp_coeff * (temperature_K - T_ref)
    temp_factor = max(0.1, temp_factor)
    if hydrocolloid_fraction is not None and emulsifier_fraction is not None:
        comp_factor = (
            1.0
            + 2.4 * hydrocolloid_fraction
            + 0.85 * emulsifier_fraction
            + 0.5 * sugar_fraction
        )
    else:
        comp_factor = 1.0 + 2.0 * stabilizer_fraction + 0.5 * sugar_fraction
    return k_consistency * shear_term * temp_factor * comp_factor


def mixing_power(W: float, mu: float, N_rps: float, D_m: float) -> float:
    """
    Power draw (W) for agitated vessel: P = K·μ·N²·D³.

    Uses laminar power number K=2; replace via ``MixerModelBase`` for other impellers.
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

    Empirical wall-loss scaling; override via ``MixerModelBase`` for plant-specific fouling.
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
    w_h = rm.stabilizers / total_mass
    w_e = rm.emulsifiers_kg / total_mass
    # Shear rate from RPM and diameter (simplified): gamma ~ N * D / gap
    N_rps = inputs.rpm / 60.0
    shear_rate = N_rps * inputs.impeller_diameter_m * 10.0  # 1/s

    mu = viscosity_power_law(
        temperature_K=T,
        shear_rate_1_s=shear_rate,
        stabilizer_fraction=comp.solids,
        sugar_fraction=comp.sugar,
        hydrocolloid_fraction=w_h,
        emulsifier_fraction=w_e,
    )

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
        metadata={
            "w_hydrocolloid_mass_fraction": w_h,
            "w_emulsifier_mass_fraction": w_e,
        },
    )
    tank_residue = TankResidue(
        mass_kg=residue_kg,
        composition=comp,
        viscosity_Pa_s=mu,
    )
    return product_batch, tank_residue, power_W


class DefaultMixerModel(MixerModelBase):
    """Default mixer implementation using Power Law viscosity and P = K·μ·N²·D³."""

    def run(self, inputs: MixerInput) -> tuple[ProductBatch, TankResidue, float]:
        return run_mixer(inputs)
