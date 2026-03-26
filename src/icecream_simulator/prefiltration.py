"""
Pre-filtration (coarse screening / straining) before cavitation and nanofiltration.

Removes a fraction of suspended solids to protect downstream hydrodynamic cavitation
and membrane units from fouling. Typical: static or drum screens, bag filters.

**Note:** Only **TSS** is reduced here in a conservative way; dissolved COD/BOD/FOG
pass through unchanged. Removed solid mass is reported for mass-balance checks.

Cavitation literature (DOIs) is listed in ``docs/WATER_TREATMENT_CAVITATION.md``; optional local
PDFs can live under ``papers/`` (see ``papers/README.md``).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from icecream_simulator.batch_models import WastewaterStream


class PrefiltrationConfig(BaseModel):
    """Coarse pre-filter: fraction of suspended solids removed (captured on screen)."""

    tss_removal_fraction: float = Field(
        default=0.62,
        ge=0.0,
        le=0.92,
        description="Fraction of TSS mass removed (typical 0.5–0.85 for dairy CIP pretreatment)",
    )


def run_prefiltration(
    wastewater: WastewaterStream,
    config: PrefiltrationConfig | None = None,
) -> tuple[WastewaterStream, dict]:
    """
    Reduce TSS concentration; volume and dissolved loads unchanged.

    Returns (stream_to_cavitation, report_dict).
    """
    cfg = config or PrefiltrationConfig()
    f = min(0.92, max(0.0, cfg.tss_removal_fraction))
    v = max(wastewater.volume_L, 1e-9)
    tss_kg = (wastewater.tss_mg_L * 1e-6) * v
    tss_removed_kg = tss_kg * f
    tss_mg_L_new = ((tss_kg - tss_removed_kg) * 1e6 / v) if v > 0 else 0.0

    out = WastewaterStream(
        volume_L=wastewater.volume_L,
        mass_kg=max(0.0, wastewater.mass_kg - tss_removed_kg),
        temperature_K=wastewater.temperature_K,
        tss_mg_L=tss_mg_L_new,
        dissolved_sugar_kg=wastewater.dissolved_sugar_kg,
        cod_mg_L=wastewater.cod_mg_L,
        bod_mg_L=wastewater.bod_mg_L,
        fog_mg_L=wastewater.fog_mg_L,
        metadata={
            **wastewater.metadata,
            "stage": "prefiltration",
            "tss_removal_fraction": f,
        },
    )
    report = {
        "tss_mg_L_before": wastewater.tss_mg_L,
        "tss_mg_L_after": out.tss_mg_L,
        "tss_removed_kg": tss_removed_kg,
    }
    return out, report
