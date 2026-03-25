"""Unit tests for research-grade crystallization and emulsion physics."""

from icecream_simulator import industrial_physics as phys


def test_wall_smaller_than_bulk():
    d_w = phys.ice_crystal_wall_um_sshe(45.0, 253.15, 55.0, 268.15, 0.01, 0.005)
    d_b = phys.ice_crystal_bulk_um_sshe(45.0, 253.15, 55.0, 268.15, 0.01, 0.005)
    assert d_w < d_b


def test_volume_mean_between_wall_and_bulk():
    d_w, d_b, d_v = phys.ice_crystal_volume_mean_um_sshe(
        45.0, 253.15, 55.0, 268.15, 0.015, 0.008, volume_fraction_wall_ice=0.28
    )
    assert min(d_w, d_b) <= d_v <= max(d_w, d_b) + 1e-6


def test_avrami_and_gompertz_in_0_1_range():
    g = phys.gompertz_frozen_water_fraction_sshe(45.0, -2.0, -5.0)
    a = phys.avrami_frozen_water_fraction_sshe(45.0, -2.0, -5.0)
    assert 0.0 <= g <= 1.0
    assert 0.0 <= a <= 1.0
    b = phys.blended_frozen_water_fraction_kinetics(g, a)
    assert abs(b - 0.5 * (g + a)) < 1e-9


def test_storage_increases_crystal_size():
    d0 = 40.0
    d1 = phys.storage_recrystallized_mean_um(d0, 72 * 3600.0, 248.15, 0.01, 0.005)
    assert d1 >= d0


def test_storage_zero_time_no_change():
    d0 = 40.0
    d1 = phys.storage_recrystallized_mean_um(d0, 0.0, 248.15, 0.01, 0.005)
    assert d1 == d0


def test_run_full_cycle_with_storage():
    from icecream_simulator.run_full_cycle import run_full_cycle

    r = run_full_cycle(
        include_cleaning_phase=False,
        storage_time_s=72 * 3600.0,
        storage_temp_K=248.15,
    )
    q = r["quality"]
    assert q.get("storage_time_s") == 72 * 3600.0
    assert q.get("ice_crystal_mean_um_before_storage") is not None


def test_hydrocolloid_reduces_bulk_crystal_size():
    d_hi = phys.ice_crystal_bulk_um_sshe(45.0, 253.15, 55.0, 268.15, 0.04, 0.0)
    d_lo = phys.ice_crystal_bulk_um_sshe(45.0, 253.15, 55.0, 268.15, 0.0, 0.0)
    assert d_hi < d_lo
