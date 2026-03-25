"""Crystallization parameter loading and parity with default physics."""

from pathlib import Path

from icecream_simulator.crystallization_parameters import (
    DEFAULT_CRYSTALLIZATION_PARAMETERS,
    CrystallizationParameters,
    load_crystallization_parameters_from_json,
)
from icecream_simulator.run_full_cycle import run_full_cycle


def test_default_none_matches_explicit_default():
    r1 = run_full_cycle(include_cleaning_phase=False, crystallization_parameters=None)
    r2 = run_full_cycle(
        include_cleaning_phase=False,
        crystallization_parameters=DEFAULT_CRYSTALLIZATION_PARAMETERS,
    )
    assert r1["quality"]["ice_crystal_mean_um"] == r2["quality"]["ice_crystal_mean_um"]
    assert r1["quality"]["gompertz_frozen_water_fraction"] == r2["quality"]["gompertz_frozen_water_fraction"]


def test_example_json_loads_and_runs():
    root = Path(__file__).resolve().parents[1]
    path = root / "examples" / "crystallization_parameters_example.json"
    params = load_crystallization_parameters_from_json(path)
    assert isinstance(params, CrystallizationParameters)
    assert params.name == "example_product_line"
    r = run_full_cycle(include_cleaning_phase=False, crystallization_parameters=params)
    assert r["inputs"]["crystallization_parameters_name"] == "example_product_line"
    assert r["efficiency_summary"]["mass_balance_closed"] is True


def test_report_includes_parameter_dump():
    r = run_full_cycle(include_cleaning_phase=False)
    assert "crystallization_parameters" in r["inputs"]
    assert r["inputs"]["crystallization_parameters"]["name"] == "default"
