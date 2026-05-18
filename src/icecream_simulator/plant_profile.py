"""
Synthetic plant profiles — sensor maps, alarm thresholds, equipment identity.

A profile bundles every assumption that a *plant* would impose on a simulated
run: which sensors exist on each stage, their accuracy class, sampling rate,
expected drift, and the alarm thresholds an operator (or a supervisor agent)
would use. Each value carries a ``Provenance``.

Defaults below are drawn from public sources only — FDA Grade A PMO (2017),
3-A Sanitary Standards, IEC 60751 (PT100 class A), and standard industrial-grade
flow/pressure transmitter datasheets (Endress+Hauser Promass, Anderson-Negele,
Tetra Pak / GEA application notes). Citation strings point at the regulation
section or datasheet ID; replace with site-specific values when you have them.

The single shipped profile is ``midsize_continuous_dairy.json`` under
``data/plant_profiles/``. Build new profiles by editing that JSON or by calling
``build_midsize_continuous_dairy()`` and persisting to disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from icecream_simulator.provenance import Provenance, SourceKind
from icecream_simulator.sensors import AccuracyKind, SensorSpec


# ---------------------------------------------------------------------------
# Vendor / standards helpers — provenance-tagged sensor factories
# ---------------------------------------------------------------------------


def pt100_class_a(
    name: str, *, range_min: float = -50.0, range_max: float = 200.0,
    sampling_hz: float = 1.0, bias: float = 0.0, drift_per_hour: float = 0.0,
    dropout_prob: float = 0.0,
) -> SensorSpec:
    """PT100 class A (IEC 60751): ±(0.15 + 0.002·|T|) °C; absolute approximated by 0.3 °C
    over typical dairy ranges. Use for any mix or coolant temperature loop."""
    return SensorSpec(
        name=name, measurand="temperature", unit="K",
        accuracy=0.30, accuracy_kind=AccuracyKind.ABS,
        range_min=range_min + 273.15, range_max=range_max + 273.15,
        sampling_hz=sampling_hz, bias=bias, drift_per_hour=drift_per_hour,
        dropout_prob=dropout_prob,
        provenance=Provenance(kind=SourceKind.STANDARD,
                              citation="IEC 60751:2008 (PT100 class A)",
                              note="±(0.15 + 0.002·|T|) °C; approximated as 0.30 K over dairy range"),
    )


def piezo_pressure(
    name: str, *, range_max_bar: float = 400.0, accuracy_fs: float = 0.0025,
    sampling_hz: float = 10.0, bias: float = 0.0, drift_per_hour: float = 0.0,
) -> SensorSpec:
    """Piezoresistive pressure transmitter, ±0.25 % FS typical industrial class.

    Used for homogenizer 1st/2nd stage pressure, freezer barrel backpressure,
    membrane TMP, cavitation inlet pressure.
    """
    return SensorSpec(
        name=name, measurand="pressure", unit="bar",
        accuracy=accuracy_fs, accuracy_kind=AccuracyKind.REL_FS,
        range_min=0.0, range_max=range_max_bar,
        sampling_hz=sampling_hz, bias=bias, drift_per_hour=drift_per_hour,
        provenance=Provenance(kind=SourceKind.VENDOR,
                              citation="Industrial piezoresistive class, ±0.25% FS",
                              note="Anderson-Negele / E+H Cerabar S generic class"),
    )


def coriolis_flow(
    name: str, *, range_max_Lmin: float = 200.0, accuracy_rate: float = 0.001,
    sampling_hz: float = 5.0, bias: float = 0.0,
) -> SensorSpec:
    """Coriolis mass flowmeter, ±0.1 % of rate (Promass-class).

    Used for mix flow into PHE/freezer, coolant flow, retentate flow.
    """
    return SensorSpec(
        name=name, measurand="flow", unit="L/min",
        accuracy=accuracy_rate, accuracy_kind=AccuracyKind.REL_RATE,
        range_min=0.0, range_max=range_max_Lmin,
        sampling_hz=sampling_hz, bias=bias,
        provenance=Provenance(kind=SourceKind.VENDOR,
                              citation="E+H Promass Coriolis, ±0.10% of rate",
                              note="Industrial dairy class"),
    )


def mag_flow(
    name: str, *, range_max_Lmin: float = 500.0, accuracy_rate: float = 0.002,
    sampling_hz: float = 5.0,
) -> SensorSpec:
    """Electromagnetic flowmeter, ±0.2 % of rate. CIP, water, wastewater paths."""
    return SensorSpec(
        name=name, measurand="flow", unit="L/min",
        accuracy=accuracy_rate, accuracy_kind=AccuracyKind.REL_RATE,
        range_min=0.0, range_max=range_max_Lmin,
        sampling_hz=sampling_hz,
        provenance=Provenance(kind=SourceKind.VENDOR,
                              citation="Magnetic flowmeter ±0.20% of rate",
                              note="E+H Promag generic class for conductive fluids"),
    )


def motor_current(
    name: str, *, range_max_A: float = 200.0, accuracy_fs: float = 0.01,
    sampling_hz: float = 50.0,
) -> SensorSpec:
    """VFD-reported motor current, ±1 % FS. Dasher motor and agitator load."""
    return SensorSpec(
        name=name, measurand="motor_current", unit="A",
        accuracy=accuracy_fs, accuracy_kind=AccuracyKind.REL_FS,
        range_min=0.0, range_max=range_max_A,
        sampling_hz=sampling_hz,
        provenance=Provenance(kind=SourceKind.VENDOR,
                              citation="VFD class ±1% FS",
                              note="ABB ACS580 / Danfoss FC-302 generic class"),
    )


def speed_sensor(
    name: str, *, range_max_rpm: float = 200.0, accuracy_fs: float = 0.005,
    sampling_hz: float = 10.0,
) -> SensorSpec:
    """Tachometer / VFD-reported speed, ±0.5 % FS."""
    return SensorSpec(
        name=name, measurand="speed", unit="rpm",
        accuracy=accuracy_fs, accuracy_kind=AccuracyKind.REL_FS,
        range_min=0.0, range_max=range_max_rpm,
        sampling_hz=sampling_hz,
        provenance=Provenance(kind=SourceKind.VENDOR,
                              citation="VFD speed feedback ±0.5% FS",
                              note=""),
    )


def conductivity(name: str) -> SensorSpec:
    """In-line conductivity for CIP / permeate, ±1 % of rate."""
    return SensorSpec(
        name=name, measurand="conductivity", unit="mS/cm",
        accuracy=0.01, accuracy_kind=AccuracyKind.REL_RATE,
        range_min=0.0, range_max=200.0, sampling_hz=2.0,
        provenance=Provenance(kind=SourceKind.VENDOR,
                              citation="Toroidal conductivity, ±1% rate",
                              note="E+H Indumax generic class"),
    )


def turbidity(name: str) -> SensorSpec:
    """In-line turbidity for CIP return, ±2 % FS."""
    return SensorSpec(
        name=name, measurand="turbidity", unit="NTU",
        accuracy=0.02, accuracy_kind=AccuracyKind.REL_FS,
        range_min=0.0, range_max=4000.0, sampling_hz=1.0,
        provenance=Provenance(kind=SourceKind.VENDOR,
                              citation="Optical turbidity, ±2% FS",
                              note=""),
    )


def derived_quality(
    name: str, *, measurand: str, unit: str,
    range_min: float, range_max: float,
    accuracy_rate: float = 0.05,
) -> SensorSpec:
    """Derived / inferred lab quantity (e.g. d32 by laser diffraction, ice
    crystal size by image analysis). Treated as ±5 % of rate by default."""
    return SensorSpec(
        name=name, measurand=measurand, unit=unit,
        accuracy=accuracy_rate, accuracy_kind=AccuracyKind.REL_RATE,
        range_min=range_min, range_max=range_max, sampling_hz=0.1,
        provenance=Provenance(kind=SourceKind.ASSUMPTION,
                              citation="lab analytics typical ±5% rate",
                              note="Replace with measured instrument spec"),
    )


# ---------------------------------------------------------------------------
# Alarms and profile model
# ---------------------------------------------------------------------------


class AlarmThresholds(BaseModel):
    """Quality and operational thresholds used to derive events from a report."""

    log10_reduction_min: float = 5.0
    fat_globule_d32_um_max: float = 1.0
    ice_crystal_mean_um_max: float = 50.0
    ice_crystal_mean_um_warn: float = 40.0
    hardness_kPa_min: float = 200.0
    hardness_kPa_max: float = 2000.0
    overrun_min: float = 0.30
    overrun_max: float = 1.10
    cavitation_intensity_min: float = 0.20
    filter_saturation_warn: float = 0.70
    filter_saturation_alarm: float = 0.90
    mass_balance_relative_tolerance: float = 1e-4


class StageSensors(BaseModel):
    """The sensor list for one stage, keyed by short local name."""

    stage: str
    sensors: dict[str, SensorSpec] = Field(default_factory=dict)


class PlantProfile(BaseModel):
    """Synthetic plant profile (sensor map + alarms + identity)."""

    name: str
    description: str
    provenance: Provenance
    sensors_by_stage: dict[str, StageSensors] = Field(default_factory=dict)
    alarms: AlarmThresholds = Field(default_factory=AlarmThresholds)

    def find_sensor(self, stage: str, measurand: str) -> Optional[SensorSpec]:
        """Return the first sensor matching ``(stage, measurand)`` if any."""
        ss = self.sensors_by_stage.get(stage)
        if ss is None:
            return None
        for s in ss.sensors.values():
            if s.measurand == measurand:
                return s
        return None

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> "PlantProfile":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Shipped profile: midsize continuous dairy line
# ---------------------------------------------------------------------------


def build_midsize_continuous_dairy() -> PlantProfile:
    """A representative midsize HTST continuous-freezer dairy line.

    Sensor selection follows FDA Grade A PMO (2017) §6 (HTST pasteurization,
    required indicating thermometer, recording thermometer, FDV, flow
    controls) and standard industrial instrument classes. Treat as a
    *credibly-shaped* synthetic plant rather than a specific site.
    """
    profile = PlantProfile(
        name="midsize_continuous_dairy",
        description=(
            "Midsize HTST continuous-freezer dairy ice cream line with a "
            "wastewater pretreatment train (prefiltration → hydrodynamic "
            "cavitation → nanofiltration → PHA bioconversion). Sensor list "
            "and accuracy classes from FDA PMO + IEC 60751 + standard "
            "industrial transmitter datasheets."
        ),
        provenance=Provenance(
            kind=SourceKind.STANDARD,
            citation="FDA Grade A Pasteurized Milk Ordinance (2017); 3-A Sanitary Standards; IEC 60751",
            note="Composite synthetic profile; replace with site values when available",
        ),
        alarms=AlarmThresholds(),
    )
    s = profile.sensors_by_stage

    s["preparation_mix"] = StageSensors(stage="preparation_mix", sensors={
        "mix_T": pt100_class_a("prep.mix_T", range_min=-10.0, range_max=120.0),
        "agitator_rpm": speed_sensor("prep.agitator_rpm", range_max_rpm=200.0),
        "agitator_current": motor_current("prep.agitator_current", range_max_A=100.0),
    })

    s["pasteurization"] = StageSensors(stage="pasteurization", sensors={
        # PMO §6.B: indicating thermometer required at hold-tube outlet
        "hold_outlet_T": pt100_class_a("past.hold_outlet_T", range_min=0.0, range_max=120.0,
                                       sampling_hz=2.0),
        "mix_flow": coriolis_flow("past.mix_flow", range_max_Lmin=400.0),
        # COD-style indirect quality
        "lethality_log10": derived_quality("past.lethality_log10",
                                           measurand="log10_reduction",
                                           unit="log10", range_min=0.0, range_max=8.0,
                                           accuracy_rate=0.05),
    })

    s["homogenization"] = StageSensors(stage="homogenization", sensors={
        "p1_pressure": piezo_pressure("hom.p1_pressure", range_max_bar=400.0),
        "p2_pressure": piezo_pressure("hom.p2_pressure", range_max_bar=80.0),
        "motor_current": motor_current("hom.motor_current", range_max_A=400.0),
        "d32_lab": derived_quality("hom.d32_lab", measurand="d32", unit="um",
                                   range_min=0.05, range_max=20.0, accuracy_rate=0.06),
    })

    s["cooling_phe"] = StageSensors(stage="cooling_phe", sensors={
        "mix_in_T":  pt100_class_a("cool.mix_in_T",  range_min=0.0, range_max=120.0),
        "mix_out_T": pt100_class_a("cool.mix_out_T", range_min=-5.0, range_max=120.0),
        "coolant_in_T":  pt100_class_a("cool.coolant_in_T",  range_min=-30.0, range_max=30.0),
        "coolant_out_T": pt100_class_a("cool.coolant_out_T", range_min=-30.0, range_max=30.0),
        "coolant_flow": mag_flow("cool.coolant_flow", range_max_Lmin=600.0),
    })

    s["ageing_vat"] = StageSensors(stage="ageing_vat", sensors={
        "mix_T":  pt100_class_a("age.mix_T", range_min=-5.0, range_max=20.0,
                                drift_per_hour=0.005),  # slow drift typical
        "agitator_rpm":     speed_sensor("age.agitator_rpm", range_max_rpm=120.0),
        "agitator_current": motor_current("age.agitator_current", range_max_A=60.0),
        "jacket_in_T":  pt100_class_a("age.jacket_in_T",  range_min=-30.0, range_max=20.0),
        "jacket_out_T": pt100_class_a("age.jacket_out_T", range_min=-30.0, range_max=20.0),
        "jacket_flow": mag_flow("age.jacket_flow", range_max_Lmin=120.0),
    })

    s["freezer"] = StageSensors(stage="freezer", sensors={
        "mix_in_T":     pt100_class_a("freezer.mix_in_T",  range_min=-5.0, range_max=20.0,
                                      sampling_hz=2.0),
        "mix_out_T":    pt100_class_a("freezer.mix_out_T", range_min=-15.0, range_max=10.0,
                                      sampling_hz=2.0),
        "evap_T":       pt100_class_a("freezer.evap_T", range_min=-40.0, range_max=0.0,
                                      sampling_hz=2.0),
        "barrel_dp":    piezo_pressure("freezer.barrel_dp", range_max_bar=20.0,
                                       accuracy_fs=0.005),
        "dasher_current": motor_current("freezer.dasher_current", range_max_A=200.0,
                                        sampling_hz=50.0),
        "dasher_rpm":   speed_sensor("freezer.dasher_rpm", range_max_rpm=200.0),
        "air_flow":     mag_flow("freezer.air_flow", range_max_Lmin=60.0),
        # Derived ice metrics (lab / image analysis, off-line in many plants)
        "ice_mean_um":  derived_quality("freezer.ice_mean_um",
                                        measurand="ice_crystal_size", unit="um",
                                        range_min=1.0, range_max=200.0, accuracy_rate=0.08),
        "overrun":      derived_quality("freezer.overrun",
                                        measurand="overrun", unit="frac",
                                        range_min=0.0, range_max=1.5, accuracy_rate=0.03),
    })

    s["hardening"] = StageSensors(stage="hardening", sensors={
        "zone_T":         pt100_class_a("hard.zone_T", range_min=-50.0, range_max=10.0),
        "product_surf_T": pt100_class_a("hard.product_surf_T", range_min=-50.0, range_max=10.0,
                                        bias=0.5, drift_per_hour=0.01,
                                        dropout_prob=0.005),  # IR sensors drift more
        "hardness_kPa": derived_quality("hard.hardness_kPa", measurand="concentration",
                                        unit="kPa", range_min=100.0, range_max=5000.0,
                                        accuracy_rate=0.10),
    })

    s["packaging"] = StageSensors(stage="packaging", sensors={
        "net_weight": SensorSpec(
            name="pack.net_weight", measurand="level", unit="kg",
            accuracy=0.005, accuracy_kind=AccuracyKind.REL_RATE,
            range_min=0.0, range_max=10.0, sampling_hz=10.0,
            provenance=Provenance.vendor("Checkweigher ±0.5% rate"),
        ),
        "fill_count": SensorSpec(
            name="pack.fill_count", measurand="level", unit="count",
            accuracy=1e-6, accuracy_kind=AccuracyKind.REL_RATE,
            range_min=0.0, range_max=1e6, sampling_hz=1.0,
            provenance=Provenance.vendor("Optical fill counter"),
        ),
    })

    s["cip"] = StageSensors(stage="cip", sensors={
        "supply_T":   pt100_class_a("cip.supply_T", range_min=10.0, range_max=95.0),
        "return_T":   pt100_class_a("cip.return_T", range_min=10.0, range_max=95.0),
        "flow":       mag_flow("cip.flow", range_max_Lmin=500.0),
        "supply_p":   piezo_pressure("cip.supply_p", range_max_bar=10.0),
        "conductivity": conductivity("cip.conductivity"),
        "turbidity_return": turbidity("cip.turbidity_return"),
    })

    s["prefiltration"] = StageSensors(stage="prefiltration", sensors={
        "inlet_p":  piezo_pressure("pref.inlet_p",  range_max_bar=10.0),
        "outlet_p": piezo_pressure("pref.outlet_p", range_max_bar=10.0),
        "flow":     mag_flow("pref.flow", range_max_Lmin=500.0),
    })

    s["hydrodynamic_cavitation"] = StageSensors(stage="hydrodynamic_cavitation", sensors={
        "inlet_p":   piezo_pressure("cav.inlet_p",  range_max_bar=20.0),
        "throat_dp": piezo_pressure("cav.throat_dp", range_max_bar=20.0, accuracy_fs=0.005),
        "outlet_T":  pt100_class_a("cav.outlet_T", range_min=10.0, range_max=80.0),
        "flow":      mag_flow("cav.flow", range_max_Lmin=500.0),
    })

    s["filtration"] = StageSensors(stage="filtration", sensors={
        "feed_p":      piezo_pressure("nf.feed_p",      range_max_bar=40.0),
        "permeate_p":  piezo_pressure("nf.permeate_p",  range_max_bar=10.0),
        "retentate_p": piezo_pressure("nf.retentate_p", range_max_bar=40.0),
        "permeate_flow": coriolis_flow("nf.permeate_flow", range_max_Lmin=200.0),
        "permeate_conductivity": conductivity("nf.permeate_conductivity"),
        "feed_T": pt100_class_a("nf.feed_T", range_min=5.0, range_max=60.0),
    })

    s["bioconversion"] = StageSensors(stage="bioconversion", sensors={
        "pH":   SensorSpec(name="bio.pH", measurand="ph", unit="pH",
                           accuracy=0.05, accuracy_kind=AccuracyKind.ABS,
                           range_min=2.0, range_max=12.0, sampling_hz=1.0,
                           drift_per_hour=0.01,
                           provenance=Provenance.vendor("Memosens pH ±0.05 pH; drift typical")),
        "DO":   SensorSpec(name="bio.DO", measurand="concentration", unit="%sat",
                           accuracy=0.02, accuracy_kind=AccuracyKind.REL_FS,
                           range_min=0.0, range_max=200.0, sampling_hz=1.0,
                           provenance=Provenance.vendor("Optical DO ±2% FS")),
        "T":    pt100_class_a("bio.T", range_min=10.0, range_max=50.0),
        "OD":   derived_quality("bio.OD", measurand="concentration",
                                unit="OD600", range_min=0.0, range_max=15.0,
                                accuracy_rate=0.05),
    })

    return profile


def default_profile_path() -> Path:
    """Resolve the shipped JSON profile location (under the package data dir)."""
    return Path(__file__).resolve().parent / "data" / "plant_profiles" / "midsize_continuous_dairy.json"


def load_default_profile() -> PlantProfile:
    """Load the shipped midsize-continuous-dairy profile, building if missing."""
    p = default_profile_path()
    if p.exists():
        return PlantProfile.from_json(p)
    profile = build_midsize_continuous_dairy()
    p.parent.mkdir(parents=True, exist_ok=True)
    profile.to_json(p)
    return profile


__all__ = [
    "AccuracyKind",
    "AlarmThresholds",
    "StageSensors",
    "PlantProfile",
    "pt100_class_a",
    "piezo_pressure",
    "coriolis_flow",
    "mag_flow",
    "motor_current",
    "speed_sensor",
    "conductivity",
    "turbidity",
    "derived_quality",
    "build_midsize_continuous_dairy",
    "default_profile_path",
    "load_default_profile",
]
