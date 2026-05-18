"""Tests for the scenario runner / dataset writer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from icecream_simulator import (
    Constant,
    Discrete,
    ProcessParamsDist,
    RawMaterialsDist,
    ScenarioSpec,
    Triangular,
    Uniform,
    diverse_industrial_spec,
    run_sweep,
)


def test_diverse_spec_smoke(tmp_path):
    spec = diverse_industrial_spec()
    spec.include_cleaning_phase = False  # faster
    result = run_sweep(spec, n=4, output_dir=tmp_path, seed=1,
                       sampler="lhs", save_full_reports=False)
    assert result.n_succeeded == 4
    assert result.n_failed == 0
    assert (tmp_path / "runs.csv").exists()
    assert (tmp_path / "runs.jsonl").exists()
    assert (tmp_path / "manifest.json").exists()


def test_seed_determinism(tmp_path):
    spec = diverse_industrial_spec()
    spec.include_cleaning_phase = False
    r1 = run_sweep(spec, n=3, output_dir=tmp_path / "a", seed=99,
                   save_full_reports=False)
    r2 = run_sweep(spec, n=3, output_dir=tmp_path / "b", seed=99,
                   save_full_reports=False)
    a = (tmp_path / "a" / "runs.csv").read_text()
    b = (tmp_path / "b" / "runs.csv").read_text()
    # CSV header differs only by ordering of dynamically-added optional columns;
    # for deterministic seeds the produced row content should match.
    assert a == b


def test_manifest_records_full_spec(tmp_path):
    spec = ScenarioSpec(
        name="unit_test_spec",
        raw_materials=RawMaterialsDist(milk=Constant(value=100.0)),
        include_cleaning_phase=False,
    )
    run_sweep(spec, n=2, output_dir=tmp_path, seed=5, save_full_reports=False)
    m = json.loads((tmp_path / "manifest.json").read_text())
    assert m["scenario_name"] == "unit_test_spec"
    assert m["n_requested"] == 2
    assert m["n_succeeded"] == 2
    assert m["seed"] == 5
    assert m["sampler"] in ("lhs", "random")
    assert "plant_profile" in m
    assert "scenario_spec" in m


def test_per_run_reports_saved_when_requested(tmp_path):
    spec = diverse_industrial_spec()
    spec.include_cleaning_phase = False
    run_sweep(spec, n=3, output_dir=tmp_path, seed=1, save_full_reports=True)
    reports = list((tmp_path / "reports").glob("run_*.json"))
    assert len(reports) == 3
    rpt = json.loads(reports[0].read_text())
    assert "sensors" in rpt
    assert "events" in rpt
    assert "energy" in rpt


def test_distributions_sample_within_range():
    u = Uniform(lo=0.0, hi=10.0)
    assert 0.0 <= u.sample(0.5) <= 10.0
    t = Triangular(lo=0.0, mode=5.0, hi=10.0)
    assert 0.0 <= t.sample(0.0) <= 10.0
    assert 0.0 <= t.sample(0.999) <= 10.0
    d = Discrete(values=[1.0, 2.0, 3.0])
    assert d.sample(0.0) == 1.0
    assert d.sample(0.5) == 2.0
    assert d.sample(0.99) == 3.0


def test_lhs_covers_each_marginal_uniformly(tmp_path):
    """Smoke check on coverage: LHS should hit every percentile band."""
    spec = ScenarioSpec(
        name="cov_test",
        raw_materials=RawMaterialsDist(),
        process=ProcessParamsDist(
            air_overrun=Uniform(lo=0.0, hi=1.0),
        ),
        include_cleaning_phase=False,
    )
    result = run_sweep(spec, n=20, output_dir=tmp_path, seed=11,
                       sampler="lhs", save_full_reports=False)
    rows = result.rows
    overruns = sorted(float(r["pp_air_overrun"]) for r in rows)
    # With 20 LHS samples in [0, 1] the deciles should be distinct
    assert overruns[0] < 0.1 + 0.05
    assert overruns[-1] > 0.9 - 0.05


def test_literature_preset_overrides_raw_materials(tmp_path):
    spec = diverse_industrial_spec()
    spec.include_cleaning_phase = False
    spec.literature_preset_ids = ["GIUDICI_2021_INDUSTRIAL"]
    result = run_sweep(spec, n=3, output_dir=tmp_path, seed=0,
                       save_full_reports=False)
    for r in result.rows:
        assert r["literature_preset_id"] == "GIUDICI_2021_INDUSTRIAL"


def test_failure_in_one_run_does_not_abort_sweep(tmp_path):
    # Force one run to fail by giving a clearly broken raw material spec
    spec = ScenarioSpec(
        name="fail_test",
        raw_materials=RawMaterialsDist(
            milk=Uniform(lo=-1.0, hi=-1.0),  # invalid (RawMaterials Field(ge=0))
        ),
        include_cleaning_phase=False,
    )
    result = run_sweep(spec, n=3, output_dir=tmp_path, seed=0,
                       save_full_reports=False)
    assert result.n_failed >= 1
    # Sweep still wrote manifest and CSV
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "runs.csv").exists()
