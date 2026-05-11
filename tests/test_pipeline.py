"""Smoke tests for the simplified pipeline."""

from icecream_simulator import RawMaterials, run_full_cycle, run_literature_suite, list_preset_ids


def test_run_full_cycle_default():
    r = run_full_cycle()
    assert r["production"]["product_mass_kg"] > 0
    assert r["summary"]["mass_balance_closed"] is True
    assert "bioconversion" in r


def test_run_full_cycle_no_cleaning():
    r = run_full_cycle(include_cleaning_phase=False)
    assert r["cip"]["wastewater_volume_L"] == 0
    assert r["bioconversion"]["bioplastic_mass_kg"] == 0


def test_literature_suite():
    rows = run_literature_suite(include_cleaning_phase=True)
    assert len(rows) == len(list_preset_ids())


def test_custom_recipe():
    raw = RawMaterials(milk=50, cream=10, sugar=12, stabilizers=1, water=27, emulsifiers_kg=0.2)
    r = run_full_cycle(raw_materials=raw, residue_mass_fraction=0.03)
    assert r["inputs"]["total_batch_mass_kg"] == raw.total_mass
