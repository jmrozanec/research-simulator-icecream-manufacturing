"""Tests for the instrumentation layer: sensors, events, energy aggregation."""

from __future__ import annotations

import math
import random

import pytest

from icecream_simulator import (
    AccuracyKind,
    AlarmThresholds,
    Event,
    EventBus,
    PlantProfile,
    Provenance,
    SensorReading,
    SensorSpec,
    Severity,
    SourceKind,
    apply_instrumentation,
    build_midsize_continuous_dairy,
    load_default_profile,
    run_full_cycle,
    sample_reading,
)


# ---------------------------------------------------------------------------
# Sensor model
# ---------------------------------------------------------------------------


def _spec(**kw):
    base = dict(
        name="T", measurand="temperature", unit="K",
        accuracy=0.3, accuracy_kind=AccuracyKind.ABS,
        range_min=200.0, range_max=400.0, sampling_hz=1.0,
        provenance=Provenance.assumption("test"),
    )
    base.update(kw)
    return SensorSpec(**base)


def test_sensor_reading_unbiased_when_sigma_zero():
    spec = _spec(accuracy=1e-12)  # ~0 sigma
    rng = random.Random(0)
    r = sample_reading(spec, 300.0, rng)
    assert abs(r.value - 300.0) < 1e-6
    assert r.truth == 300.0
    assert not r.dropped


def test_sensor_reading_noise_within_3_sigma():
    spec = _spec(accuracy=0.3)
    rng = random.Random(0)
    deltas = []
    for _ in range(2000):
        r = sample_reading(spec, 300.0, rng)
        deltas.append(r.value - 300.0)
    mean = sum(deltas) / len(deltas)
    var = sum((d - mean) ** 2 for d in deltas) / len(deltas)
    # Empirical sigma should be close to 0.3 within tolerance for n=2000
    assert 0.2 < math.sqrt(var) < 0.4


def test_sensor_dropout_produces_nan():
    spec = _spec(dropout_prob=1.0)
    rng = random.Random(0)
    r = sample_reading(spec, 300.0, rng)
    assert r.dropped
    assert math.isnan(r.value)


def test_sensor_out_of_range_flag():
    spec = _spec(range_min=200.0, range_max=400.0, bias=200.0, accuracy=1e-12)
    rng = random.Random(0)
    r = sample_reading(spec, 350.0, rng)
    assert r.out_of_range
    # Value is clipped to range
    assert r.value == 400.0


def test_sensor_drift_is_applied():
    spec = _spec(drift_per_hour=0.1, accuracy=1e-12)
    rng = random.Random(0)
    r0 = sample_reading(spec, 300.0, rng, elapsed_hours=0.0)
    r10 = sample_reading(spec, 300.0, rng, elapsed_hours=10.0)
    assert r10.value - r0.value == pytest.approx(1.0, rel=1e-3)


def test_accuracy_kind_rel_rate():
    spec = _spec(accuracy=0.01, accuracy_kind=AccuracyKind.REL_RATE)
    assert spec.sigma_for(100.0) == pytest.approx(1.0)
    assert spec.sigma_for(50.0) == pytest.approx(0.5)


def test_accuracy_kind_rel_fs():
    spec = _spec(accuracy=0.01, accuracy_kind=AccuracyKind.REL_FS,
                 range_min=0.0, range_max=400.0)
    assert spec.sigma_for(100.0) == pytest.approx(4.0)


def test_nan_truth_is_dropped_not_propagated():
    spec = _spec()
    rng = random.Random(0)
    r = sample_reading(spec, float("nan"), rng)
    assert r.dropped


# ---------------------------------------------------------------------------
# Event bus
# ---------------------------------------------------------------------------


def test_event_bus_counts_and_worst_severity():
    bus = EventBus()
    bus.info("stage1", "test.info", "fine")
    bus.warn("stage1", "test.warn", "warning")
    bus.alarm("stage2", "test.alarm", "alarm")
    counts = bus.count_by_severity()
    assert counts == {"info": 1, "warn": 1, "alarm": 1, "critical": 0}
    assert bus.worst_severity() == Severity.ALARM


def test_event_bus_filter_by_stage_and_severity():
    bus = EventBus()
    bus.warn("freezer", "freezer.x", "x")
    bus.warn("freezer", "freezer.y", "y")
    bus.alarm("freezer", "freezer.z", "z")
    bus.warn("hardening", "hardening.x", "x")
    assert len(bus.filter(stage="freezer")) == 3
    assert len(bus.filter(stage="freezer", severity=Severity.ALARM)) == 1
    assert len(bus.filter(code_prefix="freezer.")) == 3


# ---------------------------------------------------------------------------
# Plant profile
# ---------------------------------------------------------------------------


def test_default_profile_has_expected_stages():
    profile = build_midsize_continuous_dairy()
    expected = {
        "preparation_mix", "pasteurization", "homogenization", "cooling_phe",
        "ageing_vat", "freezer", "hardening", "packaging",
        "cip", "prefiltration", "hydrodynamic_cavitation", "filtration",
        "bioconversion",
    }
    assert expected.issubset(set(profile.sensors_by_stage.keys()))


def test_every_sensor_has_provenance():
    profile = build_midsize_continuous_dairy()
    for stage in profile.sensors_by_stage.values():
        for sensor in stage.sensors.values():
            assert isinstance(sensor.provenance, Provenance)
            assert sensor.provenance.citation


def test_profile_roundtrip_json(tmp_path):
    profile = build_midsize_continuous_dairy()
    path = tmp_path / "p.json"
    profile.to_json(path)
    loaded = PlantProfile.from_json(path)
    assert loaded.name == profile.name
    assert set(loaded.sensors_by_stage) == set(profile.sensors_by_stage)


def test_find_sensor_by_measurand():
    profile = build_midsize_continuous_dairy()
    s = profile.find_sensor("freezer", "ice_crystal_size")
    assert s is not None
    assert s.measurand == "ice_crystal_size"


# ---------------------------------------------------------------------------
# End-to-end instrumentation on a real run
# ---------------------------------------------------------------------------


def test_apply_instrumentation_adds_sensors_events_energy():
    report = run_full_cycle(include_cleaning_phase=True)
    profile = load_default_profile()
    enriched = apply_instrumentation(report, profile, seed=42)

    # Original keys preserved
    assert "mixer" in enriched
    assert "quality" in enriched
    # New keys added
    assert "sensors" in enriched
    assert "events" in enriched
    assert "energy" in enriched
    assert "plant_profile" in enriched

    # At least the freezer stage should have populated sensors
    assert "freezer" in enriched["sensors"]
    freezer_sensors = enriched["sensors"]["freezer"]
    assert len(freezer_sensors) > 0
    for r in freezer_sensors:
        # Every reading has a truth and a sigma
        assert "truth" in r and "sigma" in r and "value" in r


def test_apply_instrumentation_is_seed_deterministic():
    report = run_full_cycle(include_cleaning_phase=False)
    profile = load_default_profile()
    a = apply_instrumentation(report, profile, seed=7)
    b = apply_instrumentation(report, profile, seed=7)
    # First sensor of freezer must match exactly
    ra = a["sensors"]["freezer"][0]
    rb = b["sensors"]["freezer"][0]
    assert ra["value"] == rb["value"]
    assert ra["truth"] == rb["truth"]


def test_apply_instrumentation_emits_events_for_quality_excursions():
    # Drive log10 below target by giving an absurdly short hold
    report = run_full_cycle(
        include_cleaning_phase=False,
        pasteurization_hold_time_s=0.001,
    )
    profile = load_default_profile()
    enriched = apply_instrumentation(report, profile, seed=0)
    codes = {e["code"] for e in enriched["events"]["list"]}
    assert any("pasteurization" in c for c in codes)


def test_energy_aggregator_has_thermal_and_electrical():
    report = run_full_cycle(include_cleaning_phase=True)
    profile = load_default_profile()
    enriched = apply_instrumentation(report, profile, seed=0)
    e = enriched["energy"]
    assert e["thermal_J"] >= 0.0
    assert e["electrical_J"] >= 0.0
    assert e["total_J"] == pytest.approx(e["thermal_J"] + e["electrical_J"])
    assert e["total_kWh"] == pytest.approx(e["total_J"] / 3.6e6)
