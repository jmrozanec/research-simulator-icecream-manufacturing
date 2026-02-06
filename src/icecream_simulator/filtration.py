"""
Module 3: Filtration — Saturation (Darcy) Model.

Inputs: WastewaterStream, filter pore size, membrane surface area.
Simulation: Fouling — resistance R increases as mass accumulated increases.
Lifecycle: Filter health; if saturation > 90% => Maintenance Event.
Outputs: Permeate (clean water), Retentate (concentrated sugar/sludge).
"""

from __future__ import annotations

from icecream_simulator.batch_models import (
    WastewaterStream,
    PermeateStream,
    RetentateStream,
    FilterState,
)

# Saturation threshold for maintenance
SATURATION_MAINTENANCE_THRESHOLD = 0.90


class FiltrationConfig:
    """Filter and Darcy model parameters."""

    def __init__(
        self,
        filter_pore_size_um: float = 0.1,
        membrane_surface_area_m2: float = 10.0,
        max_accumulated_mass_kg: float = 50.0,
        membrane_resistance_base_m_1: float = 1e12,
        fouling_coefficient: float = 1e14,
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
    initial_filter_state: FilterState | None = None,
) -> tuple[PermeateStream, RetentateStream, FilterState]:
    """
    Split wastewater into permeate and retentate; update filter state.
    Fouling: resistance increases with accumulated mass; saturation > 90%
    flags maintenance.
    """
    state = initial_filter_state or FilterState()

    # Recovery ratio: how much goes to permeate vs retentate
    # Insert custom separation model here (e.g. rejection vs pore size, flux).
    # Simplified: 70% volume to permeate, 30% to retentate (concentrated).
    permeate_volume_fraction = 0.70
    retentate_volume_fraction = 1.0 - permeate_volume_fraction

    permeate_volume_L = wastewater.volume_L * permeate_volume_fraction
    retentate_volume_L = wastewater.volume_L * retentate_volume_fraction
    # Mass split (assume density ~1)
    permeate_mass_kg = wastewater.mass_kg * permeate_volume_fraction
    retentate_mass_kg = wastewater.mass_kg * retentate_volume_fraction

    # Sugar and solids concentrate in retentate (membrane rejects sugar)
    sugar_rejection_to_retentate = 0.85  # Insert custom rejection model here
    retentate_sugar_kg = wastewater.dissolved_sugar_kg * sugar_rejection_to_retentate
    total_solids_kg = wastewater.tss_mg_L * 1e-6 * wastewater.volume_L
    solids_in_retentate = total_solids_kg * 0.9  # Most TSS in retentate
    solids_fraction = (solids_in_retentate / retentate_mass_kg) if retentate_mass_kg > 0 else 0

    # Fouling: mass accumulated on filter increases
    new_accumulated = state.mass_accumulated_kg + retentate_mass_kg * 0.1  # 10% of retentate fouls
    sat = saturation_fraction(new_accumulated, config.max_accumulated_mass_kg)
    maintenance = sat >= SATURATION_MAINTENANCE_THRESHOLD

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

    # Permeate: cleaner water (reduced TSS)
    permeate_tss = wastewater.tss_mg_L * 0.05  # 95% rejection
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
