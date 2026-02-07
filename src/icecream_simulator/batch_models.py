"""
MaterialBatch and stream data models for the Ice Cream Manufacturing
& Wastewater Valorization Simulator.

The MaterialBatch object passes through every stage of the simulation.
All stages consume or produce batches/streams derived from these types.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Composition & Contaminant Load (used inside MaterialBatch)
# ---------------------------------------------------------------------------


class Composition(BaseModel):
    """Mass fractions of main components (0–1). Sum need not equal 1 (remainder = water/other)."""

    fat: float = Field(ge=0, le=1, description="Fat mass fraction")
    sugar: float = Field(ge=0, le=1, description="Sugar mass fraction")
    water: float = Field(ge=0, le=1, description="Water mass fraction")
    solids: float = Field(ge=0, le=1, description="Solids (e.g. stabilizers, MSNF) mass fraction")

    def total_fraction(self) -> float:
        """Sum of defined fractions (for sanity checks)."""
        return self.fat + self.sugar + self.water + self.solids


class ContaminantLoad(BaseModel):
    """Contaminant load for wastewater/stream characterization (COD/BOD)."""

    cod_mg_L: float = Field(ge=0, description="Chemical Oxygen Demand (mg/L)")
    bod_mg_L: float = Field(ge=0, description="Biological Oxygen Demand (mg/L)")


# ---------------------------------------------------------------------------
# MaterialBatch — core object flowing through the simulation
# ---------------------------------------------------------------------------


class MaterialBatch(BaseModel):
    """
    Core object that passes through every stage of the simulation.

    Attributes:
        mass_kg: Total mass (kg).
        temperature_K: Temperature (K).
        viscosity_Pa_s: Dynamic viscosity μ (Pa·s).
        composition: Mass fractions (fat%, sugar%, water%, solids%).
        contaminant_load: COD/BOD when applicable (e.g. after CIP).
    """

    mass_kg: float = Field(ge=0, description="Mass (kg)")
    temperature_K: float = Field(ge=0, description="Temperature (K)")
    viscosity_Pa_s: float = Field(ge=0, description="Dynamic viscosity μ (Pa·s)")
    composition: Composition = Field(default_factory=Composition)
    contaminant_load: Optional[ContaminantLoad] = Field(
        default=None,
        description="COD/BOD load (None if not applicable, e.g. fresh mix)",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def sugar_mass_kg(self) -> float:
        """Sugar mass in batch (kg)."""
        return self.mass_kg * self.composition.sugar

    @property
    def fat_mass_kg(self) -> float:
        """Fat mass in batch (kg)."""
        return self.mass_kg * self.composition.fat


# ---------------------------------------------------------------------------
# Mixer outputs: product to freezer vs residue for cleaning
# ---------------------------------------------------------------------------


class ProductBatch(MaterialBatch):
    """Mixed product leaving the mixer (goes to freezer). Same as MaterialBatch with a semantic name."""

    pass


class TankResidue(BaseModel):
    """
    Residue left on tank walls after emptying (stays for cleaning).
    High viscosity and surface area increase residue mass.
    """

    mass_kg: float = Field(ge=0, description="Residue mass (kg)")
    composition: Composition = Field(default_factory=Composition)
    viscosity_Pa_s: float = Field(ge=0, description="Viscosity of residue (Pa·s)")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def sugar_mass_kg(self) -> float:
        return self.mass_kg * self.composition.sugar


# ---------------------------------------------------------------------------
# CIP output: wastewater stream (no longer "ice cream")
# ---------------------------------------------------------------------------


class WastewaterStream(BaseModel):
    """
    Stream after CIP: water with high TSS and dissolved sugars.
    This is no longer ice cream but wastewater for filtration/valorization.
    """

    volume_L: float = Field(ge=0, description="Volume (L)")
    mass_kg: float = Field(ge=0, description="Mass (kg)")
    temperature_K: float = Field(ge=0, description="Temperature (K)")
    tss_mg_L: float = Field(ge=0, description="Total Suspended Solids (mg/L)")
    dissolved_sugar_kg: float = Field(ge=0, description="Dissolved sugar mass (kg)")
    cod_mg_L: float = Field(ge=0, description="Chemical Oxygen Demand (mg/L)")
    bod_mg_L: float = Field(ge=0, description="Biological Oxygen Demand (mg/L)")
    fog_mg_L: float = Field(ge=0, description="Fats, Oils, Grease (mg/L)")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_sugar_kg(self) -> float:
        """Total sugar (dissolved + in TSS) for downstream valorization."""
        # Approximate: TSS includes some solids; sugar is part of organics
        return self.dissolved_sugar_kg  # + optional TSS-sugar if modeled


# ---------------------------------------------------------------------------
# Filtration outputs: permeate (clean water) and retentate (concentrate)
# ---------------------------------------------------------------------------


class PermeateStream(BaseModel):
    """Clean water stream after filtration (permeate)."""

    volume_L: float = Field(ge=0, description="Volume (L)")
    mass_kg: float = Field(ge=0, description="Mass (kg)")
    tss_mg_L: float = Field(ge=0, description="Residual TSS (mg/L)")
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetentateStream(BaseModel):
    """Concentrated sugar/sludge stream (retentate) for bioconversion."""

    mass_kg: float = Field(ge=0, description="Mass (kg)")
    sugar_mass_kg: float = Field(ge=0, description="Sugar mass available for conversion (kg)")
    solids_fraction: float = Field(ge=0, le=1, description="Solids mass fraction (0–1)")
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Filter state (for saturation / maintenance)
# ---------------------------------------------------------------------------


class FilterState(BaseModel):
    """Tracks filter health and accumulated mass for Darcy/fouling model."""

    mass_accumulated_kg: float = Field(default=0.0, ge=0, description="Mass accumulated on filter (kg)")
    saturation_fraction: float = Field(default=0.0, ge=0, le=1, description="Saturation (0–1); >0.9 triggers maintenance")
    maintenance_required: bool = Field(default=False, description="True if saturation > threshold")
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Bioconversion output
# ---------------------------------------------------------------------------


class BioplasticOutput(BaseModel):
    """Output of sugar-to-plastic bioconversion (e.g. PHA)."""

    mass_kg: float = Field(ge=0, description="Produced bioplastic mass (kg)")
    sugar_consumed_kg: float = Field(ge=0, description="Sugar mass consumed (kg)")
    yield_coefficient: float = Field(ge=0, description="g plastic per g sugar used")
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Typed report for full cycle
# ---------------------------------------------------------------------------

class MaterialBatchCycleReport(BaseModel):
    """
    Typed report for one MaterialBatch cycle.
    Includes mass_balance_closed for validation.
    """

    raw_materials_kg: float = 0.0
    product_to_freezer_kg: float = 0.0
    ice_cream_volume_L: float = 0.0  # with air overrun
    total_wastewater_mass_kg: float = 0.0
    total_bioplastic_mass_kg: float = 0.0
    total_energy_consumed_J: float = 0.0
    mass_balance_closed: bool = True
    report_dict: dict[str, Any] = Field(default_factory=dict)
