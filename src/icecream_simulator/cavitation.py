"""
Hydrodynamic cavitation (HC) treatment of wastewater before nanofiltration.

Cavitation collapses vapor bubbles, producing localized high shear, shock waves, and
·OH radicals. Reported effects include partial **mineralisation** of organics (lower COD)
and **mechanical fragmentation** of biopolymers (proteins, lipids, polysaccharides) into
smaller molecules—often observed as improved biodegradability or shifted size distributions,
even when total COD changes modestly.

This module uses a compact **two-path model** aligned with common HC wastewater studies:
(1) first-order-like **COD/BOD removal** vs. hydrodynamic intensity and residence time;
(2) **chain scission** of a "macro-organic" pool (proxied from TSS + FOG) into dissolved
fragments, increasing bioavailability proxy and slightly affecting BOD/COD ratio.

**References (peer-reviewed):** Gogate & Pandit (2004) two-part review in *Advances in Environmental
Research* on ambient oxidation technologies for wastewater (Part I) and hybrid methods (Part II);
Gogate & Pandit (2000) *AIChE Journal* on engineering design of **hydrodynamic** cavitation reactors
(pressure drop, operating conditions). Full citations and DOIs: ``docs/WATER_TREATMENT_CAVITATION.md``.
Coefficients below are **tunable** via ``CavitationConfig`` to match pilot or literature operating maps.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from icecream_simulator.batch_models import WastewaterStream
from icecream_simulator import constants as C


class CavitationConfig(BaseModel):
    """
    Operating and kinetic parameters for the cavitation stage.

    ``pressure_drop_bar`` and ``inlet_pressure_bar`` drive a crude cavitation intensity
    proxy; ``residence_time_s`` scales contact time for oxidation and shear.
    """

    inlet_pressure_bar: float = Field(
        default=C.CAV_DEFAULT_INLET_PRESSURE_BAR, ge=C.CAV_INLET_PRESSURE_FLOOR_BAR,
        description="Upstream pressure (Venturi/orifice feed)",
    )
    pressure_drop_bar: float = Field(
        default=C.CAV_DEFAULT_PRESSURE_DROP_BAR, ge=0.1,
        description="Pressure drop across constriction (HC driver)",
    )
    residence_time_s: float = Field(
        default=C.CAV_DEFAULT_RESIDENCE_TIME_S, ge=C.CAV_TIME_FLOOR_S,
        description="Effective exposure time in cavitation zone",
    )
    cod_removal_max_fraction: float = Field(
        default=C.CAV_DEFAULT_COD_REMOVAL_MAX, le=0.7,
        description="Asymptotic max COD removal fraction",
    )
    k_oxidation_1_per_s: float = Field(
        default=C.CAV_DEFAULT_K_OXIDATION_1_PER_S,
        description="Pseudo-first-order rate scale for oxidation path",
    )
    chain_scission_max_fraction: float = Field(
        default=C.CAV_DEFAULT_CHAIN_SCISSION_MAX, le=0.8,
        description="Max fraction of macro-organic pool converted to small fragments per pass",
    )
    k_scission_1_per_s: float = Field(
        default=C.CAV_DEFAULT_K_SCISSION_1_PER_S,
        description="Rate scale for mechanical scission",
    )
    tss_to_dissolved_cod_yield: float = Field(
        default=C.CAV_DEFAULT_TSS_TO_DISSOLVED_COD_YIELD, le=1.0,
        description="kg COD equivalent released per kg TSS disrupted into colloidal/dissolved form",
    )
    fog_fragilization_fraction: float = Field(
        default=C.CAV_DEFAULT_FOG_FRAGILIZATION, le=0.9,
        description="Fraction of FOG subject to emulsion breakup / smaller droplets",
    )


def _cavitation_intensity(config: CavitationConfig) -> float:
    """Dimensionless intensity 0–1 from pressure drop and inlet pressure (Venturi-type HC)."""
    p_in = max(config.inlet_pressure_bar, C.CAV_INLET_PRESSURE_FLOOR_BAR)
    dp = max(config.pressure_drop_bar, C.CAV_PRESSURE_DROP_FLOOR_BAR)
    raw = math.sqrt(dp / p_in) * (1.0 - math.exp(-dp / C.CAV_INTENSITY_DP_DECAY_BAR))
    return min(1.0, max(0.0, raw * C.CAV_INTENSITY_PROXY_GAIN))


def _removal_fraction(intensity: float, residence_time_s: float, k: float, max_eta: float) -> float:
    """1 - exp(-k * t * intensity), capped."""
    t = max(residence_time_s, C.CAV_TIME_FLOOR_S)
    eta = max_eta * (
        1.0
        - math.exp(-k * t * (C.CAV_INTENSITY_FLOOR + (1.0 - C.CAV_INTENSITY_FLOOR) * intensity))
    )
    return min(max_eta, max(0.0, eta))


def run_hydrodynamic_cavitation(
    wastewater: WastewaterStream,
    config: CavitationConfig | None = None,
) -> tuple[WastewaterStream, dict]:
    """
    Apply HC: reduce COD/BOD by oxidation, fragment macromolecules, partially solubilise TSS/FOG.

    Returns updated ``WastewaterStream`` and a report dict (removals, indices, energy proxy).
    """
    cfg = config or CavitationConfig()
    intensity = _cavitation_intensity(cfg)

    v = max(wastewater.volume_L, C.CAV_VOLUME_FLOOR_L)
    cod_before = wastewater.cod_mg_L
    bod_before = wastewater.bod_mg_L
    tss_kg = (wastewater.tss_mg_L * C.KG_PER_MG) * v
    fog_kg = (wastewater.fog_mg_L * C.KG_PER_MG) * v

    eta_cod = _removal_fraction(
        intensity, cfg.residence_time_s, cfg.k_oxidation_1_per_s, cfg.cod_removal_max_fraction
    )
    eta_bod = eta_cod * C.CAV_BOD_TO_COD_REMOVAL_RATIO
    cod_after_oxid = cod_before * (1.0 - eta_cod)
    bod_after_oxid = bod_before * (1.0 - eta_bod)

    macro_kg = max(0.0, tss_kg * C.CAV_MACRO_TSS_FRACTION + fog_kg * C.CAV_MACRO_FOG_FRACTION)
    eta_sci = _removal_fraction(
        intensity, cfg.residence_time_s, cfg.k_scission_1_per_s, cfg.chain_scission_max_fraction
    )
    fragmented_kg = macro_kg * eta_sci
    tss_disrupted_kg = min(tss_kg * C.CAV_MACRO_TSS_FRACTION, fragmented_kg * C.CAV_TSS_DISRUPTION_FRACTION)
    tss_after_kg = max(0.0, tss_kg - tss_disrupted_kg)
    extra_cod_mg_L = (
        (fragmented_kg * cfg.tss_to_dissolved_cod_yield * C.MG_PER_KG / v) if v > 0 else 0.0
    )

    cod_after = max(0.0, cod_after_oxid + extra_cod_mg_L * C.CAV_EXTRA_COD_TO_COD_FACTOR)
    bod_after = max(0.0, bod_after_oxid + extra_cod_mg_L * C.CAV_EXTRA_COD_TO_BOD_FACTOR)

    fog_after_kg = fog_kg * (
        1.0 - cfg.fog_fragilization_fraction * intensity * C.CAV_FOG_DEPLETION_INTENSITY_COEFF
    )
    fog_mg_L_after = (fog_after_kg * C.MG_PER_KG / v) if v > 0 else 0.0
    tss_mg_L_after = (tss_after_kg * C.MG_PER_KG / v) if v > 0 else 0.0

    mw_index_before = C.CAV_MW_INDEX_BEFORE
    mw_index_after = max(
        C.CAV_MW_INDEX_FLOOR,
        mw_index_before
        * (1.0 - C.CAV_MW_INDEX_SCISSION_COEFF * eta_sci)
        * (1.0 - C.CAV_MW_INDEX_INTENSITY_COEFF * intensity),
    )

    bioavailability_factor = (
        1.0
        + C.CAV_BIOAVAIL_SCISSION_COEFF * eta_sci
        + C.CAV_BIOAVAIL_MW_COEFF * (1.0 - mw_index_after)
    )

    out = WastewaterStream(
        volume_L=wastewater.volume_L,
        mass_kg=wastewater.mass_kg,
        temperature_K=wastewater.temperature_K + C.CAV_OUTLET_TEMP_RISE_K,
        tss_mg_L=tss_mg_L_after,
        dissolved_sugar_kg=wastewater.dissolved_sugar_kg,
        cod_mg_L=cod_after,
        bod_mg_L=bod_after,
        fog_mg_L=fog_mg_L_after,
        metadata={
            **wastewater.metadata,
            "stage": "hydrodynamic_cavitation",
            "cavitation_intensity": intensity,
            "cod_removal_fraction": eta_cod,
            "bod_removal_fraction": eta_bod,
            "chain_scission_fraction": eta_sci,
            "mean_mw_index_before": mw_index_before,
            "mean_mw_index_after": mw_index_after,
            "bioavailability_factor": bioavailability_factor,
            "macro_organic_fragmented_kg": fragmented_kg,
            "inlet_pressure_bar": cfg.inlet_pressure_bar,
            "pressure_drop_bar": cfg.pressure_drop_bar,
            "residence_time_s": cfg.residence_time_s,
        },
    )

    q_m3_s = v / 1000.0 / max(cfg.residence_time_s, C.CAV_TIME_FLOOR_S)
    energy_proxy_kwh = (
        C.CAV_PUMPING_ENERGY_COEFF_KWH * q_m3_s * cfg.pressure_drop_bar * cfg.residence_time_s * 3600.0
    )

    report = {
        "cod_mg_L_before": cod_before,
        "cod_mg_L_after": out.cod_mg_L,
        "bod_mg_L_before": bod_before,
        "bod_mg_L_after": out.bod_mg_L,
        "tss_mg_L_before": wastewater.tss_mg_L,
        "tss_mg_L_after": out.tss_mg_L,
        "fog_mg_L_before": wastewater.fog_mg_L,
        "fog_mg_L_after": out.fog_mg_L,
        "cavitation_intensity": intensity,
        "mean_mw_index_after": mw_index_after,
        "bioavailability_factor": bioavailability_factor,
        "energy_proxy_kwh": energy_proxy_kwh,
    }
    return out, report
