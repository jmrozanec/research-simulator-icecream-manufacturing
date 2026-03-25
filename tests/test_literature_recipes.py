"""Tests for literature presets and cocoa-inclusive raw materials."""

from icecream_simulator.literature_recipes import LITERATURE_PRESETS, get_preset, list_preset_ids, run_literature_suite
from icecream_simulator.schemas import RawMaterials
from icecream_simulator.run_full_cycle import run_full_cycle


def test_all_presets_total_200kg():
    for pid in list_preset_ids():
        p = get_preset(pid)
        assert abs(p.raw_materials.total_mass - 200.0) < 1e-6, pid


def test_run_full_cycle_each_preset():
    for pid in list_preset_ids():
        r = run_full_cycle(literature_preset_id=pid, include_cleaning_phase=False)
        assert r["inputs"].get("literature_preset_id") == pid
        assert r["efficiency_summary"]["mass_balance_closed"] is True


def test_egg_yolk_increases_fat_fraction():
    base = RawMaterials(
        milk=100, cream=30, sugar=25, stabilizers=1.65, emulsifiers_kg=0.35, water=43
    )
    with_egg = RawMaterials(
        milk=75.0,
        cream=40.0,
        sugar=34.0,
        stabilizers=0.2,
        water=47.269,
        egg_yolk_kg=2.8,
        vanilla_extract_kg=0.73,
        vanillin_kg=0.001,
    )
    assert abs(with_egg.total_mass - 200.0) < 1e-6
    from icecream_simulator.mixer import _composition_from_raw_materials

    cb = _composition_from_raw_materials(base)
    ce = _composition_from_raw_materials(with_egg)
    assert ce.fat > cb.fat


def test_cocoa_increases_solids_fraction():
    base = RawMaterials(
        milk=100, cream=30, sugar=25, stabilizers=1.65, emulsifiers_kg=0.35, water=43
    )
    choc = RawMaterials(
        milk=82,
        cream=25,
        sugar=30,
        stabilizers=1.2,
        emulsifiers_kg=0.3,
        cocoa_powder_kg=6.0,
        water=55.5,
    )
    assert choc.total_mass == 200.0
    from icecream_simulator.mixer import _composition_from_raw_materials

    cb = _composition_from_raw_materials(base)
    cc = _composition_from_raw_materials(choc)
    assert cc.solids > cb.solids


def test_literature_suite_runs():
    rows = run_literature_suite(include_cleaning_phase=False)
    assert len(rows) == len(LITERATURE_PRESETS)
    for row in rows:
        assert row["mass_balance_closed"] is True
