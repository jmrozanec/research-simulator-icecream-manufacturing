"""
Literature-based ice cream mix presets (batch-scale ``RawMaterials`` + optional flavor).

Each preset ties a **coded recipe** to a PDF in ``papers/`` and to a **table or section**
in that paper. Masses are chosen so ``total_mass`` is typically **200 kg** for comparable
runs; where a paper gives **kg per kg of final ice cream** (LCA inventory), the mapping
to a single mix batch is **documented in ``notes``** and is approximate.

**Papers (repository filenames):**

- ``icecream-01.pdf`` — Harfoush et al. (2024), *Manufacturing Letters* 41, 170–181 (process review).
- ``icecream-02.pdf`` — Giudici et al. (2021), *Foods* 10, 334 (batch freezing, crystallization kinetics).
- ``icecream-03.pdf`` — Konstantas et al. (2019), *J. Cleaner Prod.* 209, 259–272 (LCA; Table 2 inventory).
- ``icecream-04.pdf`` — Cook & Hartel, mechanisms of ice crystallization (review; no recipe table).
- ``icecream-05.pdf`` — Wari & Zhu (2019), *Int. J. Prod. Res.* (scheduling; no formulation).

Run all presets::

    from icecream_simulator.literature_recipes import run_literature_suite
    rows = run_literature_suite(include_cleaning_phase=False)

Or one full cycle::

    from icecream_simulator.run_full_cycle import run_full_cycle
    run_full_cycle(literature_preset_id=\"GIUDICI_2021_INDUSTRIAL\")
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from icecream_simulator.schemas import RawMaterials


class LiteratureRecipePreset(BaseModel):
    """One named recipe with citation metadata."""

    id: str = Field(description="Stable preset id for ``run_full_cycle(literature_preset_id=...)``")
    citation: str
    paper_pdf: str = Field(description="PDF filename under papers/, e.g. icecream-02.pdf")
    table_or_section: str = Field(
        description="Table number, figure, or section anchor in the paper",
    )
    raw_materials: RawMaterials
    flavor_syrup_mass_kg: float = 0.0
    inclusion_mass_kg: float = 0.0
    notes: str = ""


# --- Presets (200 kg total raw mass unless noted) ---

LITERATURE_PRESETS: dict[str, LiteratureRecipePreset] = {
    "HARFOUSH_2024_BASELINE": LiteratureRecipePreset(
        id="HARFOUSH_2024_BASELINE",
        citation=(
            "Harfoush, A., Fan, Z., Goddik, L., & Haapala, K. R. (2024). "
            "A review of ice cream manufacturing process and system improvement strategies. "
            "Manufacturing Letters, 41, 170–181."
        ),
        paper_pdf="icecream-01.pdf",
        table_or_section="Fig. 2 (typical industrial step sequence); process narrative",
        raw_materials=RawMaterials(
            milk=100.0,
            cream=30.0,
            sugar=25.0,
            stabilizers=1.65,
            emulsifiers_kg=0.35,
            water=43.0,
        ),
        notes="Baseline 200 kg batch; hydrocolloid vs emulsifier split for research-grade physics.",
    ),
    "GIUDICI_2021_INDUSTRIAL": LiteratureRecipePreset(
        id="GIUDICI_2021_INDUSTRIAL",
        citation=(
            "Giudici, P., Baiano, A., Chiari, P., De Vero, L., Ghanbarzadeh, B., & Falcone, P. M. (2021). "
            "Industrial versus artisanal ice cream: Effects of freezing process on properties and microstructure. "
            "Foods, 10(2), 334. DOI 10.3390/foods10020334"
        ),
        paper_pdf="icecream-02.pdf",
        table_or_section="Table 2 (text): industrial-style composition — total solids up to ~42%; "
        "milk fat / MSNF / sweeteners / hydrocolloids up to 18%, 8%, 17%, 0.5%",
        raw_materials=RawMaterials(
            milk=90.0,
            cream=50.0,
            sugar=34.0,
            stabilizers=0.75,
            emulsifiers_kg=0.25,
            water=25.0,
        ),
        notes=(
            "Masses scaled to 200 kg with sugar ~17% and hydrocolloids 0.5% of batch; "
            "dairy split is illustrative (paper gives upper bounds, not a single recipe)."
        ),
    ),
    "GIUDICI_2021_ARTISANAL": LiteratureRecipePreset(
        id="GIUDICI_2021_ARTISANAL",
        citation=(
            "Giudici et al. (2021), Foods 10(2), 334 — artisanal / gelato-style composition."
        ),
        paper_pdf="icecream-02.pdf",
        table_or_section="Table 2 (text): artisanal — fat 8%, MSNF 7.5%, sweeteners 16%, "
        "hydrocolloids 0.2%; total solids up to ~32%",
        raw_materials=RawMaterials(
            milk=120.0,
            cream=25.0,
            sugar=32.0,
            stabilizers=0.3,
            emulsifiers_kg=0.1,
            water=22.6,
        ),
        notes="200 kg batch; sweetener and hydrocolloid levels match table text; dairy split illustrative.",
    ),
    "KONSTANTAS_2019_VANILLA_REGULAR": LiteratureRecipePreset(
        id="KONSTANTAS_2019_VANILLA_REGULAR",
        citation=(
            "Konstantas, A., Stamford, L., & Azapagic, A. (2019). "
            "Environmental impacts of ice cream and the influence of different ingredients and waste management options. "
            "Journal of Cleaner Production, 209, 259–272."
        ),
        paper_pdf="icecream-03.pdf",
        table_or_section="Table 2 — Vanilla regular: inventory kg/kg ice cream (cream 0.25, sugar 0.15, …)",
        raw_materials=RawMaterials(
            milk=84.2,
            cream=25.0,
            sugar=30.0,
            stabilizers=0.65,
            emulsifiers_kg=0.15,
            water=59.269,
            vanilla_extract_kg=0.73,
            vanillin_kg=0.001,
        ),
        notes=(
            "Stabilisers 0.004 kg/kg; vanilla extract 3.65e-3 kg/kg (0.73 kg/200 kg); "
            "vanillin as trace solids (0.001 kg). Table 2 LCI per kg product — process recipe only."
        ),
    ),
    "KONSTANTAS_2019_VANILLA_PREMIUM": LiteratureRecipePreset(
        id="KONSTANTAS_2019_VANILLA_PREMIUM",
        citation="Konstantas et al. (2019), J. Cleaner Prod. 209 — vanilla premium.",
        paper_pdf="icecream-03.pdf",
        table_or_section="Table 2 — Vanilla premium: cream 0.40, sugar 0.17, … per kg ice cream",
        raw_materials=RawMaterials(
            milk=75.0,
            cream=40.0,
            sugar=34.0,
            stabilizers=0.15,
            emulsifiers_kg=0.05,
            water=47.269,
            egg_yolk_kg=2.8,
            vanilla_extract_kg=0.73,
            vanillin_kg=0.001,
        ),
        notes=(
            "Table 2: cream 0.40, sugar 0.17, stabilisers 0.001, egg yolk 0.014 kg/kg → 2.8 kg/200 kg; "
            "vanilla extract scaled as in vanilla regular."
        ),
    ),
    "KONSTANTAS_2019_CHOCOLATE_REGULAR": LiteratureRecipePreset(
        id="KONSTANTAS_2019_CHOCOLATE_REGULAR",
        citation="Konstantas et al. (2019), J. Cleaner Prod. 209 — chocolate regular.",
        paper_pdf="icecream-03.pdf",
        table_or_section="Table 2 — Chocolate regular: cocoa powder 0.03 kg/kg ice cream",
        raw_materials=RawMaterials(
            milk=82.0,
            cream=25.0,
            sugar=30.0,
            stabilizers=0.5,
            emulsifiers_kg=0.1,
            cocoa_powder_kg=6.0,
            water=56.4,
        ),
        notes="Cocoa 0.03 kg/kg; stabilisers 0.003 kg/kg per Table 2.",
    ),
    "KONSTANTAS_2019_CHOCOLATE_PREMIUM": LiteratureRecipePreset(
        id="KONSTANTAS_2019_CHOCOLATE_PREMIUM",
        citation="Konstantas et al. (2019), J. Cleaner Prod. 209 — chocolate premium.",
        paper_pdf="icecream-03.pdf",
        table_or_section="Table 2 — Chocolate premium: cream 0.40, cocoa 0.035, sugar 0.19, …",
        raw_materials=RawMaterials(
            milk=72.0,
            cream=45.0,
            sugar=38.0,
            stabilizers=0.15,
            emulsifiers_kg=0.05,
            cocoa_powder_kg=7.0,
            egg_yolk_kg=2.8,
            water=35.0,
        ),
        notes=(
            "Table 2: cocoa 0.035, sugar 0.19, egg yolk 0.014, stabilisers 0.001 kg/kg ice cream; "
            "200 kg batch-scale masses."
        ),
    ),
    "COOK_HARTEL_CRYSTALLIZATION_REFERENCE": LiteratureRecipePreset(
        id="COOK_HARTEL_CRYSTALLIZATION_REFERENCE",
        citation=(
            "Cook, K. L. K., & Hartel, R. W. Mechanisms of ice crystallization in ice cream production "
            "(review of nucleation, growth, recrystallization; crystal size ranges ~1–150 µm)."
        ),
        paper_pdf="icecream-04.pdf",
        table_or_section="N/A — conceptual review; use with freezer metadata (Kelvin ΔT, mean crystal size)",
        raw_materials=RawMaterials(
            milk=100.0,
            cream=30.0,
            sugar=25.0,
            stabilizers=1.65,
            emulsifiers_kg=0.35,
            water=43.0,
        ),
        notes=(
            "No formulation table in the review; recipe matches simulator default. "
            "Use report quality/freezer fields for crystallization physics (see industrial_physics)."
        ),
    ),
    "WARI_ZHU_2019_SCHEDULING_REFERENCE": LiteratureRecipePreset(
        id="WARI_ZHU_2019_SCHEDULING_REFERENCE",
        citation=(
            "Wari, E., & Zhu, W. (2019). Constraint programming for scheduling in an ice cream manufacturing line. "
            "International Journal of Production Research, 57(21), 6648–6664. DOI 10.1080/00207543.2019.1571250"
        ),
        paper_pdf="icecream-05.pdf",
        table_or_section="Scheduling / sequencing (not formulation)",
        raw_materials=RawMaterials(
            milk=100.0,
            cream=30.0,
            sugar=25.0,
            stabilizers=1.65,
            emulsifiers_kg=0.35,
            water=43.0,
        ),
        notes="Placeholder recipe; paper addresses plant scheduling, not mix design.",
    ),
}


def list_preset_ids() -> list[str]:
    """Sorted preset ids for CLI and tests."""
    return sorted(LITERATURE_PRESETS.keys())


def get_preset(preset_id: str) -> LiteratureRecipePreset:
    if preset_id not in LITERATURE_PRESETS:
        raise KeyError(
            f"Unknown literature preset {preset_id!r}. "
            f"Choose one of: {', '.join(list_preset_ids())}"
        )
    return LITERATURE_PRESETS[preset_id]


def run_literature_suite(
    include_cleaning_phase: bool = False,
    **run_full_cycle_kwargs: Any,
) -> list[dict[str, Any]]:
    """
    Run ``run_full_cycle`` once per literature preset (for regression / batch comparison).

    Default ``include_cleaning_phase=False`` keeps runs fast; enable for full wastewater path.
    """
    from icecream_simulator.run_full_cycle import run_full_cycle

    rows: list[dict[str, Any]] = []
    for pid in list_preset_ids():
        report = run_full_cycle(
            literature_preset_id=pid,
            include_cleaning_phase=include_cleaning_phase,
            **run_full_cycle_kwargs,
        )
        q = report.get("quality") or {}
        rows.append(
            {
                "preset_id": pid,
                "product_kg": report.get("mixer", {}).get("product_to_freezer_kg"),
                "ice_crystal_primary_um": q.get("ice_crystal_primary_um"),
                "ice_crystal_mean_um": q.get("ice_crystal_mean_um"),
                "ice_crystal_wall_um": q.get("ice_crystal_wall_um"),
                "ice_crystal_bulk_um": q.get("ice_crystal_bulk_um"),
                "gompertz_frozen_water_fraction": q.get("gompertz_frozen_water_fraction"),
                "avrami_frozen_water_fraction": q.get("avrami_frozen_water_fraction"),
                "initial_freezing_point_mix_C": q.get("initial_freezing_point_mix_C"),
                "kelvin_depression_K": q.get("kelvin_freezing_point_depression_for_mean_crystal_K"),
                "hardness_proxy_kPa": q.get("hardness_proxy_kPa"),
                "mass_balance_closed": report.get("efficiency_summary", {}).get("mass_balance_closed"),
            }
        )
    return rows
