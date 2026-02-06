"""
Data schemas for the Ice Cream Production and Waste-to-Plastic Simulator.

Uses Pydantic for type safety, validation, and JSON serialization.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Production State Machine
# ---------------------------------------------------------------------------


class State(str, Enum):
    """Production line state. Wastewater is generated during CLEANING or IDLE→RUNNING."""

    IDLE = "idle"
    RUNNING = "running"
    CLEANING = "cleaning"


# ---------------------------------------------------------------------------
# Input Stage: Raw Materials (defined early for IceCreamRecipe)
# ---------------------------------------------------------------------------


class RawMaterials(BaseModel):
    """Raw material inputs for ice cream production (all in kg)."""

    milk: float = Field(ge=0, description="Milk mass (kg)")
    cream: float = Field(ge=0, description="Cream mass (kg)")
    sugar: float = Field(ge=0, description="Sugar mass (kg)")
    stabilizers: float = Field(ge=0, description="Stabilizers mass (kg)")
    water: float = Field(ge=0, description="Water mass (kg)")

    @property
    def total_mass(self) -> float:
        """Total mass of raw materials (kg)."""
        return self.milk + self.cream + self.sugar + self.stabilizers + self.water


# ---------------------------------------------------------------------------
# Ice Cream Recipe (for BOD/FOG calculations)
# ---------------------------------------------------------------------------


class IceCreamRecipe(BaseModel):
    """Recipe composition for BOD/FOG calculations in wastewater."""

    fat_content: float = Field(ge=0, le=1, description="Mass fraction of fat (0-1)")
    sugar_content: float = Field(ge=0, le=1, description="Mass fraction of sugar (0-1)")

    @classmethod
    def from_raw_materials(cls, raw_materials: RawMaterials) -> IceCreamRecipe:
        """Derive recipe composition from raw materials."""
        total = raw_materials.total_mass
        if total <= 0:
            return cls(fat_content=0.0, sugar_content=0.0)
        # Approximate: milk ~4% fat, cream ~36% fat
        fat_mass = raw_materials.milk * 0.04 + raw_materials.cream * 0.36
        return cls(
            fat_content=fat_mass / total,
            sugar_content=raw_materials.sugar / total,
        )


# ---------------------------------------------------------------------------
# Shrinkage (Operational Loss)
# ---------------------------------------------------------------------------


class ShrinkageResult(BaseModel):
    """Result of CalculateShrinkage: adhesion loss + interface flush."""

    adhesion_loss_kg: float = Field(ge=0, description="Product lost to tank/pipe adhesion (kg)")
    interface_flush_kg: float = Field(ge=0, description="Product discarded at start-of-run (kg)")
    adhesion_loss_L: float = Field(ge=0, description="Adhesion loss volume (L)")
    interface_flush_L: float = Field(ge=0, description="Interface flush volume (L)")
    total_system_shrinkage_kg: float = Field(ge=0, description="Total product loss (kg)")
    total_system_shrinkage_L: float = Field(ge=0, description="Total shrinkage volume (L)")


# ---------------------------------------------------------------------------
# Wastewater (from cleaning + operational loss)
# ---------------------------------------------------------------------------


class Wastewater(BaseModel):
    """Wastewater from cleaning/flushing. BOD and FOG scale with product loss."""

    volume_L: float = Field(ge=0, description="Total wastewater volume (L)")
    product_loss_kg: float = Field(ge=0, description="Product (mix) lost into wastewater (kg)")
    organic_content_kg: float = Field(ge=0, description="Organic load for BOD/bioplastic (kg)")
    bod_mg_L: float = Field(ge=0, description="Biological Oxygen Demand concentration (mg/L)")
    fog_mg_L: float = Field(ge=0, description="Fats, Oils, Grease concentration (mg/L)")
    bod_load_kg: float = Field(ge=0, description="Total BOD load (kg O2 equivalent)")
    cleaning_water_L: float = Field(ge=0, description="Cleaning water inflow (L)")


# ---------------------------------------------------------------------------
# Mixing Process (PIML) - Input/Output
# ---------------------------------------------------------------------------


class MixingInput(BaseModel):
    """Input for the mixing/PIML model."""

    raw_materials: RawMaterials
    shear_rate: float = Field(ge=0, description="Shear rate (1/s)")
    temperature: float = Field(ge=0, description="Temperature (K)")
    mixing_time: float = Field(ge=0, description="Mixing time (s)")

    @property
    def total_mass(self) -> float:
        return self.raw_materials.total_mass


class MixingOutput(BaseModel):
    """Output from the mixing/PIML model."""

    viscosity: float = Field(ge=0, description="Dynamic viscosity (Pa·s)")
    thermal_conductivity: float = Field(ge=0, description="Thermal conductivity (W/(m·K))")
    specific_heat: float = Field(ge=0, description="Specific heat capacity (J/(kg·K))")
    product_mass: float = Field(ge=0, description="Mass of mixed product (kg)")
    energy_consumed: float = Field(ge=0, description="Energy consumed during mixing (J)")


# ---------------------------------------------------------------------------
# Wastewater Filtration - Input/Output
# ---------------------------------------------------------------------------


class FiltrationInput(BaseModel):
    """Input for the filtration model."""

    feed_mass: float = Field(ge=0, description="Feed mass (kg)")
    solids_content: float = Field(ge=0, le=1, description="Fraction of solids in feed (0-1)")
    temperature: float = Field(ge=0, description="Feed temperature (K)")


class FiltrationOutput(BaseModel):
    """Output from the filtration model."""

    product_mass: float = Field(ge=0, description="Mass of recovered product (kg)")
    wastewater_mass: float = Field(ge=0, description="Mass of wastewater stream (kg)")
    solids_in_wastewater: float = Field(ge=0, description="Solids/organics in wastewater (kg)")
    energy_consumed: float = Field(ge=0, description="Energy consumed (J)")


# ---------------------------------------------------------------------------
# Bioplastic Conversion - Input/Output
# ---------------------------------------------------------------------------


class BioplasticConversionInput(BaseModel):
    """Input for the bioplastic conversion model."""

    wastewater_mass: float = Field(ge=0, description="Wastewater mass (kg)")
    organic_content: float = Field(ge=0, description="Organic/sugar content in wastewater (kg)")
    pathway: str = Field(default="PHA", description="Conversion pathway (e.g., PHA, PLA)")


class BioplasticConversionOutput(BaseModel):
    """Output from the bioplastic conversion model."""

    bioplastic_mass: float = Field(ge=0, description="Produced bioplastic mass (kg)")
    residue_mass: float = Field(ge=0, description="Residue/byproduct mass (kg)")
    conversion_yield: float = Field(ge=0, le=1, description="Yield fraction (0-1)")
    energy_consumed: float = Field(ge=0, description="Energy consumed (J)")


# ---------------------------------------------------------------------------
# Mass Balance State (internal tracking)
# ---------------------------------------------------------------------------


class MassBalanceState(BaseModel):
    """Tracks mass and energy across the pipeline."""

    stage: str
    mass_in: float = 0.0
    mass_out: float = 0.0
    energy_in: float = 0.0
    energy_consumed: float = 0.0
    mass_product: float = 0.0
    mass_waste: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Simulation Report (JSON-ready output)
# ---------------------------------------------------------------------------


class StageResult(BaseModel):
    """Result of a single simulation stage."""

    stage_name: str
    mass_balance: MassBalanceState
    outputs: dict[str, Any] = Field(default_factory=dict)
    model_used: str = ""


class SimulationReport(BaseModel):
    """Comprehensive simulation report, JSON-serializable."""

    raw_materials: RawMaterials
    stage_results: list[StageResult] = Field(default_factory=list)
    total_product_mass: float = 0.0
    total_wastewater_mass: float = 0.0
    total_bioplastic_mass: float = 0.0
    total_energy_consumed: float = 0.0
    mass_balance_closed: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
