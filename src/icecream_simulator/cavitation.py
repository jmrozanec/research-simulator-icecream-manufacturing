"""
Hydrodynamic cavitation (HC) treatment of wastewater before nanofiltration.

Cavitation collapses vapor bubbles, producing localized high shear, shock waves, and
·OH radicals. Reported effects include partial **mineralisation** of organics (lower COD)
and **mechanical fragmentation** of biopolymers (proteins, lipids, polysaccharides) into
smaller molecules—often observed as improved biodegradability or shifted size distributions,
even when total COD changes modestly.

This module uses a compact **two-path model** aligned with common HC wastewater studies:
(1) first-order-like **COD/BOD removal** vs. hydrodynamic intensity and residence time;
(2) **chain scission** of a “macro-organic” pool (proxied from TSS + FOG) into dissolved
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


class CavitationConfig(BaseModel):
    """
    Operating and kinetic parameters for the cavitation stage.

    ``pressure_drop_bar`` and ``inlet_pressure_bar`` drive a crude cavitation intensity
    proxy; ``residence_time_s`` scales contact time for oxidation and shear.
    """

    inlet_pressure_bar: float = Field(default=3.5, ge=0.5, description="Upstream pressure (Venturi/orifice feed)")
    pressure_drop_bar: float = Field(default=1.2, ge=0.1, description="Pressure drop across constriction (HC driver)")
    residence_time_s: float = Field(default=45.0, ge=1.0, description="Effective exposure time in cavitation zone")
    # Kinetic caps (tune to pilot data)
    cod_removal_max_fraction: float = Field(default=0.38, le=0.7, description="Asymptotic max COD removal fraction")
    k_oxidation_1_per_s: float = Field(default=0.018, description="Pseudo-first-order rate scale for oxidation path")
    chain_scission_max_fraction: float = Field(
        default=0.42,
        le=0.8,
        description="Max fraction of macro-organic pool converted to small fragments per pass",
    )
    k_scission_1_per_s: float = Field(default=0.022, description="Rate scale for mechanical scission")
    tss_to_dissolved_cod_yield: float = Field(
        default=0.55,
        le=1.0,
        description="kg COD equivalent released per kg TSS disrupted into colloidal/dissolved form",
    )
    fog_fragilization_fraction: float = Field(
        default=0.35,
        le=0.9,
        description="Fraction of FOG subject to emulsion breakup / smaller droplets",
    )


def _cavitation_intensity(config: CavitationConfig) -> float:
    """Dimensionless intensity 0–1 from pressure drop and inlet pressure (Venturi-type HC)."""
    p_in = max(config.inlet_pressure_bar, 0.5)
    dp = max(config.pressure_drop_bar, 0.05)
    # Higher dp/p_in encourages stronger cavitation (bounded)
    raw = math.sqrt(dp / p_in) * (1.0 - math.exp(-dp / 2.0))
    return min(1.0, max(0.0, raw * 1.4))


def _removal_fraction(intensity: float, residence_time_s: float, k: float, max_eta: float) -> float:
    """1 - exp(-k * t * intensity), capped."""
    t = max(residence_time_s, 1.0)
    eta = max_eta * (1.0 - math.exp(-k * t * (0.15 + 0.85 * intensity)))
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

    v = max(wastewater.volume_L, 1e-9)
    cod_before = wastewater.cod_mg_L
    bod_before = wastewater.bod_mg_L
    tss_kg = (wastewater.tss_mg_L * 1e-6) * v
    fog_kg = (wastewater.fog_mg_L * 1e-6) * v

    # Path 1: partial mineralisation (·OH / indirect oxidation)
    eta_cod = _removal_fraction(
        intensity, cfg.residence_time_s, cfg.k_oxidation_1_per_s, cfg.cod_removal_max_fraction
    )
    eta_bod = eta_cod * 0.92
    cod_after_oxid = cod_before * (1.0 - eta_cod)
    bod_after_oxid = bod_before * (1.0 - eta_bod)

    # Path 2: mechanical scission — macromolecules → smaller fragments; some TSS → dissolved organics
    macro_kg = max(0.0, tss_kg * 0.45 + fog_kg * 0.85)
    eta_sci = _removal_fraction(
        intensity, cfg.residence_time_s, cfg.k_scission_1_per_s, cfg.chain_scission_max_fraction
    )
    fragmented_kg = macro_kg * eta_sci
    tss_disrupted_kg = min(tss_kg * 0.45, fragmented_kg * 0.55)
    tss_after_kg = max(0.0, tss_kg - tss_disrupted_kg)
    extra_cod_mg_L = (fragmented_kg * cfg.tss_to_dissolved_cod_yield * 1e6 / v) if v > 0 else 0.0

    # Net dissolved COD: oxidation wins on bulk, but fragmentation adds measurable COD
    cod_after = max(0.0, cod_after_oxid + extra_cod_mg_L * 0.35)
    bod_after = max(0.0, bod_after_oxid + extra_cod_mg_L * 0.12)

    fog_after_kg = fog_kg * (1.0 - cfg.fog_fragilization_fraction * intensity * 0.8)
    fog_mg_L_after = (fog_after_kg * 1e6 / v) if v > 0 else 0.0
    tss_mg_L_after = (tss_after_kg * 1e6 / v) if v > 0 else 0.0

    # Mean molecular weight index: 1 = large polymers, 0 = small fragments (inverse scale)
    mw_index_before = 1.0
    mw_index_after = max(0.12, mw_index_before * (1.0 - 0.75 * eta_sci) * (1.0 - 0.2 * intensity))

    # Bioavailability proxy for downstream bioconversion (more labile carbon after HC)
    bioavailability_factor = 1.0 + 0.15 * eta_sci + 0.08 * (1.0 - mw_index_after)

    out = WastewaterStream(
        volume_L=wastewater.volume_L,
        mass_kg=wastewater.mass_kg,
        temperature_K=wastewater.temperature_K + 0.5,
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

    # Pumping energy proxy (kWh/m3 order of magnitude for recirculating HC loop)
    q_m3_s = v / 1000.0 / max(cfg.residence_time_s, 1.0)
    energy_proxy_kwh = 0.011 * q_m3_s * cfg.pressure_drop_bar * cfg.residence_time_s * 3600.0

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
