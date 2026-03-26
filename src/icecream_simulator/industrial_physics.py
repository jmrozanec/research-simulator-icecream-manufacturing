"""
Physics correlations for the industrial ice cream chain.

Includes composition-based heat capacity, pasteurization lethality, homogenized fat
globule diameter (Walstra), ageing fat crystallinity, **wall vs bulk** ice crystal
populations (Cook & Hartel), **Gompertz and Avrami** frozen-water kinetics, barrel
recrystallization, optional **storage-time** Ostwald ripening, Kelvin (Gibbs–Thomson)
depression, SSHE dasher power, and hardness / melt proxies. Hydrocolloid and
emulsifier mass fractions (from batch metadata) modulate viscosity and crystal physics.
References are noted in each function docstring. **Wall vs bulk ice** and crystallization narratives follow
Cook & Hartel (2010), *Comprehensive Reviews in Food Science and Food Safety*, 9(2), 213–222.
https://doi.org/10.1111/j.1541-4337.2009.00101.x — preset ``COOK_HARTEL_CRYSTALLIZATION_REFERENCE`` / ``icecream-04.pdf``.
**Gompertz** kinetics align with Giudici et al. (2021), *Foods* 10(2), 334. https://doi.org/10.3390/foods10020334
"""

from __future__ import annotations

import math

from icecream_simulator.batch_models import Composition
from icecream_simulator.crystallization_parameters import (
    DEFAULT_CRYSTALLIZATION_PARAMETERS,
    CrystallizationParameters,
)

# Specific heats (J/(kg·K)) — food engineering handbook values
CP_WATER = 4180.0
CP_FAT = 2010.0
CP_SUGAR = 1450.0
CP_SOLIDS_MSNF = 1550.0


def specific_heat_mix_J_kgK(comp: Composition) -> float:
    """
    Mass-fraction-weighted specific heat of the mix (ideal mixing).

    Cp ≈ Σ w_i Cp_i (Singh & Heldman, food properties).
    """
    w = comp.water + comp.fat + comp.sugar + comp.solids
    if w <= 0:
        return CP_WATER
    # Renormalize if fractions do not sum to 1
    fw = comp.fat / w
    sw = comp.sugar / w
    ww = comp.water / w
    sow = comp.solids / w
    return fw * CP_FAT + sw * CP_SUGAR + ww * CP_WATER + sow * CP_SOLIDS_MSNF


def pasteurization_d_value_minutes_at_T_C(T_celsius: float, d_ref_min: float, t_ref_c: float, z_c: float) -> float:
    """
    D-value (decimal reduction time in minutes) at T for isothermal hold.

    log10(D(T)/D_ref) = (T_ref - T) / z  =>  D(T) = D_ref * 10^((T_ref - T) / z).

    Typical milk ice cream mix: D for Listeria ~0.2 min at 72 °C, z ≈ 7 °C (ICMSF / dairy thermal processing).
    """
    return d_ref_min * (10.0 ** ((t_ref_c - T_celsius) / z_c))


def pasteurization_log10_reduction(t_hold_s: float, T_celsius: float, d_ref_min: float = 0.2, t_ref_c: float = 72.0, z_c: float = 7.0) -> float:
    """
    Log10 microbial reduction during isothermal hold at T_celsius for t_hold_s.

    log10(N0/N) = t_min / D(T)  (first-order Bigelow; t in minutes, D in minutes).
    Capped at 6 logs (practical detection limit for “sterile” claim avoidance in model).
    """
    t_min = t_hold_s / 60.0
    if t_min <= 0 or T_celsius < 60.0:
        return 0.0
    d_t = pasteurization_d_value_minutes_at_T_C(T_celsius, d_ref_min, t_ref_c, z_c)
    if d_t <= 1e-9:
        return 6.0
    return min(6.0, t_min / d_t)


def homogenization_fat_globule_d32_um(pressure_bar: float, d32_ref_um: float = 0.85, p_ref_bar: float = 200.0, exponent: float = 0.45) -> float:
    """
    Volume–surface mean fat globule diameter after single-stage homogenization.

    Empirical scaling d32 ∝ P^(-b), b ≈ 0.4–0.6 for dairy (Walstra, Dairy Technology).
    d32_um = d32_ref * (P_ref / P)^exponent.
    """
    p = max(pressure_bar, 1.0)
    return d32_ref_um * ((p_ref_bar / p) ** exponent)


def homogenization_apparent_viscosity_Pa_s(mu_in: float, d32_um: float, d32_in_um: float, exponent: float = 0.25) -> float:
    """
    Apparent viscosity after homogenization from finer emulsion (Pal–Rhodes-type).

    μ_rel ≈ (d32_in / d32)^exp for shear-thinning dairy emulsion (order-of-magnitude).
    """
    if d32_um <= 0:
        return mu_in
    ratio = max(d32_in_um, 1e-6) / max(d32_um, 1e-6)
    return mu_in * (ratio ** exponent)


def ageing_fat_crystallinity_fraction(ageing_time_h: float, hold_temp_K: float, tau_h: float = 4.0, t_milk_fat_K: float = 290.0) -> float:
    """
    Fraction of crystallizable milk fat that has crystallized during ageing (first-order).

    X = X_max * (1 - exp(-t/tau)); X_max increases as T approaches milk fat melting zone.
    tau ~ few hours at 4 °C (Hartel, ice cream crystallization).
    """
    x_max = min(0.75, 0.5 + 0.25 * max(0.0, (t_milk_fat_K - hold_temp_K) / 15.0))
    return x_max * (1.0 - math.exp(-max(0.0, ageing_time_h) / max(tau_h, 0.1)))


def ageing_viscosity_after_crystallinity(mu_in: float, crystallinity: float) -> float:
    """Partial fat crystallization increases effective viscosity (crystal network)."""
    return mu_in * (1.0 + 0.35 * crystallinity)


def ice_crystal_mean_um_sshe(
    residence_time_s: float,
    coolant_temp_K: float,
    dasher_rpm: float,
    product_exit_temp_K: float,
    params: CrystallizationParameters | None = None,
) -> float:
    """
    Legacy single-population mean ice crystal size (µm) — volume mean of wall + bulk
    with default hydrocolloid/emulsifier fractions of zero.

    Prefer :func:`ice_crystal_volume_mean_um_sshe` for research-grade wall vs bulk resolution.
    """
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    d_w = ice_crystal_wall_um_sshe(
        residence_time_s, coolant_temp_K, dasher_rpm, product_exit_temp_K, 0.0, 0.0, params=p
    )
    d_b = ice_crystal_bulk_um_sshe(
        residence_time_s, coolant_temp_K, dasher_rpm, product_exit_temp_K, 0.0, 0.0, params=p
    )
    return ice_crystal_volume_mean_um_from_wall_bulk(d_w, d_b, volume_fraction_wall_ice=0.28, params=p)


def ice_crystal_wall_um_sshe(
    residence_time_s: float,
    coolant_temp_K: float,
    dasher_rpm: float,
    product_exit_temp_K: float,
    hydrocolloid_mass_fraction: float,
    emulsifier_mass_fraction: float,
    params: CrystallizationParameters | None = None,
) -> float:
    """
    Wall-region mean crystal size (µm): high undercooling and shear at the scraped surface
    (Cook & Hartel: nucleation-dominated, finer crystals than bulk).

    Hydrocolloids and emulsifiers slightly reduce effective wall crystal size (growth limitation).
    """
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    t_res = max(residence_time_s, 5.0)
    w_h = min(p.wall_max_hydrocolloid_fraction, max(0.0, float(hydrocolloid_mass_fraction)))
    w_e = min(p.wall_max_emulsifier_fraction, max(0.0, float(emulsifier_mass_fraction)))
    delta_t = max(1.0, product_exit_temp_K - coolant_temp_K)
    base = p.wall_base_offset_um + p.wall_base_scale_um * math.exp(-t_res / p.wall_residence_decay_s)
    wall_undercool = 1.0 / (1.0 + p.wall_delta_T_coeff * delta_t)
    friction = 1.0 + p.wall_friction_rpm_sq_coeff * (dasher_rpm - p.wall_dasher_rpm_ref) ** 2
    d = base * wall_undercool * friction
    d *= 1.0 - p.wall_hydrocolloid_suppression * w_h - p.wall_emulsifier_suppression * w_e
    return max(p.wall_d_min_um, min(p.wall_d_max_um, d))


def ice_crystal_bulk_um_sshe(
    residence_time_s: float,
    coolant_temp_K: float,
    dasher_rpm: float,
    product_exit_temp_K: float,
    hydrocolloid_mass_fraction: float,
    emulsifier_mass_fraction: float,
    params: CrystallizationParameters | None = None,
) -> float:
    """
    Bulk mean crystal size (µm): growth- and ripening-dominated, coarser than wall ice
    (Cook & Hartel).

    Hydrocolloids suppress ice growth (smaller bulk crystals); emulsifiers have a mild effect.
    """
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    t_res = max(residence_time_s, 5.0)
    w_h = min(p.bulk_max_hydrocolloid_fraction, max(0.0, float(hydrocolloid_mass_fraction)))
    w_e = min(p.bulk_max_emulsifier_fraction, max(0.0, float(emulsifier_mass_fraction)))
    delta_t = max(1.0, product_exit_temp_K - coolant_temp_K)
    base = p.bulk_base_offset_um + p.bulk_base_scale_um * math.exp(-t_res / p.bulk_residence_decay_s)
    nucleation_factor = 1.0 / (1.0 + p.bulk_nucleation_delta_coeff * delta_t)
    friction_factor = 1.0 + p.bulk_friction_rpm_sq_coeff * (dasher_rpm - p.bulk_dasher_rpm_ref) ** 2
    d = base * nucleation_factor * friction_factor
    d *= 1.0 - p.bulk_hydrocolloid_suppression * w_h - p.bulk_emulsifier_suppression * w_e
    return max(p.bulk_d_min_um, min(p.bulk_d_max_um, d))


def ice_crystal_volume_mean_um_from_wall_bulk(
    d_wall_um: float,
    d_bulk_um: float,
    volume_fraction_wall_ice: float = 0.28,
    params: CrystallizationParameters | None = None,
) -> float:
    """
    Volume-weighted mean diameter from wall and bulk populations (Cook & Hartel: ~15–35 %
    of ice mass can associate with wall layers depending on SSHE and heat flux).

    Uses d_mean = (f_w * d_w³ + (1 - f_w) * d_b³)^(1/3).
    """
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    f_w = min(p.volume_mean_f_wall_max, max(p.volume_mean_f_wall_min, float(volume_fraction_wall_ice)))
    dw = max(float(d_wall_um), 1e-6)
    db = max(float(d_bulk_um), 1e-6)
    return (f_w * dw**3 + (1.0 - f_w) * db**3) ** (1.0 / 3.0)


def ice_crystal_volume_mean_um_sshe(
    residence_time_s: float,
    coolant_temp_K: float,
    dasher_rpm: float,
    product_exit_temp_K: float,
    hydrocolloid_mass_fraction: float,
    emulsifier_mass_fraction: float,
    volume_fraction_wall_ice: float = 0.28,
    params: CrystallizationParameters | None = None,
) -> tuple[float, float, float]:
    """
    Returns (d_wall_um, d_bulk_um, d_volume_mean_um) for SSHE ice populations.
    """
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    d_w = ice_crystal_wall_um_sshe(
        residence_time_s,
        coolant_temp_K,
        dasher_rpm,
        product_exit_temp_K,
        hydrocolloid_mass_fraction,
        emulsifier_mass_fraction,
        params=p,
    )
    d_b = ice_crystal_bulk_um_sshe(
        residence_time_s,
        coolant_temp_K,
        dasher_rpm,
        product_exit_temp_K,
        hydrocolloid_mass_fraction,
        emulsifier_mass_fraction,
        params=p,
    )
    d_v = ice_crystal_volume_mean_um_from_wall_bulk(d_w, d_b, volume_fraction_wall_ice, params=p)
    return d_w, d_b, d_v


def freezer_dasher_shaft_power_W(dynamic_viscosity_Pa_s: float, dasher_rpm: float, barrel_diameter_m: float = 0.15, k_power: float = 2.0) -> float:
    """
    Shaft power for scraped-surface rotor (laminar analog P ∝ μ N² D³).

    Same form as mixer power number; k_power groups geometry.
    """
    n = dasher_rpm / 60.0
    d = barrel_diameter_m
    return k_power * dynamic_viscosity_Pa_s * (n**2) * (d**3)


def freezer_effective_overrun(
    target_overrun: float,
    dasher_rpm: float,
    residence_time_s: float,
    air_injection_efficiency: float = 0.92,
) -> float:
    """
    Effective overrun fraction accounting for dasher shear and residence (air incorporation).

    Overrun realized ≈ η_air * target_overrun * (1 - k_loss / (t_res * rpm_scale)).
    """
    t_res = max(residence_time_s, 5.0)
    shear_factor = 1.0 - 0.08 * math.exp(-t_res / 200.0) * (1.0 + 0.002 * abs(dasher_rpm - 55.0))
    return max(0.05, min(1.2, air_injection_efficiency * target_overrun * shear_factor))


def hardness_proxy_kPa(
    ice_crystal_mean_um: float,
    overrun_fraction: float,
    hardening_temp_K: float,
    frozen_water_fraction: float | None = None,
    params: CrystallizationParameters | None = None,
) -> float:
    """
    Empirical hardness proxy (kPa scale): harder with smaller crystals, lower overrun, lower temperature.

    Optional ``frozen_water_fraction`` (Gompertz SSHE proxy) scales hardness toward more ice phase.
    Order-of-magnitude aligned with penetrometry scales (not calibrated to a single product).
    """
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    t_c = hardening_temp_K - 273.15
    h = (p.hardness_scale / max(ice_crystal_mean_um, p.hardness_ice_denominator_um)) * (1.0 + overrun_fraction) * (
        1.0 + p.hardness_temp_coeff * abs(t_c + p.hardness_temp_offset_c)
    )
    if frozen_water_fraction is not None:
        fw = min(1.0, max(0.0, float(frozen_water_fraction)))
        h *= p.hardness_frozen_water_base + p.hardness_frozen_water_scale * fw
    return h


def melt_rate_proxy_per_s(hardness_kPa: float) -> float:
    """Inverse relationship: higher hardness → lower melt rate (relative scale)."""
    return 0.001 / max(hardness_kPa, 1.0)


def initial_freezing_point_mix_celsius(
    comp: Composition,
    params: CrystallizationParameters | None = None,
) -> float:
    """
    Empirical initial (equilibrium) freezing point of the unfrozen mix vs composition.

    Sweetened dairy mixes show depression below 0 °C; this is a simple monotonic
    proxy for reporting (not a full colligative or Gompertz crystallization fit).
    See Giudici et al. (2021) on initial freezing point and supercooling in batch freezing.
    """
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    w_s = max(0.0, min(0.5, comp.sugar))
    return p.ifp_offset_c + p.ifp_sugar_coefficient * w_s


def avrami_frozen_water_fraction_sshe(
    residence_time_s: float,
    initial_freezing_point_c: float,
    product_exit_temp_c: float,
    n_avrami: float | None = None,
    params: CrystallizationParameters | None = None,
) -> float:
    """
    Avrami–Erofeev-style frozen water fraction: X(t) ≈ X_max * (1 - exp(-(k t)^n)).

    Typical n ≈ 3 for three-dimensional ice growth; k scales with supercooling
    (Christian–Avrami theory; contrast with Gompertz sigmoid in Giudici-style fits).
    """
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    t_res = max(residence_time_s, 1.0)
    supercool = max(0.0, float(initial_freezing_point_c) - float(product_exit_temp_c))
    x_max = min(
        p.avrami_x_max_upper,
        max(p.avrami_x_max_lower, p.avrami_x_max_offset + p.avrami_x_max_supercool_coeff * supercool),
    )
    k = p.avrami_k_base * (1.0 + p.avrami_k_supercool_coeff * supercool)
    n_in = p.avrami_n_default if n_avrami is None else float(n_avrami)
    n = max(p.avrami_n_min, min(p.avrami_n_max, n_in))
    x_rel = 1.0 - math.exp(-((k * t_res) ** n))
    return x_max * min(1.0, max(0.0, x_rel))


def gompertz_frozen_water_fraction_sshe(
    residence_time_s: float,
    initial_freezing_point_c: float,
    product_exit_temp_c: float,
    params: CrystallizationParameters | None = None,
) -> float:
    """
    Gompertz-sigmoid proxy for frozen water fraction after SSHE (Giudici et al.–style
    crystallization kinetics; batch Gompertz adapted using residence time as characteristic time).

    X(t) = X_max * exp(-exp(-(t - t0) / tau)). Stronger undercooling (IFP above exit T)
    raises the asymptotic frozen fraction.
    """
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    t_res = max(residence_time_s, 1.0)
    supercool = float(initial_freezing_point_c) - float(product_exit_temp_c)
    x_max = min(
        p.gompertz_x_max_upper,
        max(
            p.gompertz_x_max_lower,
            p.gompertz_x_max_offset + p.gompertz_x_max_supercool_coeff * max(0.0, supercool),
        ),
    )
    t0 = p.gompertz_t0_offset + p.gompertz_t0_supercool_coeff * max(0.0, supercool)
    tau = p.gompertz_tau
    z = (t_res - t0) / max(tau, 1.0)
    g = math.exp(-math.exp(-z))
    return x_max * g


def ice_crystal_mean_um_after_recrystallization(
    primary_mean_um: float,
    residence_time_s: float,
    params: CrystallizationParameters | None = None,
) -> float:
    """
    Mean crystal size after coarsening / recrystallization in the freezer barrel (Cook & Hartel).

    Longer residence allows Ostwald-type ripening: d_mean increases slowly with time.
    """
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    t_res = max(residence_time_s, 5.0)
    factor = 1.0 + p.barrel_ripening_log_coeff * math.log1p(t_res / p.barrel_ripening_time_ref_s)
    d_out = primary_mean_um * factor
    return max(p.barrel_d_min_um, min(p.barrel_d_max_um, d_out))


def blended_frozen_water_fraction_kinetics(
    gompertz_X: float,
    avrami_X: float,
    params: CrystallizationParameters | None = None,
) -> float:
    """Weighted blend of Gompertz and Avrami ice fractions for reporting / hardness."""
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    wg = float(p.kinetic_blend_gompertz_weight)
    wa = float(p.kinetic_blend_avrami_weight)
    s = wg + wa
    if s <= 0:
        return 0.5 * (float(gompertz_X) + float(avrami_X))
    return (wg * float(gompertz_X) + wa * float(avrami_X)) / s


def storage_recrystallized_mean_um(
    mean_um_before_storage: float,
    storage_time_s: float,
    storage_temp_K: float,
    hydrocolloid_mass_fraction: float,
    emulsifier_mass_fraction: float,
    params: CrystallizationParameters | None = None,
) -> float:
    """
    Mean crystal size after distribution / hardening storage (Ostwald ripening; Hartel / Livney).

    Higher storage temperature and longer time increase coarsening; hydrocolloids retard it.
    """
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    t_s = max(0.0, float(storage_time_s))
    if t_s <= 1e-6:
        return float(mean_um_before_storage)
    w_h = min(p.storage_max_hydrocolloid_fraction, max(0.0, float(hydrocolloid_mass_fraction)))
    w_e = min(p.storage_max_emulsifier_fraction, max(0.0, float(emulsifier_mass_fraction)))
    t_c = storage_temp_K - 273.15
    arr = math.exp(
        min(p.storage_arr_exp_clip, max(-p.storage_arr_exp_clip, (t_c + p.storage_temp_arr_offset_c) / p.storage_temp_arr_divisor))
    )
    r = p.storage_r_scale * arr * math.log1p(t_s / 3600.0)
    r *= 1.0 - p.storage_hydrocolloid_retardation * w_h - p.storage_emulsifier_retardation * w_e
    d_in = max(float(mean_um_before_storage), 1e-6)
    d_out = d_in * (
        1.0
        + r
        * min(
            p.storage_diameter_amplification_cap,
            1.0 + d_in / p.storage_diameter_amplification_scale_um,
        )
    )
    return max(d_in, min(p.storage_d_max_um, d_out))


def kelvin_freezing_point_depression_K_for_ice_sphere_um(
    diameter_um: float,
    params: CrystallizationParameters | None = None,
) -> float:
    """
    Gibbs–Thomson / Kelvin-style melting-point shift for a spherical ice crystal.

    ΔT ≈ 4 γ T_m / (ρ_s L_f d) with d the diameter (m). Small crystals have slightly
    higher equilibrium melting T than bulk ice (Cook & Hartel; Hartel ice cream reviews).

    Returns depression magnitude in K (positive number meaning the small crystal is
    less stable than bulk ice at the same T).
    """
    p = params or DEFAULT_CRYSTALLIZATION_PARAMETERS
    d = max(float(diameter_um), p.kelvin_d_min_um) * 1e-6
    delta = 4.0 * p.kelvin_gamma_surface_tension * p.kelvin_T_m / (p.kelvin_rho_ice * p.kelvin_L_fusion * d)
    return min(p.kelvin_delta_max_K, max(0.0, delta))
