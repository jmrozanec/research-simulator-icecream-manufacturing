"""
Energy accounting for ice cream manufacturing — thermal and mechanical.

Tracks per-stage energy consumption with:
- Thermal energy: heating, cooling (with PHE effectiveness), refrigeration (with COP)
- Mechanical electrical: mixing, homogenization, dasher, agitation
- Energy losses: tank surface radiation + convection
- Composition-dependent properties (cp, conductivity)

References:
- Singh & Heldman (2014) — food engineering thermal properties
- IEC 61800-3 — VFD motor efficiency classes
- Gogate & Pandit (2004) — cavitation power consumption

Returns per-stage and aggregated energy reports (J, kWh, thermal vs electrical).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from icecream_simulator.batch_models import Composition
from icecream_simulator import industrial_physics as phys


# Physical constants
STEFAN_BOLTZMANN = 5.67e-8  # W/(m²·K⁴)


@dataclass
class EnergyBalance:
    """Energy breakdown for one stage."""

    stage_name: str
    thermal_duty_J: float = 0.0  # Heating/cooling duty (absolute value)
    electrical_shaft_W: float = 0.0  # Shaft power (mixing, homogenization, dasher)
    electrical_motor_W: float = 0.0  # Motor power (shaft + losses)
    refrigeration_J: float = 0.0  # Cooling load (evaporator duty)
    refrigeration_electrical_J: float = 0.0  # Compressor work (duty / COP)
    tank_loss_J: float = 0.0  # Conduction + radiation from tank walls
    total_thermal_J: float = 0.0  # thermal_duty + tank_loss (all heat interactions)
    total_electrical_J: float = 0.0  # electrical_motor + refrigeration_electrical
    total_J: field(default=0.0) = field(init=False)

    def __post_init__(self):
        """Compute totals."""
        self.total_thermal_J = self.thermal_duty_J + self.tank_loss_J
        self.total_electrical_J = self.electrical_motor_W * 1.0 + self.refrigeration_electrical_J
        # Total includes both: what we input (electrical) and what we remove/add (thermal)
        self.total_J = max(self.total_electrical_J, self.total_thermal_J)

    def to_kWh(self) -> float:
        """Convert total to kWh."""
        return self.total_J / 3.6e6

    def to_dict(self) -> dict:
        """Export as dict."""
        return {
            "stage_name": self.stage_name,
            "thermal_duty_J": self.thermal_duty_J,
            "electrical_shaft_W": self.electrical_shaft_W,
            "electrical_motor_W": self.electrical_motor_W,
            "refrigeration_J": self.refrigeration_J,
            "refrigeration_electrical_J": self.refrigeration_electrical_J,
            "tank_loss_J": self.tank_loss_J,
            "total_thermal_J": self.total_thermal_J,
            "total_electrical_J": self.total_electrical_J,
            "total_J": self.total_J,
            "total_kWh": self.to_kWh(),
        }


# ============================================================================
# Thermal properties (composition-dependent)
# ============================================================================


def thermal_conductivity_W_mK(water_fraction: float) -> float:
    """Thermal conductivity (W/(m·K)) from water fraction."""
    return 0.4 + 0.2 * water_fraction


def tank_u_value_W_m2K(insulation_thickness_mm: float = 50.0) -> float:
    """
    Overall heat transfer coefficient U for a jacketed tank.

    U ≈ 1 / (R_inside + R_wall + R_insulation + R_outside).
    Typical dairy tank with 50 mm foam: U ≈ 0.3–0.5 W/(m²·K).
    With no insulation (steel only): U ≈ 10 W/(m²·K).
    """
    if insulation_thickness_mm <= 0:
        return 10.0  # Bare steel tank
    # R_insulation ≈ thickness / k_foam; k_foam ≈ 0.035 W/(m·K) for polyurethane
    r_ins = insulation_thickness_mm / 1000.0 / 0.035
    return 1.0 / (0.0002 + 0.0005 + r_ins + 0.0001)  # rough estimates for other layers


def tank_surface_loss_J(
    mass_kg: float,
    T_inside_K: float,
    T_ambient_K: float,
    tank_surface_area_m2: float = 10.0,
    u_value_W_m2K: float = 0.3,
    duration_s: float = 300.0,
    emissivity: float = 0.5,
) -> float:
    """
    Heat loss from tank walls during a process stage.

    Combines:
    - Convection/conduction: Q = U × A × ΔT
    - Radiation: Q = σ × ε × A × (T_inside⁴ - T_ambient⁴)

    Total loss is integrated over duration_s.
    """
    if T_inside_K <= T_ambient_K or duration_s <= 0:
        return 0.0

    delta_T = T_inside_K - T_ambient_K
    q_convection = u_value_W_m2K * tank_surface_area_m2 * delta_T
    q_radiation = (
        emissivity
        * STEFAN_BOLTZMANN
        * tank_surface_area_m2
        * (T_inside_K**4 - T_ambient_K**4)
    )
    q_total = q_convection + q_radiation
    return q_total * duration_s


# ============================================================================
# Mechanical power consumption
# ============================================================================


def motor_efficiency_fraction(motor_power_W: float, efficiency_class: str = "IE3") -> float:
    """
    Motor efficiency (input electrical / output shaft) for industrial motors.

    Typical efficiencies:
    - IE2 (EFF1): 87–92% for 10–100 kW
    - IE3 (EFF2): 90–94% for 10–100 kW (EU standard as of 2015)
    - IE4 (EFF3): 92–96% for 10–100 kW
    """
    classes = {
        "IE1": 0.88,
        "IE2": 0.90,
        "IE3": 0.92,
        "IE4": 0.94,
    }
    eta = classes.get(efficiency_class, 0.92)
    # Loss scales slightly with load; at part load, efficiency dips ~1–2%
    if motor_power_W < 1.0:
        eta *= 0.85
    return eta


def motor_electrical_power_from_shaft(
    shaft_power_W: float, efficiency_class: str = "IE3"
) -> float:
    """Convert shaft power to electrical input power via motor efficiency."""
    if shaft_power_W <= 0:
        return 0.0
    eta = motor_efficiency_fraction(shaft_power_W, efficiency_class)
    return shaft_power_W / eta


def homogenizer_power_W(
    mass_flow_kg_s: float,
    pressure_bar: float,
    pump_efficiency: float = 0.70,
) -> float:
    """
    Homogenizer (pump) power: P = (Q × ΔP) / η.

    Q: volumetric flow (m³/s) from mass_flow and density (~1050 kg/m³)
    ΔP: pressure rise (Pa)
    η: pump overall efficiency (typical 65–75%)
    """
    if mass_flow_kg_s <= 0 or pressure_bar <= 0:
        return 0.0
    density = 1050.0  # kg/m³ for milk-based mix
    q_m3_s = mass_flow_kg_s / density
    dp_pa = pressure_bar * 1e5
    return (q_m3_s * dp_pa) / pump_efficiency


# ============================================================================
# Refrigeration and cooling
# ============================================================================


def refrigeration_cop(
    evaporator_temp_K: float,
    condenser_temp_K: float = 308.15,
) -> float:
    """
    Coefficient of performance (COP) for a vapor-compression cycle.

    Carnot COP = T_cold / (T_hot - T_cold); real systems ~60% of Carnot.
    Typical commercial: 3–5 at (T_evap=253K, T_cond=308K).
    """
    if evaporator_temp_K >= condenser_temp_K:
        return 1.0  # Impossible; return degenerate value
    carnot_cop = evaporator_temp_K / (condenser_temp_K - evaporator_temp_K)
    return max(1.0, 0.60 * carnot_cop)


def phe_effectiveness(
    mass_flow_kg_s: float,
    cp_J_kgK: float,
    hot_in_K: float,
    cold_in_K: float,
    effectiveness: float = 0.85,
) -> float:
    """
    Effectiveness of a plate-frame heat exchanger (0–1).

    ε = (T_hot_out - T_hot_in) / (T_hot_in - T_cold_in).

    Typical industrial PHE: 0.80–0.95. We assume 0.85.
    Returns outlet temperature of the hot side.
    """
    if effectiveness <= 0 or effectiveness > 1:
        effectiveness = 0.85
    delta_T_max = hot_in_K - cold_in_K
    delta_T_actual = effectiveness * delta_T_max
    return hot_in_K - delta_T_actual


# ============================================================================
# Stage-level energy calculations
# ============================================================================


def energy_preparation_mix(
    mass_kg: float,
    power_W: float,
    duration_s: float,
    tank_surface_area_m2: float = 10.0,
    T_process_K: float = 328.0,
    T_ambient_K: float = 293.15,
) -> EnergyBalance:
    """Energy for preparation: mixing shaft power + tank losses."""
    motor_power = motor_electrical_power_from_shaft(power_W)
    tank_loss = tank_surface_loss_J(
        mass_kg,
        T_process_K,
        T_ambient_K,
        tank_surface_area_m2,
        duration_s=duration_s,
    )
    return EnergyBalance(
        stage_name="preparation_mix",
        electrical_shaft_W=power_W,
        electrical_motor_W=motor_power,
        tank_loss_J=tank_loss,
    )


def energy_pasteurization(
    mass_kg: float,
    heat_duty_J: float,
    duration_s: float,
    tank_surface_area_m2: float = 10.0,
    T_process_K: float = 353.15,
    T_ambient_K: float = 293.15,
    phe_eff: float = 0.85,
) -> EnergyBalance:
    """
    Energy for pasteurization: heating duty + tank losses.

    The duty is computed as mass × cp × ΔT. To deliver it via a PHE,
    we need to account for effectiveness (losses in the exchanger).
    """
    # PHE duty accounts for approach temperature; input is actual heat duty
    duty_input = heat_duty_J / phe_eff if phe_eff > 0 else heat_duty_J
    tank_loss = tank_surface_loss_J(
        mass_kg,
        T_process_K,
        T_ambient_K,
        tank_surface_area_m2,
        duration_s=duration_s,
    )
    return EnergyBalance(
        stage_name="pasteurization",
        thermal_duty_J=duty_input,
        tank_loss_J=tank_loss,
    )


def energy_homogenization(
    mass_kg: float,
    pressure_bar: float,
    hold_time_s: float,
) -> EnergyBalance:
    """Energy for homogenization: pump power."""
    # Approximate flow rate: batch mass over hold time
    flow_kg_s = mass_kg / max(hold_time_s, 1.0)
    shaft_power_W_avg = homogenizer_power_W(flow_kg_s, pressure_bar)
    motor_power = motor_electrical_power_from_shaft(shaft_power_W_avg)
    return EnergyBalance(
        stage_name="homogenization",
        electrical_shaft_W=shaft_power_W_avg,
        electrical_motor_W=motor_power,
    )


def energy_cooling(
    mass_kg: float,
    heat_removed_J: float,
    coolant_temp_K: float,
    duration_s: float = 600.0,
    tank_surface_area_m2: float = 10.0,
    T_ambient_K: float = 293.15,
) -> EnergyBalance:
    """
    Energy for cooling: refrigeration load + tank losses.

    Cooling is delivered by a refrigeration cycle (evaporator in PHE jacket).
    Electrical work = evaporator duty / COP.
    """
    cop = refrigeration_cop(coolant_temp_K)
    electrical_J = heat_removed_J / cop
    # Product temperature during cooling: assume average between before and after
    T_avg_K = 315.0  # ~42°C, rough middle point
    tank_loss = tank_surface_loss_J(
        mass_kg, T_avg_K, T_ambient_K, tank_surface_area_m2, duration_s=duration_s
    )
    return EnergyBalance(
        stage_name="cooling_phe",
        refrigeration_J=heat_removed_J,
        refrigeration_electrical_J=electrical_J,
        tank_loss_J=tank_loss,
    )


def energy_ageing(
    mass_kg: float,
    stirrer_on: bool,
    jacket_flow_L_min: float,
    duration_hours: float = 4.0,
    tank_surface_area_m2: float = 10.0,
    T_ageing_K: float = 277.15,
    T_ambient_K: float = 293.15,
) -> EnergyBalance:
    """
    Energy for ageing: stirrer power (if on) + cooling to maintain jacket T.

    Jacket cooling maintains T ≈ 4°C against ambient heat leak.
    """
    shaft_power_W = 0.0
    if stirrer_on:
        # Rough estimate: slow agitation ~3–5 kW for a 200 L batch
        shaft_power_W = 3.5
    motor_power = motor_electrical_power_from_shaft(shaft_power_W)

    # Cooling load: maintain jacket outlet T against ambient
    duration_s = duration_hours * 3600.0
    jacket_inlet_K = 271.0  # Typical -2°C coolant return
    jacket_outlet_K = 274.0  # Typical +1°C coolant return
    # Rough: estimate heat leak through tank walls (Q = U·A·ΔT_jacket)
    u_value = tank_u_value_W_m2K()
    q_jacket = u_value * tank_surface_area_m2 * (T_ageing_K - jacket_inlet_K)
    cooling_load_J = max(0, q_jacket * duration_s)
    cop = refrigeration_cop(jacket_inlet_K)
    refrig_electrical_J = cooling_load_J / cop if cop > 0 else 0.0

    tank_loss = tank_surface_loss_J(
        mass_kg, T_ageing_K, T_ambient_K, tank_surface_area_m2, duration_s=duration_s
    )

    return EnergyBalance(
        stage_name="ageing_vat",
        electrical_shaft_W=shaft_power_W,
        electrical_motor_W=motor_power,
        refrigeration_J=cooling_load_J,
        refrigeration_electrical_J=refrig_electrical_J,
        tank_loss_J=tank_loss,
    )


def energy_freezer(
    mass_kg: float,
    dasher_shaft_power_W: float,
    residence_time_s: float,
    coolant_temp_K: float,
    exit_temp_K: float = 268.15,
    composition: Optional[Composition] = None,
) -> EnergyBalance:
    """
    Energy for freezer (SSHE): dasher power + cooling load.

    Cooling load: latent heat of ice formation + sensible cooling.
    Dasher is the dominant mechanical load; refrigeration is the dominant thermal load.
    """
    motor_power = motor_electrical_power_from_shaft(dasher_shaft_power_W)

    # Cooling load = mass × cp × (T_in - T_out) + latent heat of water frozen
    comp = composition or Composition(fat=0.15, sugar=0.125, water=0.68, solids=0.045)
    cp = phys.specific_heat_mix_J_kgK(comp)
    t_in_k = 278.15  # ~5°C entering freezer (from ageing vat)
    sensible_cooling_J = mass_kg * cp * (t_in_k - exit_temp_K)

    # Latent heat of ice: ~334 kJ/kg; assume ~25–30% of product becomes ice
    ice_fraction = 0.28  # typical for soft-serve ice cream
    latent_heat_J_kg = 334000.0  # J/kg
    latent_cooling_J = ice_fraction * mass_kg * latent_heat_J_kg

    total_cooling_J = sensible_cooling_J + latent_cooling_J

    cop = refrigeration_cop(coolant_temp_K)
    refrig_electrical_J = total_cooling_J / cop if cop > 0 else 0.0

    return EnergyBalance(
        stage_name="freezer",
        electrical_shaft_W=dasher_shaft_power_W,
        electrical_motor_W=motor_power,
        refrigeration_J=total_cooling_J,
        refrigeration_electrical_J=refrig_electrical_J,
    )


def energy_hardening(
    mass_kg: float,
    heat_removed_J: float,
    duration_s: float = 3600.0,
    hardening_temp_K: float = 243.15,
) -> EnergyBalance:
    """
    Energy for hardening tunnel: refrigeration load.

    Removes residual heat and brings product to -18°C.
    """
    cop = refrigeration_cop(hardening_temp_K)
    electrical_J = heat_removed_J / cop if cop > 0 else 0.0
    return EnergyBalance(
        stage_name="hardening",
        refrigeration_J=heat_removed_J,
        refrigeration_electrical_J=electrical_J,
    )


def energy_cavitation(
    mass_wastewater_kg: float,
    energy_proxy_kWh: float,
) -> EnergyBalance:
    """Energy for hydrodynamic cavitation: electrical pump/circulation."""
    electrical_J = energy_proxy_kWh * 3.6e6
    return EnergyBalance(
        stage_name="hydrodynamic_cavitation",
        electrical_motor_W=energy_proxy_kWh * 1000.0 / 3600.0,  # Rough conversion
        electrical_shaft_W=energy_proxy_kWh * 1000.0 / 3600.0 * 0.85,  # Account for motor eff
    )


# ============================================================================
# Aggregation
# ============================================================================


def aggregate_energy_report(balances: list[EnergyBalance]) -> dict:
    """Summarize per-stage and total energy."""
    total_thermal_J = sum(b.total_thermal_J for b in balances)
    total_electrical_J = sum(b.total_electrical_J for b in balances)
    total_J = sum(b.total_J for b in balances)

    return {
        "by_stage": [b.to_dict() for b in balances],
        "total_thermal_J": total_thermal_J,
        "total_electrical_J": total_electrical_J,
        "total_J": total_J,
        "total_kWh": total_J / 3.6e6,
        "thermal_fraction": (
            total_thermal_J / max(total_J, 1.0) if total_J > 0 else 0.0
        ),
        "electrical_fraction": (
            total_electrical_J / max(total_J, 1.0) if total_J > 0 else 0.0
        ),
    }


__all__ = [
    "EnergyBalance",
    "thermal_conductivity_W_mK",
    "tank_u_value_W_m2K",
    "tank_surface_loss_J",
    "motor_efficiency_fraction",
    "motor_electrical_power_from_shaft",
    "homogenizer_power_W",
    "refrigeration_cop",
    "phe_effectiveness",
    "energy_preparation_mix",
    "energy_pasteurization",
    "energy_homogenization",
    "energy_cooling",
    "energy_ageing",
    "energy_freezer",
    "energy_hardening",
    "energy_cavitation",
    "aggregate_energy_report",
]
