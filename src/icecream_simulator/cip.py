"""
Module 2: CIP (Clean-in-Place) & Wastewater Generation.

Inputs: Water volume, water temperature, detergent type.
Simulation: Wash efficiency — dilute TankResidue into water.
Output: WastewaterStream (water with high TSS and dissolved sugars).
"""

from __future__ import annotations

from icecream_simulator.batch_models import TankResidue, WastewaterStream
from icecream_simulator import constants as C


class CIPInput:
    """Input bundle for the CIP stage."""

    def __init__(
        self,
        tank_residue: TankResidue,
        water_volume_L: float = C.CIP_DEFAULT_WATER_VOLUME_L,
        water_temperature_K: float = C.CIP_DEFAULT_WATER_TEMP_K,
        detergent_type: str = C.CIP_DEFAULT_DETERGENT_TYPE,
    ):
        self.tank_residue = tank_residue
        self.water_volume_L = water_volume_L
        self.water_temperature_K = water_temperature_K
        self.detergent_type = detergent_type


def wash_efficiency(detergent_type: str) -> float:
    """
    Fraction of residue transferred into the wash water (empirical by detergent class).
    """
    return C.WASH_EFFICIENCY.get(detergent_type.lower(), C.WASH_EFFICIENCY_DEFAULT)


def run_cip(inputs: CIPInput) -> WastewaterStream:
    """
    Simulate CIP: residue is diluted into cleaning water.
    Output is wastewater with TSS and dissolved sugars (no longer ice cream).
    """
    residue = inputs.tank_residue
    water_L = max(0.0, inputs.water_volume_L)
    water_mass_kg = water_L * C.WATER_DENSITY_KG_L

    eff = wash_efficiency(inputs.detergent_type)
    residue_into_water_kg = residue.mass_kg * eff
    dissolved_sugar_kg = residue_into_water_kg * residue.composition.sugar
    solids_kg = residue_into_water_kg * (1.0 - residue.composition.water)
    total_mass_kg = water_mass_kg + residue_into_water_kg
    total_volume_L = water_L + (residue_into_water_kg / C.WATER_DENSITY_KG_L)
    if total_volume_L <= 0:
        total_volume_L = C.VOLUME_EPSILON_L
    tss_mg_L = (solids_kg * C.MG_PER_KG) / total_volume_L

    bod_kg = (
        dissolved_sugar_kg * C.BOD_SUGAR_COEFFICIENT
        + residue_into_water_kg * residue.composition.fat * C.BOD_FAT_COEFFICIENT
    )
    cod_kg = bod_kg * C.COD_TO_BOD_RATIO
    bod_mg_L = (bod_kg * C.MG_PER_KG) / total_volume_L
    cod_mg_L = (cod_kg * C.MG_PER_KG) / total_volume_L

    fat_into_water_kg = residue_into_water_kg * residue.composition.fat
    fog_mg_L = (
        (fat_into_water_kg * C.MG_PER_KG) / total_volume_L if total_volume_L > 0 else 0.0
    )

    return WastewaterStream(
        volume_L=total_volume_L,
        mass_kg=total_mass_kg,
        temperature_K=inputs.water_temperature_K,
        tss_mg_L=tss_mg_L,
        dissolved_sugar_kg=dissolved_sugar_kg,
        cod_mg_L=cod_mg_L,
        bod_mg_L=bod_mg_L,
        fog_mg_L=fog_mg_L,
        metadata={"detergent": inputs.detergent_type, "wash_efficiency": eff},
    )
