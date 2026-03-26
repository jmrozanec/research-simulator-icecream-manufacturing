"""Tests for pre-filtration and hydrodynamic cavitation wastewater stages."""

from icecream_simulator.batch_models import WastewaterStream
from icecream_simulator.cavitation import CavitationConfig, run_hydrodynamic_cavitation
from icecream_simulator.prefiltration import PrefiltrationConfig, run_prefiltration
from icecream_simulator.run_full_cycle import run_full_cycle


def _sample_ww() -> WastewaterStream:
    return WastewaterStream(
        volume_L=80.0,
        mass_kg=82.0,
        temperature_K=323.0,
        tss_mg_L=1200.0,
        dissolved_sugar_kg=2.5,
        cod_mg_L=4500.0,
        bod_mg_L=2100.0,
        fog_mg_L=800.0,
    )


def test_prefiltration_reduces_tss_and_mass_balance():
    w0 = _sample_ww()
    out, rep = run_prefiltration(w0, PrefiltrationConfig(tss_removal_fraction=0.5))
    assert out.tss_mg_L < w0.tss_mg_L
    assert rep["tss_removed_kg"] > 0
    v = w0.volume_L
    tss_in = (w0.tss_mg_L * 1e-6) * v
    assert abs(tss_in - rep["tss_removed_kg"] - (out.tss_mg_L * 1e-6) * v) < 1e-6


def test_cavitation_updates_cod_and_bioavailability():
    w0 = _sample_ww()
    out, rep = run_hydrodynamic_cavitation(w0, CavitationConfig())
    assert "bioavailability_factor" in rep
    assert rep["bioavailability_factor"] >= 1.0
    assert "mean_mw_index_after" in rep
    assert out.metadata.get("stage") == "hydrodynamic_cavitation"


def test_full_cycle_includes_prefiltration_and_cavitation_reports():
    r = run_full_cycle(include_cleaning_phase=True, water_volume_L=80.0)
    assert r.get("prefiltration") is not None
    assert r.get("hydrodynamic_cavitation") is not None
    assert r["bioconversion"].get("cavitation_bioavailability_factor") is not None
    assert r.get("wastewater_to_nanofiltration") is not None


def test_full_cycle_skip_cleaning_no_prefiltration_keys():
    r = run_full_cycle(include_cleaning_phase=False)
    assert r.get("prefiltration") is None
    assert r.get("hydrodynamic_cavitation") is None
