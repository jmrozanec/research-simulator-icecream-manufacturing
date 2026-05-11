"""
Module 3: Filtration — Saturation (Darcy) Model.

Inputs: WastewaterStream, filter pore size, membrane surface area.
Simulation: Fouling — resistance R increases as mass accumulated increases.
Lifecycle: Filter health; if saturation > 90% => Maintenance Event.
Outputs: Permeate (clean water), Retentate (concentrated sugar/sludge).
"""

from __future__ import annotations

from typing import Optional

from icecream_simulator.batch_models import (
    WastewaterStream,
    PermeateStream,
    RetentateStream,
    FilterState,
)
from icecream_simulator import constants as C


class FiltrationConfig:
    """Filter and Darcy model parameters."""

    def __init__(
        self,
        filter_pore_size_um: float = C.FILTER_PORE_SIZE_UM,
        membrane_surface_area_m2: float = C.FILTER_MEMBRANE_AREA_M2,
        max_accumulated_mass_kg: float = C.FILTER_MAX_ACCUMULATED_MASS_KG,
        membrane_resistance_base_m_1: float = C.FILTER_BASE_RESISTANCE_M_1,
        fouling_coefficient: float = C.FILTER_FOULING_COEFFICIENT,
    ):
        self.filter_pore_size_um = filter_pore_size_um
        self.membrane_surface_area_m2 = membrane_surface_area_m2
        self.max_accumulated_mass_kg = max_accumulated_mass_kg
        self.membrane_resistance_base_m_1 = membrane_resistance_base_m_1
        self.fouling_coefficient = fouling_coefficient


def darcy_resistance(
    R_base: float,
    mass_accumulated_kg: float,
    fouling_coeff: float,
) -> float:
    """
    Simplified Darcy: total resistance R = R_base + fouling_term.
    Fouling term increases with mass accumulated on the membrane.
    Insert custom Darcy / cake resistance formula here.
    """
    return R_base + fouling_coeff * mass_accumulated_kg


def saturation_fraction(mass_accumulated_kg: float, max_mass_kg: float) -> float:
    """Saturation = accumulated / max (0–1)."""
    if max_mass_kg <= 0:
        return 0.0
    return min(1.0, mass_accumulated_kg / max_mass_kg)


def run_filtration(
    wastewater: WastewaterStream,
    config: FiltrationConfig,
    initial_filter_state: Optional[FilterState] = None,
) -> tuple[PermeateStream, RetentateStream, FilterState]:
    """
    Split wastewater into permeate and retentate; update filter state.
    Fouling: resistance increases with accumulated mass; saturation > 90%
    flags maintenance.
    """
    state = initial_filter_state or FilterState()

    permeate_volume_fraction = C.PERMEATE_VOLUME_FRACTION
    retentate_volume_fraction = 1.0 - permeate_volume_fraction

    permeate_volume_L = wastewater.volume_L * permeate_volume_fraction
    retentate_volume_L = wastewater.volume_L * retentate_volume_fraction
    permeate_mass_kg = wastewater.mass_kg * permeate_volume_fraction
    retentate_mass_kg = wastewater.mass_kg * retentate_volume_fraction

    retentate_sugar_kg = wastewater.dissolved_sugar_kg * C.SUGAR_REJECTION_TO_RETENTATE
    total_solids_kg = wastewater.tss_mg_L * C.KG_PER_MG * wastewater.volume_L
    solids_in_retentate = total_solids_kg * C.SOLIDS_REJECTION_TO_RETENTATE
    solids_fraction = (solids_in_retentate / retentate_mass_kg) if retentate_mass_kg > 0 else 0

    new_accumulated = (
        state.mass_accumulated_kg + retentate_mass_kg * C.FILTER_FOULING_MASS_FRACTION
    )
    sat = saturation_fraction(new_accumulated, config.max_accumulated_mass_kg)
    maintenance = sat >= C.FILTER_SATURATION_MAINTENANCE_THRESHOLD

    R = darcy_resistance(
        config.membrane_resistance_base_m_1,
        new_accumulated,
        config.fouling_coefficient,
    )
    new_state = FilterState(
        mass_accumulated_kg=new_accumulated,
        saturation_fraction=sat,
        maintenance_required=maintenance,
        metadata={"resistance_m_1": R},
    )

    permeate_tss = wastewater.tss_mg_L * C.PERMEATE_TSS_PASSAGE
    permeate = PermeateStream(
        volume_L=permeate_volume_L,
        mass_kg=permeate_mass_kg,
        tss_mg_L=permeate_tss,
    )
    retentate = RetentateStream(
        mass_kg=retentate_mass_kg,
        sugar_mass_kg=retentate_sugar_kg,
        solids_fraction=solids_fraction,
    )
    return permeate, retentate, new_state
