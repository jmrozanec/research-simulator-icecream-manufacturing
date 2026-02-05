"""
Data schemas for the Ice Cream Production and Waste-to-Plastic Simulator.

Uses Pydantic for type safety, validation, and JSON serialization.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input Stage: Raw Materials
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
