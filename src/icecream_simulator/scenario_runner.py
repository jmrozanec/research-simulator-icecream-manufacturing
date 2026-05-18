"""
Scenario runner — Phase 1 data generation.

Given a ``ScenarioSpec`` (distributions over raw materials, process parameters,
crystallization parameters, and plant profiles), the runner samples N scenarios,
calls ``run_full_cycle`` for each, applies the plant profile's instrumentation
(sensors + events + energy), and writes a flat dataset that ML training can
consume directly.

Outputs in the chosen ``output_dir``:

- ``runs.csv``   — one row per run (flat schema)
- ``runs.jsonl`` — same rows as JSON Lines (preserves nested structure)
- ``runs.parquet`` — same rows as Parquet, only if ``pyarrow`` is available
- ``reports/run_<id>.json`` — full per-run report (sensors, events, energy)
- ``manifest.json`` — sweep metadata: seed, profile, scenario spec, simulator
  version, package git SHA when available

Sampling supports random and Latin Hypercube. The default is LHS because for
small N (10–500) it gives much better coverage than random sampling.
"""

from __future__ import annotations

import json
import math
import os
import random
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from icecream_simulator.crystallization_parameters import (
    CrystallizationParameters,
    DEFAULT_CRYSTALLIZATION_PARAMETERS,
)
from icecream_simulator.instrumentation import apply_instrumentation
from icecream_simulator.plant_profile import PlantProfile, load_default_profile
from icecream_simulator.run_full_cycle import run_full_cycle
from icecream_simulator.schemas import RawMaterials


# ---------------------------------------------------------------------------
# Distributions
# ---------------------------------------------------------------------------


class Distribution(BaseModel):
    """Base class for a one-dimensional distribution."""

    model_config = ConfigDict(extra="forbid")

    def sample(self, u: float) -> float:
        """Map u ∈ [0, 1) to a value."""
        raise NotImplementedError

    def pick(self, rng: random.Random) -> Any:
        return self.sample(rng.random())


class Uniform(Distribution):
    kind: Literal["uniform"] = "uniform"
    lo: float
    hi: float

    def sample(self, u: float) -> float:
        return self.lo + (self.hi - self.lo) * u


class LogUniform(Distribution):
    kind: Literal["log_uniform"] = "log_uniform"
    lo: float
    hi: float

    def sample(self, u: float) -> float:
        lo, hi = math.log(self.lo), math.log(self.hi)
        return math.exp(lo + (hi - lo) * u)


class Triangular(Distribution):
    kind: Literal["triangular"] = "triangular"
    lo: float
    mode: float
    hi: float

    def sample(self, u: float) -> float:
        # Inverse CDF of triangular distribution
        c = (self.mode - self.lo) / (self.hi - self.lo)
        if u < c:
            return self.lo + math.sqrt(u * (self.hi - self.lo) * (self.mode - self.lo))
        return self.hi - math.sqrt((1 - u) * (self.hi - self.lo) * (self.hi - self.mode))


class Constant(Distribution):
    kind: Literal["constant"] = "constant"
    value: float

    def sample(self, u: float) -> float:
        return float(self.value)


class Discrete(Distribution):
    """Sample uniformly from a list of numeric values."""

    kind: Literal["discrete"] = "discrete"
    values: list[float]

    def sample(self, u: float) -> float:
        n = len(self.values)
        idx = min(int(u * n), n - 1)
        return float(self.values[idx])


class Categorical(BaseModel):
    """Sample uniformly from a list of categorical values (e.g. profile names)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["categorical"] = "categorical"
    values: list[Any]

    def pick(self, rng: random.Random) -> Any:
        return rng.choice(self.values)


# ---------------------------------------------------------------------------
# Spec types
# ---------------------------------------------------------------------------


# Anything we sample over the unit-hypercube is a Distribution.
NumericDist = Union[Uniform, LogUniform, Triangular, Constant, Discrete]


class RawMaterialsDist(BaseModel):
    """Distributions for each raw material."""

    model_config = ConfigDict(extra="forbid")

    milk: NumericDist = Constant(value=100.0)
    cream: NumericDist = Constant(value=30.0)
    sugar: NumericDist = Constant(value=25.0)
    stabilizers: NumericDist = Constant(value=1.65)
    emulsifiers_kg: NumericDist = Constant(value=0.35)
    water: NumericDist = Constant(value=43.0)
    cocoa_powder_kg: NumericDist = Constant(value=0.0)
    egg_yolk_kg: NumericDist = Constant(value=0.0)
    vanilla_extract_kg: NumericDist = Constant(value=0.0)
    vanillin_kg: NumericDist = Constant(value=0.0)


class ProcessParamsDist(BaseModel):
    """Distributions for each ``run_full_cycle`` process parameter."""

    model_config = ConfigDict(extra="forbid")

    tank_surface_area_m2: NumericDist = Constant(value=10.0)
    water_volume_L: NumericDist = Constant(value=80.0)
    air_overrun: NumericDist = Constant(value=0.5)
    interface_flush_L: NumericDist = Constant(value=5.0)
    homogenization_pressure_bar: NumericDist = Constant(value=200.0)
    jacket_flow_L_min: NumericDist = Constant(value=20.0)
    preparation_rpm: NumericDist = Constant(value=60.0)
    preparation_mixing_time_s: NumericDist = Constant(value=300.0)
    pasteurization_hold_time_s: NumericDist = Constant(value=15.0)
    flavor_syrup_mass_kg: NumericDist = Constant(value=0.0)
    inclusion_mass_kg: NumericDist = Constant(value=0.0)
    coolant_temp_K: NumericDist = Constant(value=253.15)
    freezer_residence_time_s: NumericDist = Constant(value=45.0)
    dasher_rpm: NumericDist = Constant(value=55.0)
    barrel_diameter_m: NumericDist = Constant(value=0.15)
    volume_fraction_wall_ice: NumericDist = Constant(value=0.28)
    storage_time_s: NumericDist = Constant(value=0.0)
    storage_temp_K: NumericDist = Constant(value=248.15)
    bioplastic_yield_coefficient: NumericDist = Constant(value=0.4)


class ScenarioSpec(BaseModel):
    """A complete specification for one parameter sweep.

    Each field is a distribution over the parameter's value. The runner expands
    these into N concrete scenarios, calls ``run_full_cycle`` with them, and
    writes one row per run.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = "default_sweep"
    raw_materials: RawMaterialsDist = Field(default_factory=RawMaterialsDist)
    process: ProcessParamsDist = Field(default_factory=ProcessParamsDist)
    literature_preset_ids: Optional[list[str]] = None
    crystallization_parameter_sets: Optional[list[CrystallizationParameters]] = None
    include_cleaning_phase: bool = True

    def numeric_field_keys(self) -> list[tuple[str, str]]:
        """Return ``(group, field)`` pairs for every numeric-distribution field."""
        keys: list[tuple[str, str]] = []
        for fname in RawMaterialsDist.model_fields:
            keys.append(("raw_materials", fname))
        for fname in ProcessParamsDist.model_fields:
            keys.append(("process", fname))
        return keys

    def dist_for(self, group: str, field_name: str) -> Distribution:
        if group == "raw_materials":
            return getattr(self.raw_materials, field_name)
        if group == "process":
            return getattr(self.process, field_name)
        raise KeyError(f"Unknown group {group!r}")


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


def _latin_hypercube(d: int, n: int, rng: random.Random) -> list[list[float]]:
    """Latin Hypercube samples in [0, 1)^d with random permutations per dim."""
    if n <= 0:
        return []
    cuts = [(i + rng.random()) / n for i in range(n)]
    columns: list[list[float]] = []
    for _ in range(d):
        col = list(cuts)
        rng.shuffle(col)
        columns.append(col)
    # Transpose to row-major
    return [[columns[j][i] for j in range(d)] for i in range(n)]


def _random_hypercube(d: int, n: int, rng: random.Random) -> list[list[float]]:
    return [[rng.random() for _ in range(d)] for _ in range(n)]


def _expand_scenario(
    spec: ScenarioSpec,
    u: list[float],
    rng: random.Random,
) -> dict[str, Any]:
    """Map a unit-hypercube row to concrete simulator inputs."""
    keys = spec.numeric_field_keys()
    raw: dict[str, float] = {}
    proc: dict[str, float] = {}
    for (group, fname), value_u in zip(keys, u):
        dist = spec.dist_for(group, fname)
        v = dist.sample(value_u)
        if group == "raw_materials":
            raw[fname] = v
        else:
            proc[fname] = v

    out: dict[str, Any] = {
        "raw_materials": RawMaterials(**raw),
        **proc,
        "include_cleaning_phase": spec.include_cleaning_phase,
    }

    # Optionally pick a literature preset (overrides raw_materials)
    if spec.literature_preset_ids:
        chosen = rng.choice(spec.literature_preset_ids)
        out.pop("raw_materials", None)
        out["literature_preset_id"] = chosen

    # Optionally pick a crystallization parameter set
    if spec.crystallization_parameter_sets:
        out["crystallization_parameters"] = rng.choice(spec.crystallization_parameter_sets)

    return out


# ---------------------------------------------------------------------------
# Row flattening
# ---------------------------------------------------------------------------


def _flatten_row(
    run_id: int,
    seed: int,
    raw_inputs: dict[str, Any],
    enriched: dict[str, Any],
    profile: PlantProfile,
) -> dict[str, Any]:
    """Build one flat row for CSV/Parquet output. Keep dict-typed columns under
    ``meta_*`` so the JSONL has the full structure."""
    inputs = enriched.get("inputs", {}) or {}
    quality = enriched.get("quality", {}) or {}
    efficiency = enriched.get("efficiency_summary", {}) or {}
    energy = enriched.get("energy", {}) or {}
    events = enriched.get("events", {}) or {}
    sensors = enriched.get("sensors", {}) or {}

    row: dict[str, Any] = {
        "run_id": run_id,
        "seed": seed,
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "plant_profile_name": profile.name,
        "literature_preset_id": inputs.get("literature_preset_id") or "",
    }

    # Raw material inputs
    rm = raw_inputs.get("raw_materials")
    if rm is not None:
        for fname in RawMaterials.model_fields:
            row[f"rm_{fname}"] = getattr(rm, fname, None)

    # Process inputs we sampled
    for fname in ProcessParamsDist.model_fields:
        v = raw_inputs.get(fname)
        if v is None:
            v = inputs.get(fname)
        row[f"pp_{fname}"] = v

    # Quality and efficiency
    for k, v in quality.items():
        row[f"q_{k}"] = v
    row["product_kg"] = enriched.get("mixer", {}).get("product_to_freezer_kg")
    row["ice_cream_volume_L"] = enriched.get("mixer", {}).get("ice_cream_volume_L")
    row["mass_balance_closed"] = efficiency.get("mass_balance_closed")
    row["plastic_kg_per_tonne_input"] = efficiency.get("plastic_kg_per_tonne_input")
    row["bioplastic_mass_kg"] = enriched.get("bioconversion", {}).get("bioplastic_mass_kg")
    row["filter_saturation_pct"] = enriched.get("filtration", {}).get("filter_saturation_pct")

    # Energy
    row["energy_total_J"] = energy.get("total_J")
    row["energy_thermal_J"] = energy.get("thermal_J")
    row["energy_electrical_J"] = energy.get("electrical_J")
    row["energy_total_kWh"] = energy.get("total_kWh")

    # Events
    counts = events.get("by_severity", {}) or {}
    for sev in ("info", "warn", "alarm", "critical"):
        row[f"events_{sev}"] = counts.get(sev, 0)
    row["events_worst"] = events.get("worst_severity", "info")

    # Sensor readings (value + truth + sigma per channel; flat names)
    for stage_name, readings in sensors.items():
        for r in readings:
            local = r["local_name"]
            base = f"s_{stage_name}.{local}"
            row[f"{base}.value"] = r.get("value")
            row[f"{base}.truth"] = r.get("truth")
            row[f"{base}.sigma"] = r.get("sigma")
            if r.get("dropped"):
                row[f"{base}.dropped"] = True
            if r.get("out_of_range"):
                row[f"{base}.out_of_range"] = True

    return row


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return None


def _write_manifest(
    out_dir: Path,
    spec: ScenarioSpec,
    n: int,
    seed: int,
    profile: PlantProfile,
    sampler: str,
    n_succeeded: int,
    n_failed: int,
    elapsed_s: float,
) -> None:
    # Lazy version lookup to avoid circular import at package init time
    try:
        from icecream_simulator import __version__ as sim_version
    except ImportError:
        sim_version = "unknown"
    manifest = {
        "simulator_version": sim_version,
        "git_sha": _git_sha(),
        "scenario_name": spec.name,
        "scenario_spec": spec.model_dump(),
        "n_requested": n,
        "n_succeeded": n_succeeded,
        "n_failed": n_failed,
        "elapsed_s": elapsed_s,
        "seed": seed,
        "sampler": sampler,
        "plant_profile": {
            "name": profile.name,
            "description": profile.description,
            "provenance": profile.provenance.model_dump(),
        },
        "python_version": sys.version,
        "platform": sys.platform,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols: list[str] = []
    seen: set[str] = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                cols.append(k)
    import csv
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


def _write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")


def _try_write_parquet(rows: list[dict[str, Any]], path: Path) -> bool:
    try:
        import pandas as pd  # type: ignore
        import pyarrow  # noqa: F401
    except Exception:
        return False
    pd.DataFrame(rows).to_parquet(path, index=False)
    return True


# ---------------------------------------------------------------------------
# Top-level entry
# ---------------------------------------------------------------------------


@dataclass
class SweepResult:
    out_dir: Path
    n_succeeded: int
    n_failed: int
    elapsed_s: float
    rows: list[dict[str, Any]] = field(default_factory=list)


def run_sweep(
    spec: ScenarioSpec,
    n: int,
    output_dir: str | Path,
    *,
    seed: int = 0,
    profile: PlantProfile | None = None,
    sampler: Literal["lhs", "random"] = "lhs",
    save_full_reports: bool = True,
    on_run: Callable[[int, dict], None] | None = None,
) -> SweepResult:
    """Run ``n`` scenarios sampled from ``spec``; write a dataset to ``output_dir``.

    Args:
        spec: distributions over raw materials and process parameters.
        n: number of scenarios.
        output_dir: target directory; created if missing.
        seed: RNG seed for reproducibility (sampler and sensor noise both use it).
        profile: plant profile for instrumentation; default = shipped midsize line.
        sampler: 'lhs' (default, better coverage) or 'random'.
        save_full_reports: if True, write one JSON per run with the full report.
        on_run: optional callback ``(run_id, row)`` for live monitoring.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if save_full_reports:
        (out_dir / "reports").mkdir(exist_ok=True)

    prof = profile or load_default_profile()
    rng = random.Random(seed)

    keys = spec.numeric_field_keys()
    d = len(keys)
    if sampler == "lhs":
        u_rows = _latin_hypercube(d, n, rng)
    else:
        u_rows = _random_hypercube(d, n, rng)

    rows: list[dict[str, Any]] = []
    n_failed = 0
    t0 = time.time()

    for i, u in enumerate(u_rows):
        run_seed = seed * 1_000_003 + i
        run_rng = random.Random(run_seed)
        try:
            inputs = _expand_scenario(spec, u, run_rng)
            report = run_full_cycle(**inputs)
            enriched = apply_instrumentation(report, prof, seed=run_seed)
            row = _flatten_row(i, run_seed, inputs, enriched, prof)
            rows.append(row)
            if save_full_reports:
                # Drop typed_report (Pydantic objects don't go to JSON cleanly)
                light = {k: v for k, v in enriched.items() if k != "typed_report"}
                (out_dir / "reports" / f"run_{i:06d}.json").write_text(
                    json.dumps(light, indent=2, default=str), encoding="utf-8",
                )
            if on_run is not None:
                on_run(i, row)
        except Exception as e:  # noqa: BLE001 — record and continue
            n_failed += 1
            err_path = out_dir / "reports" / f"run_{i:06d}.error.txt"
            try:
                err_path.parent.mkdir(parents=True, exist_ok=True)
                err_path.write_text(f"{type(e).__name__}: {e}\n", encoding="utf-8")
            except Exception:
                pass
            continue

    elapsed = time.time() - t0
    _write_csv(rows, out_dir / "runs.csv")
    _write_jsonl(rows, out_dir / "runs.jsonl")
    _try_write_parquet(rows, out_dir / "runs.parquet")
    _write_manifest(out_dir, spec, n, seed, prof, sampler,
                    n_succeeded=len(rows), n_failed=n_failed, elapsed_s=elapsed)

    return SweepResult(out_dir=out_dir, n_succeeded=len(rows),
                       n_failed=n_failed, elapsed_s=elapsed, rows=rows)


# ---------------------------------------------------------------------------
# Convenience: a "diverse" preset
# ---------------------------------------------------------------------------


def diverse_industrial_spec(name: str = "diverse_industrial") -> ScenarioSpec:
    """A ready-to-run spec that varies the most influential knobs over realistic
    bands. Use this if you just want a credible diverse-scenario dataset.

    Ranges below are intentionally wide enough to surface alarms and quality
    excursions while staying within plausible operational envelopes.
    """
    return ScenarioSpec(
        name=name,
        raw_materials=RawMaterialsDist(
            milk=Uniform(lo=70.0, hi=130.0),
            cream=Uniform(lo=15.0, hi=55.0),
            sugar=Uniform(lo=18.0, hi=40.0),
            stabilizers=Uniform(lo=0.2, hi=1.8),
            emulsifiers_kg=Uniform(lo=0.05, hi=0.5),
            water=Uniform(lo=20.0, hi=60.0),
        ),
        process=ProcessParamsDist(
            homogenization_pressure_bar=Uniform(lo=120.0, hi=280.0),
            pasteurization_hold_time_s=Triangular(lo=10.0, mode=15.0, hi=30.0),
            air_overrun=Uniform(lo=0.30, hi=1.00),
            preparation_rpm=Uniform(lo=40.0, hi=90.0),
            preparation_mixing_time_s=Uniform(lo=180.0, hi=600.0),
            jacket_flow_L_min=Uniform(lo=10.0, hi=40.0),
            coolant_temp_K=Uniform(lo=248.15, hi=258.15),
            freezer_residence_time_s=Uniform(lo=30.0, hi=90.0),
            dasher_rpm=Uniform(lo=40.0, hi=90.0),
            barrel_diameter_m=Discrete(values=[0.12, 0.15, 0.18]),
            volume_fraction_wall_ice=Uniform(lo=0.18, hi=0.40),
            storage_time_s=Discrete(values=[0.0, 24 * 3600.0, 72 * 3600.0,
                                            168 * 3600.0]),
            storage_temp_K=Uniform(lo=243.15, hi=253.15),
            water_volume_L=Uniform(lo=60.0, hi=120.0),
            interface_flush_L=Uniform(lo=2.0, hi=10.0),
            bioplastic_yield_coefficient=Uniform(lo=0.30, hi=0.50),
        ),
        include_cleaning_phase=True,
    )


__all__ = [
    "Distribution",
    "Uniform",
    "LogUniform",
    "Triangular",
    "Constant",
    "Discrete",
    "Categorical",
    "RawMaterialsDist",
    "ProcessParamsDist",
    "ScenarioSpec",
    "SweepResult",
    "run_sweep",
    "diverse_industrial_spec",
]
