"""
Tunable crystallization and texture parameters for ice cream simulation.

Defaults match the built-in correlations in ``industrial_physics``. Load overrides from
JSON or YAML (YAML requires PyYAML) to fit a product line or calibrate against lab data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CrystallizationParameters(BaseModel):
    """
    All coefficients used by the research-grade ice path (SSHE, kinetics, storage).

    You can treat this as a single “fit surface”: change only the fields your data
    constrains, leave the rest at defaults. The ``name`` field is for your own
    bookkeeping (e.g. ``"premium_vanilla_lab_fit_2024"``).
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(default="default", description="Label for this parameter set (not used in physics).")

    # --- Initial freezing point (empirical vs sugar) ---
    ifp_offset_c: float = Field(default=-0.35, description="Constant term in T_ifp (°C).")
    ifp_sugar_coefficient: float = Field(default=-4.15, description="Multiplier for sugar mass fraction in T_ifp.")

    # --- Wall ice (SSHE scraped surface) ---
    wall_d_min_um: float = 6.0
    wall_d_max_um: float = 55.0
    wall_base_offset_um: float = 8.0
    wall_base_scale_um: float = 22.0
    wall_residence_decay_s: float = 200.0
    wall_delta_T_coeff: float = 0.065
    wall_dasher_rpm_ref: float = 50.0
    wall_friction_rpm_sq_coeff: float = 0.00022
    wall_hydrocolloid_suppression: float = 0.28
    wall_emulsifier_suppression: float = 0.12
    wall_max_hydrocolloid_fraction: float = 0.05
    wall_max_emulsifier_fraction: float = 0.05

    # --- Bulk ice ---
    bulk_d_min_um: float = 12.0
    bulk_d_max_um: float = 125.0
    bulk_base_offset_um: float = 26.0
    bulk_base_scale_um: float = 72.0
    bulk_residence_decay_s: float = 280.0
    bulk_nucleation_delta_coeff: float = 0.038
    bulk_dasher_rpm_ref: float = 50.0
    bulk_friction_rpm_sq_coeff: float = 0.00026
    bulk_hydrocolloid_suppression: float = 0.36
    bulk_emulsifier_suppression: float = 0.06
    bulk_max_hydrocolloid_fraction: float = 0.05
    bulk_max_emulsifier_fraction: float = 0.05

    # --- Volume mean of wall + bulk ---
    volume_mean_f_wall_min: float = 0.10
    volume_mean_f_wall_max: float = 0.42

    # --- Avrami kinetics ---
    avrami_n_default: float = 3.0
    avrami_n_min: float = 1.0
    avrami_n_max: float = 4.0
    avrami_x_max_upper: float = 0.74
    avrami_x_max_lower: float = 0.08
    avrami_x_max_offset: float = 0.15
    avrami_x_max_supercool_coeff: float = 0.052
    avrami_k_base: float = 1.15e-3
    avrami_k_supercool_coeff: float = 0.11

    # --- Gompertz kinetics ---
    gompertz_x_max_upper: float = 0.72
    gompertz_x_max_lower: float = 0.08
    gompertz_x_max_offset: float = 0.18
    gompertz_x_max_supercool_coeff: float = 0.045
    gompertz_t0_offset: float = 20.0
    gompertz_t0_supercool_coeff: float = 0.5
    gompertz_tau: float = 40.0

    # --- Barrel (in-freezer) recrystallization ---
    barrel_ripening_log_coeff: float = 0.12
    barrel_ripening_time_ref_s: float = 120.0
    barrel_d_min_um: float = 12.0
    barrel_d_max_um: float = 150.0

    # --- Frozen-fraction blend for hardness (gompertz vs avrami) ---
    kinetic_blend_gompertz_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    kinetic_blend_avrami_weight: float = Field(default=0.5, ge=0.0, le=1.0)

    # --- Storage (post-hardening) ripening ---
    storage_r_scale: float = 0.055
    storage_temp_arr_divisor: float = 18.0
    storage_temp_arr_offset_c: float = 28.0
    storage_arr_exp_clip: float = 2.0
    storage_hydrocolloid_retardation: float = 0.45
    storage_emulsifier_retardation: float = 0.12
    storage_max_hydrocolloid_fraction: float = 0.06
    storage_max_emulsifier_fraction: float = 0.06
    storage_diameter_amplification_cap: float = 2.8
    storage_diameter_amplification_scale_um: float = 45.0
    storage_d_max_um: float = 200.0

    # --- Kelvin (Gibbs–Thomson) ---
    kelvin_gamma_surface_tension: float = 0.025
    kelvin_T_m: float = 273.15
    kelvin_rho_ice: float = 917.0
    kelvin_L_fusion: float = 334000.0
    kelvin_delta_max_K: float = 2.0
    kelvin_d_min_um: float = 0.05

    # --- Hardness proxy ---
    hardness_scale: float = 500.0
    hardness_ice_denominator_um: float = 10.0
    hardness_temp_offset_c: float = 30.0
    hardness_temp_coeff: float = 0.02
    hardness_frozen_water_base: float = 0.82
    hardness_frozen_water_scale: float = 0.28


DEFAULT_CRYSTALLIZATION_PARAMETERS = CrystallizationParameters()


def load_crystallization_parameters_from_json(path: str | Path) -> CrystallizationParameters:
    """Load parameters from a JSON file (UTF-8). Unknown keys are ignored."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    return CrystallizationParameters.model_validate_json(text)


def load_crystallization_parameters_from_yaml(path: str | Path) -> CrystallizationParameters:
    """Load parameters from a YAML file. Requires ``pip install pyyaml``."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as e:
        raise ImportError(
            "Loading YAML requires PyYAML. Install with: pip install pyyaml"
        ) from e
    p = Path(path)
    data: Any = yaml.safe_load(p.read_text(encoding="utf-8"))
    if data is None:
        return CrystallizationParameters()
    return CrystallizationParameters.model_validate(data)


def load_crystallization_parameters(path: str | Path) -> CrystallizationParameters:
    """
    Load from ``.json`` or ``.yaml`` / ``.yml`` based on the file suffix.
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return load_crystallization_parameters_from_json(path)
    if suffix in (".yaml", ".yml"):
        return load_crystallization_parameters_from_yaml(path)
    raise ValueError(f"Unsupported file type {suffix!r}; use .json, .yaml, or .yml")


def crystallization_parameters_to_json_dict(params: CrystallizationParameters) -> dict[str, Any]:
    """Serialize a parameter set to a JSON-compatible dict (for saving)."""
    return params.model_dump()
