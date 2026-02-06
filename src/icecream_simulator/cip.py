"""
Module 2: CIP (Clean-in-Place) & Wastewater Generation.

Inputs: Water volume, water temperature, detergent type.
Simulation: Wash efficiency — dilute TankResidue into water.
Output: WastewaterStream (water with high TSS and dissolved sugars).
"""

from __future__ import annotations

from icecream_simulator.batch_models import TankResidue, WastewaterStream

# Water density (kg/L) for volume <-> mass
WATER_DENSITY_KG_L = 1.0


class CIPInput:
    """Input bundle for the CIP stage."""

    def __init__(
        self,
        tank_residue: TankResidue,
        water_volume_L: float = 80.0,
        water_temperature_K: float = 323.0,
        detergent_type: str = "alkaline",
    ):
        self.tank_residue = tank_residue
        self.water_volume_L = water_volume_L
        self.water_temperature_K = water_temperature_K
        self.detergent_type = detergent_type


def wash_efficiency(detergent_type: str) -> float:
    """
    Fraction of residue that is transferred into the water phase (dilution/wash).
    Insert custom detergent/wash model here (e.g. solubility, kinetics).
    """
    efficiencies = {"alkaline": 0.92, "acid": 0.88, "neutral": 0.85, "enzyme": 0.95}
    return efficiencies.get(detergent_type.lower(), 0.90)


def run_cip(inputs: CIPInput) -> WastewaterStream:
    """
    Simulate CIP: residue is diluted into cleaning water.
    Output is wastewater with TSS and dissolved sugars (no longer ice cream).
    """
    residue = inputs.tank_residue
    water_L = max(0.0, inputs.water_volume_L)
    water_mass_kg = water_L * WATER_DENSITY_KG_L

    # How much residue is washed off into the water
    eff = wash_efficiency(inputs.detergent_type)
    residue_into_water_kg = residue.mass_kg * eff
    dissolved_sugar_kg = residue_into_water_kg * residue.composition.sugar
    # TSS: suspended solids from residue (fat, stabilizers, etc.)
    solids_kg = residue_into_water_kg * (1.0 - residue.composition.water)
    total_mass_kg = water_mass_kg + residue_into_water_kg
    total_volume_L = water_L + (residue_into_water_kg / WATER_DENSITY_KG_L)
    if total_volume_L <= 0:
        total_volume_L = 1e-6
    tss_mg_L = (solids_kg * 1e6) / total_volume_L

    # BOD/COD from organics (sugar + fat) in the stream
    # Insert custom BOD/COD correlation here (e.g. from TOC, sugar, fat).
    bod_kg = dissolved_sugar_kg * 1.2 + residue_into_water_kg * residue.composition.fat * 2.0
    cod_kg = bod_kg * 1.5  # COD typically ~1.2–1.5 × BOD for organics
    bod_mg_L = (bod_kg * 1e6) / total_volume_L
    cod_mg_L = (cod_kg * 1e6) / total_volume_L

    # FOG: from fat in residue (parity with Pipeline 1 Wastewater.fog_mg_L)
    fat_into_water_kg = residue_into_water_kg * residue.composition.fat
    fog_mg_L = (fat_into_water_kg * 1e6) / total_volume_L if total_volume_L > 0 else 0.0

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
