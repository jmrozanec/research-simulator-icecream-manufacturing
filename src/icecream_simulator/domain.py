"""Pydantic models for the simplified pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from icecream_simulator import constants as C


class RawMaterials(BaseModel):
    """Raw material inputs (kg)."""

    milk: float = Field(ge=0)
    cream: float = Field(ge=0)
    sugar: float = Field(ge=0)
    stabilizers: float = Field(ge=0)
    emulsifiers_kg: float = Field(default=0.0, ge=0)
    water: float = Field(ge=0)
    cocoa_powder_kg: float = Field(default=0.0, ge=0)
    egg_yolk_kg: float = Field(default=0.0, ge=0)
    vanilla_extract_kg: float = Field(default=0.0, ge=0)
    vanillin_kg: float = Field(default=0.0, ge=0)

    @property
    def total_mass(self) -> float:
        return (
            self.milk
            + self.cream
            + self.sugar
            + self.stabilizers
            + self.emulsifiers_kg
            + self.water
            + self.cocoa_powder_kg
            + self.egg_yolk_kg
            + self.vanilla_extract_kg
            + self.vanillin_kg
        )


class MassBalanceState(BaseModel):
    stage: str
    mass_in: float = 0.0
    mass_out: float = 0.0
    energy_in: float = 0.0
    energy_consumed: float = 0.0
    mass_product: float = 0.0
    mass_waste: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class StageResult(BaseModel):
    stage_name: str
    mass_balance: MassBalanceState
    outputs: dict[str, Any] = Field(default_factory=dict)
    model_used: str = ""


class Composition(BaseModel):
    fat: float = Field(ge=0, le=1)
    sugar: float = Field(ge=0, le=1)
    water: float = Field(ge=0, le=1)
    solids: float = Field(ge=0, le=1)


class TankResidue(BaseModel):
    mass_kg: float = Field(ge=0)
    composition: Composition = Field(default_factory=Composition)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WastewaterStream(BaseModel):
    volume_L: float = Field(ge=0)
    mass_kg: float = Field(ge=0)
    temperature_K: float = Field(ge=0)
    tss_mg_L: float = Field(ge=0)
    dissolved_sugar_kg: float = Field(ge=0)
    cod_mg_L: float = Field(ge=0)
    bod_mg_L: float = Field(ge=0)
    fog_mg_L: float = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_sugar_kg(self) -> float:
        if self.volume_L <= 0:
            return self.dissolved_sugar_kg
        tss_kg = (self.tss_mg_L * C.KG_PER_MG) * self.volume_L
        return self.dissolved_sugar_kg + tss_kg * C.WASTEWATER_TSS_SUGAR_FRACTION


class PermeateStream(BaseModel):
    volume_L: float = Field(ge=0)
    mass_kg: float = Field(ge=0)
    tss_mg_L: float = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetentateStream(BaseModel):
    mass_kg: float = Field(ge=0)
    sugar_mass_kg: float = Field(ge=0)
    solids_fraction: float = Field(ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FilterState(BaseModel):
    mass_accumulated_kg: float = Field(default=0.0, ge=0)
    saturation_fraction: float = Field(default=0.0, ge=0, le=1)
    maintenance_required: bool = Field(default=False)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BioplasticOutput(BaseModel):
    mass_kg: float = Field(ge=0)
    sugar_consumed_kg: float = Field(ge=0)
    yield_coefficient: float = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MaterialBatchCycleReport(BaseModel):
    raw_materials_kg: float = 0.0
    product_kg: float = 0.0
    ice_cream_volume_L: float = 0.0
    total_wastewater_mass_kg: float = 0.0
    total_bioplastic_mass_kg: float = 0.0
    mass_balance_closed: bool = True
    report_dict: dict[str, Any] = Field(default_factory=dict)


class LiteratureRecipePreset(BaseModel):
    id: str
    citation: str = ""
    raw_materials: RawMaterials
    flavor_syrup_mass_kg: float = Field(default=0.0, ge=0)
    inclusion_mass_kg: float = Field(default=0.0, ge=0)
