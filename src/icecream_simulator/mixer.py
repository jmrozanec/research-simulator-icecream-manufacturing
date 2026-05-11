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
from icecream_simulator import constants as C


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

    tank_surface_area_m2: float = Field(ge=0, default=C.DEFAULT_TANK_SURFACE_AREA_M2)
    impeller_diameter_m: float = Field(ge=0, default=C.DEFAULT_IMPELLER_DIAMETER_M)


class MixerInput:
    """Input bundle for the mixer stage."""

    def __init__(
        self,
        raw_materials: RawMaterials,
        tank_surface_area_m2: float = C.DEFAULT_TANK_SURFACE_AREA_M2,
        impeller_diameter_m: float = C.DEFAULT_IMPELLER_DIAMETER_M,
        rpm: float = C.DEFAULT_RPM,
        mixing_time_s: float = C.DEFAULT_MIXING_TIME_S,
        initial_temperature_K: float = C.DEFAULT_TEMPERATURE_K,
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
    k_consistency: float = C.RHEOLOGY_K_CONSISTENCY,
    n_power: float = C.RHEOLOGY_POWER_INDEX_N,
    temp_coeff: float = C.RHEOLOGY_TEMP_COEFF,
    T_ref: float = C.RHEOLOGY_TEMP_REF_K,
) -> float:
    """
    Power Law fluid viscosity: μ = k * (shear_rate)^(n-1) with temperature
    and composition effects.

    Hydrocolloids (``hydrocolloid_fraction``) raise viscosity strongly; emulsifiers
    (``emulsifier_fraction``) add a smaller contribution. If not given, legacy
    ``stabilizer_fraction`` is treated as total hydrocolloid-like solids.
    """
    shear_term = max(C.RHEOLOGY_SHEAR_RATE_FLOOR, shear_rate_1_s) ** (n_power - 1.0)
    temp_factor = 1.0 + temp_coeff * (temperature_K - T_ref)
    temp_factor = max(C.RHEOLOGY_TEMP_FACTOR_FLOOR, temp_factor)
    if hydrocolloid_fraction is not None and emulsifier_fraction is not None:
        comp_factor = (
            1.0
            + C.RHEOLOGY_HYDROCOLLOID_FACTOR * hydrocolloid_fraction
            + C.RHEOLOGY_EMULSIFIER_FACTOR * emulsifier_fraction
            + C.RHEOLOGY_SUGAR_FACTOR * sugar_fraction
        )
    else:
        comp_factor = (
            1.0
            + C.RHEOLOGY_LEGACY_SOLIDS_FACTOR * stabilizer_fraction
            + C.RHEOLOGY_SUGAR_FACTOR * sugar_fraction
        )
    return k_consistency * shear_term * temp_factor * comp_factor


def mixing_power(W: float, mu: float, N_rps: float, D_m: float) -> float:
    """
    Power draw (W) for agitated vessel: P = K·μ·N²·D³.

    Uses ``MIXING_POWER_NUMBER`` (≈2 radial, laminar) from constants; override via
    ``MixerModelBase`` for other impellers.
    """
    return C.MIXING_POWER_NUMBER * mu * (N_rps**2) * (D_m**3)


def residue_mass_kg(
    viscosity_Pa_s: float,
    tank_surface_area_m2: float,
    reference_viscosity: float = C.RESIDUE_REF_VISCOSITY_PA_S,
    reference_area_m2: float = C.RESIDUE_REF_AREA_M2,
    base_residue_per_m2_kg: float = C.RESIDUE_BASE_KG_PER_M2,
) -> float:
    """
    Residue mass stuck to tank walls: function of viscosity and surface area.
    Higher viscosity => more stickiness => more waste.

    Empirical wall-loss scaling; override via ``MixerModelBase`` for plant-specific fouling.
    """
    viscosity_factor = (viscosity_Pa_s / reference_viscosity) ** C.RESIDUE_VISCOSITY_EXPONENT
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
    N_rps = inputs.rpm / C.SECONDS_PER_MINUTE
    shear_rate = N_rps * inputs.impeller_diameter_m * C.SHEAR_RATE_TIP_MULTIPLIER

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
    residue_kg = min(residue_kg, total_mass * C.RESIDUE_MAX_FRACTION_OF_BATCH)
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
