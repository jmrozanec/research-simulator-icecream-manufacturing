"""
Data schemas for the Ice Cream Production and Waste-to-Plastic Simulator.

Uses Pydantic for type safety, validation, and JSON serialization.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Raw Materials
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
# Mass Balance State (for stage callbacks / reporting)
# ---------------------------------------------------------------------------


class MassBalanceState(BaseModel):
    """Tracks mass and energy across a pipeline stage."""

    stage: str
    mass_in: float = 0.0
    mass_out: float = 0.0
    energy_in: float = 0.0
    energy_consumed: float = 0.0
    mass_product: float = 0.0
    mass_waste: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Stage Result (for on_stage_complete callback)
# ---------------------------------------------------------------------------


class StageResult(BaseModel):
    """Result of a single simulation stage."""

    stage_name: str
    mass_balance: MassBalanceState
    outputs: dict[str, Any] = Field(default_factory=dict)
    model_used: str = ""
