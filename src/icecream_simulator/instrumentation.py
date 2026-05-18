"""
Instrumentation layer — wrap a clean simulator report with realistic readings,
structured events, and an aggregated energy balance.

The existing ``run_full_cycle`` returns a deterministic ground-truth report.
``apply_instrumentation`` takes that report plus a ``PlantProfile`` and a
seeded RNG and returns the same report enriched with:

- ``report["sensors"]``: per-stage list of ``SensorReading`` dicts. Each carries
  ``value`` (noisy observation), ``truth`` (ground truth), ``sigma``, ``bias``,
  ``dropped``, and ``out_of_range``. Train ML models on (truth, sensor) pairs
  and weight by sigma for heteroscedastic loss.
- ``report["events"]``: list of structured ``Event`` records derived by scanning
  the report against the profile's ``AlarmThresholds``.
- ``report["energy"]``: aggregated heat duties and electrical power from every
  stage, converted to a single kWh / kJ summary. Closes the energy balance the
  existing report leaves open.

This is non-invasive: ``run_full_cycle`` is not modified. The wrapper is what
the scenario runner calls.
"""

from __future__ import annotations

import math
import random
from typing import Any

from icecream_simulator.events import Event, EventBus, Severity
from icecream_simulator.plant_profile import AlarmThresholds, PlantProfile
from icecream_simulator.sensors import SensorReading, SensorSpec, sample_reading


# ---------------------------------------------------------------------------
# Mapping from physics outputs → sensor measurands
# ---------------------------------------------------------------------------


def _stage_detail(report: dict, stage_name: str) -> dict:
    for s in report.get("industrial_chain", {}).get("stages_detail", []) or []:
        if s.get("stage") == stage_name:
            return s
    return {}


def _ground_truth_for(profile: PlantProfile, stage: str, sensor_local: str,
                     spec: SensorSpec, report: dict) -> float | None:
    """Look up the ground-truth value the simulator produced for this sensor."""
    d = _stage_detail(report, stage)
    inputs = report.get("inputs", {})
    quality = report.get("quality", {})

    # Stage-by-stage mapping. Where ground-truth doesn't exist (e.g. a sensor
    # the simulator doesn't expose), return None and the reading is skipped.
    if stage == "preparation_mix":
        if sensor_local == "mix_T":
            return float(d.get("temp_out_K", 328.0))
        if sensor_local == "agitator_rpm":
            return float(inputs.get("preparation_rpm", 60.0))
        if sensor_local == "agitator_current":
            # Crude proxy: scaled mixing power. Real plants don't read this
            # directly; this is an inference, hence the wide ±5% rate spec.
            p_w = float(d.get("power_W", report.get("mixer", {}).get("mixing_power_W", 0.0)))
            # P(W) / (sqrt(3)*V*PF) ~ A; assume V=400V, PF=0.85
            return max(0.0, p_w / (3.0 ** 0.5 * 400.0 * 0.85))
        return None

    if stage == "pasteurization":
        if sensor_local == "hold_outlet_T":
            return float(d.get("temp_out_K", 353.15))
        if sensor_local == "mix_flow":
            # No flow modeled; approximate from batch mass / hold time / density
            mass_kg = float(d.get("mass_kg", 0.0))
            hold_s = float(inputs.get("pasteurization_hold_time_s", 15.0) or 1.0)
            return (mass_kg / 1.05) / max(hold_s / 60.0, 1e-3)
        if sensor_local == "lethality_log10":
            return float(d.get("log10_pathogen_reduction", 0.0) or 0.0)
        return None

    if stage == "homogenization":
        if sensor_local == "p1_pressure":
            return float(inputs.get("homogenization_pressure_bar", 200.0))
        if sensor_local == "p2_pressure":
            # Two-stage homogenizers typically run 2nd stage at ~20–30 bar
            return min(float(inputs.get("homogenization_pressure_bar", 200.0)) * 0.15, 50.0)
        if sensor_local == "motor_current":
            # Empirical: P ≈ Q × dP / η. Use batch mass and pasteurization hold as flow proxy.
            mass_kg = float(d.get("mass_kg", 0.0))
            hold_s = float(inputs.get("pasteurization_hold_time_s", 15.0) or 1.0)
            q_m3_s = (mass_kg / 1050.0) / max(hold_s, 1e-3)  # mass density 1050 kg/m3
            p_bar = float(inputs.get("homogenization_pressure_bar", 200.0))
            p_w = q_m3_s * p_bar * 1e5 / 0.7  # 70 % overall efficiency
            return max(0.0, p_w / (3.0 ** 0.5 * 400.0 * 0.85))
        if sensor_local == "d32_lab":
            return float(d.get("fat_globule_d32_um", quality.get("fat_globule_d32_um", 0.0)) or 0.0)
        return None

    if stage == "cooling_phe":
        if sensor_local == "mix_in_T":
            return 353.15  # PHE inlet is pasteurizer outlet
        if sensor_local == "mix_out_T":
            return float(d.get("temp_out_K", 278.15))
        if sensor_local == "coolant_in_T":
            return 274.15  # 1 °C glycol typical
        if sensor_local == "coolant_out_T":
            return 285.15
        if sensor_local == "coolant_flow":
            return 300.0
        return None

    if stage == "ageing_vat":
        if sensor_local == "mix_T":
            return float(d.get("temp_out_K", 277.15))
        if sensor_local == "agitator_rpm":
            return 30.0  # slow agitation typical
        if sensor_local == "agitator_current":
            return 8.0
        if sensor_local == "jacket_in_T":
            return 271.15
        if sensor_local == "jacket_out_T":
            return 274.15
        if sensor_local == "jacket_flow":
            return float(inputs.get("jacket_flow_L_min", 20.0))
        return None

    if stage == "freezer":
        if sensor_local == "mix_in_T":
            return 278.15
        if sensor_local == "mix_out_T":
            return float(d.get("temp_out_K", 268.15))
        if sensor_local == "evap_T":
            return float(inputs.get("coolant_temp_K", 253.15))
        if sensor_local == "barrel_dp":
            return 4.0  # bar, generic SSHE
        if sensor_local == "dasher_current":
            p_w = float(d.get("dasher_shaft_power_W", 0.0) or 0.0)
            return max(0.0, p_w / (3.0 ** 0.5 * 400.0 * 0.85))
        if sensor_local == "dasher_rpm":
            return float(inputs.get("dasher_rpm", 55.0))
        if sensor_local == "air_flow":
            # Overrun → air flow proxy: overrun × mix volumetric flow
            ov = float(d.get("air_overrun_effective",
                             inputs.get("air_overrun", 0.5)) or 0.5)
            mass_kg = float(d.get("mass_kg", 0.0))
            res_s = float(inputs.get("freezer_residence_time_s", 45.0) or 1.0)
            mix_Lmin = (mass_kg / 1.05) / (res_s / 60.0)
            return ov * mix_Lmin
        if sensor_local == "ice_mean_um":
            return float(d.get("ice_crystal_mean_um", 40.0) or 40.0)
        if sensor_local == "overrun":
            return float(d.get("air_overrun_effective",
                              inputs.get("air_overrun", 0.5)) or 0.5)
        return None

    if stage == "hardening":
        if sensor_local == "zone_T":
            return 243.15
        if sensor_local == "product_surf_T":
            return float(d.get("temp_out_K", 243.15))
        if sensor_local == "hardness_kPa":
            return float(d.get("hardness_proxy_kPa", quality.get("hardness_proxy_kPa", 0.0)) or 0.0)
        return None

    if stage == "packaging":
        if sensor_local == "net_weight":
            return float(d.get("net_mass_kg_per_package", 0.0) or 0.0)
        if sensor_local == "fill_count":
            return float(d.get("package_count", 0) or 0)
        return None

    if stage == "cip":
        cip = report.get("cip", {})
        if sensor_local == "supply_T":
            return 323.15  # 50 °C alkaline CIP typical
        if sensor_local == "return_T":
            return 318.15
        if sensor_local == "flow":
            return 250.0
        if sensor_local == "supply_p":
            return 2.5
        if sensor_local == "conductivity":
            # rough TSS-to-conductivity proxy for monitoring
            return float(cip.get("tss_mg_L", 0.0) or 0.0) / 5000.0
        if sensor_local == "turbidity_return":
            return float(cip.get("tss_mg_L", 0.0) or 0.0) * 0.1
        return None

    if stage == "prefiltration":
        pre = report.get("prefiltration") or {}
        if sensor_local == "inlet_p":
            return 3.0
        if sensor_local == "outlet_p":
            return 2.5
        if sensor_local == "flow":
            return 200.0 if pre else 0.0
        return None

    if stage == "hydrodynamic_cavitation":
        cav = report.get("hydrodynamic_cavitation") or {}
        if sensor_local == "inlet_p":
            return 3.5
        if sensor_local == "throat_dp":
            return 1.2
        if sensor_local == "outlet_T":
            # Cavitation heats the stream very slightly
            return 323.65 if cav else 323.0
        if sensor_local == "flow":
            return 200.0 if cav else 0.0
        return None

    if stage == "filtration":
        flt = report.get("filtration") or {}
        if sensor_local == "feed_p":
            return 20.0
        if sensor_local == "permeate_p":
            return 1.0
        if sensor_local == "retentate_p":
            # Saturation → backpressure proxy
            sat = float(flt.get("filter_saturation_pct", 0.0) or 0.0) / 100.0
            return 19.0 - 5.0 * sat
        if sensor_local == "permeate_flow":
            return float(flt.get("permeate_volume_L", 0.0) or 0.0)
        if sensor_local == "permeate_conductivity":
            return 0.5
        if sensor_local == "feed_T":
            return 308.15
        return None

    if stage == "bioconversion":
        if sensor_local == "pH":
            return 6.8
        if sensor_local == "DO":
            return 35.0
        if sensor_local == "T":
            return 303.15
        if sensor_local == "OD":
            return 8.0
        return None

    return None


# ---------------------------------------------------------------------------
# Event detection from the report
# ---------------------------------------------------------------------------


def _emit_events_from_report(report: dict, alarms: AlarmThresholds, bus: EventBus) -> None:
    """Scan the report and emit structured events against the alarm thresholds."""
    q = report.get("quality", {}) or {}
    eff = report.get("efficiency_summary", {}) or {}
    flt = report.get("filtration", {}) or {}
    cav = report.get("hydrodynamic_cavitation") or {}
    inputs = report.get("inputs", {}) or {}

    # Pasteurization lethality
    log10r = q.get("log10_pathogen_reduction")
    if log10r is not None and log10r < alarms.log10_reduction_min:
        bus.alarm("pasteurization", "pasteurization.lethality_below_target",
                  f"Log10 reduction {log10r:.2f} below {alarms.log10_reduction_min}",
                  log10=log10r, min_required=alarms.log10_reduction_min)

    # Fat globule d32 (target ≤ 1 µm in research-grade homogenization)
    d32 = q.get("fat_globule_d32_um")
    if d32 is not None and d32 > alarms.fat_globule_d32_um_max:
        bus.warn("homogenization", "homogenization.d32_above_target",
                 f"d32 {d32:.3f} µm exceeds {alarms.fat_globule_d32_um_max} µm",
                 d32_um=d32, max_allowed=alarms.fat_globule_d32_um_max)

    # Ice crystal mean
    ice_um = q.get("ice_crystal_mean_um")
    if ice_um is not None:
        if ice_um > alarms.ice_crystal_mean_um_max:
            bus.alarm("freezer", "freezer.ice_crystals_too_coarse",
                      f"Ice mean {ice_um:.1f} µm exceeds alarm threshold "
                      f"{alarms.ice_crystal_mean_um_max} µm",
                      ice_um=ice_um, alarm_at=alarms.ice_crystal_mean_um_max)
        elif ice_um > alarms.ice_crystal_mean_um_warn:
            bus.warn("freezer", "freezer.ice_crystals_drifting",
                     f"Ice mean {ice_um:.1f} µm above warn threshold "
                     f"{alarms.ice_crystal_mean_um_warn} µm",
                     ice_um=ice_um, warn_at=alarms.ice_crystal_mean_um_warn)

    # Overrun band
    overrun = q.get("air_overrun_effective")
    if overrun is not None:
        if overrun < alarms.overrun_min:
            bus.warn("freezer", "freezer.overrun_low",
                     f"Effective overrun {overrun:.2f} below {alarms.overrun_min}",
                     overrun=overrun, min_required=alarms.overrun_min)
        elif overrun > alarms.overrun_max:
            bus.warn("freezer", "freezer.overrun_high",
                     f"Effective overrun {overrun:.2f} above {alarms.overrun_max}",
                     overrun=overrun, max_allowed=alarms.overrun_max)

    # Hardness band
    h = q.get("hardness_proxy_kPa")
    if h is not None:
        if h < alarms.hardness_kPa_min:
            bus.warn("hardening", "hardening.too_soft",
                     f"Hardness {h:.0f} kPa below {alarms.hardness_kPa_min}",
                     hardness_kPa=h)
        elif h > alarms.hardness_kPa_max:
            bus.warn("hardening", "hardening.too_hard",
                     f"Hardness {h:.0f} kPa above {alarms.hardness_kPa_max}",
                     hardness_kPa=h)

    # Cavitation intensity
    if cav:
        ci = cav.get("cavitation_intensity")
        if ci is not None and ci < alarms.cavitation_intensity_min:
            bus.warn("hydrodynamic_cavitation", "cavitation.under_intensity",
                     f"Intensity {ci:.2f} below {alarms.cavitation_intensity_min}",
                     intensity=ci, min_required=alarms.cavitation_intensity_min)

    # Filter saturation
    sat = float(flt.get("filter_saturation_pct", 0.0) or 0.0) / 100.0
    if sat >= alarms.filter_saturation_alarm:
        bus.alarm("filtration", "filtration.maintenance_required",
                  f"Filter saturation {sat:.0%} ≥ alarm {alarms.filter_saturation_alarm:.0%}",
                  saturation=sat)
    elif sat >= alarms.filter_saturation_warn:
        bus.warn("filtration", "filtration.saturation_rising",
                 f"Filter saturation {sat:.0%} ≥ warn {alarms.filter_saturation_warn:.0%}",
                 saturation=sat)

    # Mass balance
    if not eff.get("mass_balance_closed", True):
        bus.critical("global", "mass_balance.not_closed",
                     "Mass balance check failed; raw + flavor + inclusions ≠ "
                     "product + residue + flush",
                     details=eff)
    # Relative-tolerance variant (the simulator's absolute check can falsely
    # pass for very large or small batches; we check relatively here too)
    raw_kg = float(inputs.get("total_mass_including_additives_kg", 0.0) or 0.0)
    if raw_kg > 0:
        product = float(report.get("mixer", {}).get("product_to_freezer_kg", 0.0) or 0.0)
        residue = float(report.get("mixer", {}).get("tank_residue_kg", 0.0) or 0.0)
        flush = float(report.get("mixer", {}).get("interface_flush_kg", 0.0) or 0.0)
        rel = abs((product + residue + flush) - raw_kg) / raw_kg
        if rel > alarms.mass_balance_relative_tolerance:
            bus.warn("global", "mass_balance.relative_drift",
                     f"Relative mass-balance drift {rel:.2e} above "
                     f"{alarms.mass_balance_relative_tolerance:.0e}",
                     relative_error=rel)


# ---------------------------------------------------------------------------
# Energy aggregation
# ---------------------------------------------------------------------------


def _aggregate_energy(report: dict) -> dict[str, float]:
    """Sum up thermal duties + electrical/shaft work scattered across stages."""
    thermal_J = 0.0
    electrical_J = 0.0
    by_stage: dict[str, float] = {}

    for s in report.get("industrial_chain", {}).get("stages_detail", []) or []:
        stage = s.get("stage", "unknown")
        # Heat duty (positive removed or added)
        for k in ("heat_duty_J", "heat_removed_stage1_J", "heat_removed_stage2_J",
                  "heat_removed_J"):
            v = s.get(k)
            if v is not None:
                thermal_J += abs(float(v))
                by_stage[stage] = by_stage.get(stage, 0.0) + abs(float(v))
        # Mechanical / shaft power × residence ≈ work (use residence_time_s when present)
        p_w = s.get("power_W") or s.get("dasher_shaft_power_W")
        if p_w is not None:
            t_s = float(s.get("residence_time_s",
                              report.get("inputs", {}).get("preparation_mixing_time_s", 0.0)) or 0.0)
            w = float(p_w) * t_s
            electrical_J += w
            by_stage[stage] = by_stage.get(stage, 0.0) + w

    # Cavitation pumping
    cav = report.get("hydrodynamic_cavitation") or {}
    if cav:
        kwh = float(cav.get("energy_proxy_kwh", 0.0) or 0.0)
        electrical_J += kwh * 3.6e6
        by_stage["hydrodynamic_cavitation"] = by_stage.get("hydrodynamic_cavitation", 0.0) + kwh * 3.6e6

    total_J = thermal_J + electrical_J
    return {
        "thermal_J": thermal_J,
        "electrical_J": electrical_J,
        "total_J": total_J,
        "total_kWh": total_J / 3.6e6,
        "by_stage_J": by_stage,
    }


# ---------------------------------------------------------------------------
# Top-level instrumentation entry
# ---------------------------------------------------------------------------


def apply_instrumentation(
    report: dict,
    profile: PlantProfile,
    *,
    seed: int | None = None,
    elapsed_hours: float = 0.0,
) -> dict:
    """Enrich a ``run_full_cycle`` report with sensors, events, and energy.

    Returns a new ``report`` dict (input is not mutated) with three new keys:
    ``sensors``, ``events``, ``energy``. Existing keys are preserved.
    """
    rng = random.Random(seed) if seed is not None else random.Random()
    out = dict(report)

    # 1. Sensors
    sensor_block: dict[str, list[dict[str, Any]]] = {}
    for stage_name, stage_sensors in profile.sensors_by_stage.items():
        readings: list[dict[str, Any]] = []
        for local_name, spec in stage_sensors.sensors.items():
            truth = _ground_truth_for(profile, stage_name, local_name, spec, report)
            if truth is None or (isinstance(truth, float) and not math.isfinite(truth)):
                continue
            reading = sample_reading(spec, float(truth), rng,
                                     elapsed_hours=elapsed_hours)
            readings.append({"local_name": local_name, **reading.model_dump()})
        if readings:
            sensor_block[stage_name] = readings
    out["sensors"] = sensor_block

    # 2. Events
    bus = EventBus()
    _emit_events_from_report(report, profile.alarms, bus)
    out["events"] = {
        "by_severity": bus.count_by_severity(),
        "worst_severity": bus.worst_severity().value,
        "list": [e.model_dump(mode="json") for e in bus.events],
    }

    # 3. Energy
    out["energy"] = _aggregate_energy(report)

    # 4. Profile identity for audit
    out["plant_profile"] = {
        "name": profile.name,
        "description": profile.description,
        "provenance": profile.provenance.model_dump(),
    }
    return out


__all__ = ["apply_instrumentation"]
