---
name: run-icecream-simulator
description: >-
  Runs the ice cream manufacturing and wastewater valorization simulator (CLI or
  Python API) and interprets structured reports. Use when exploring process
  parameters, comparing literature presets, checking mass balance, ice crystal or
  texture proxies, CIP/filtration/cavitation/bioplastic outputs, parameter sweeps,
  or when the user asks to simulate, benchmark, or validate hypotheses in this
  repository.
version: 1.0.0
---

# Run Ice Cream Simulator

Run the simulator **during reasoning** (shell or short Python snippets), then cite numeric results from the report. Do not guess outputs when a quick run is feasible.

## Prerequisites

From the **repository root**:

```bash
pip install -e .
# or: uv sync && uv run python run.py
```

`run.py` prepends `src/` so an editable install is optional for CLI-only runs.

## When to run

| Goal | Approach |
|------|----------|
| Default full cycle + human summary | `python run.py` |
| Literature recipe | `python run.py --preset <ID>` |
| Compare all presets (tabular) | `python run.py --literature-suite` |
| Production chain only (faster) | `python run.py --no-cleaning` |
| Custom inputs / extract JSON | Python API (below) |
| Many randomized runs | `run_sweep` (see Sweeps) |

Preset IDs: `HARFOUSH_2024_BASELINE`, `GIUDICI_2021_INDUSTRIAL`, `GIUDICI_2021_ARTISANAL`, `KONSTANTAS_2019_*`, `COOK_HARTEL_CRYSTALLIZATION_REFERENCE`, `WARI_ZHU_2019_SCHEDULING_REFERENCE`. List at runtime: `python -c "from icecream_simulator import list_preset_ids; print(list_preset_ids())"`.

## CLI (preferred for a single run)

```bash
python run.py
python run.py --preset GIUDICI_2021_INDUSTRIAL
python run.py --literature-suite --no-cleaning
uv run python run.py
```

## Python API (structured output)

```python
import json
import sys
from pathlib import Path

# If package not installed: sys.path.insert(0, str(Path("src").resolve()))

from icecream_simulator import RawMaterials, run_full_cycle, list_preset_ids

report = run_full_cycle(
    raw_materials=RawMaterials(
        milk=100, cream=30, sugar=25, stabilizers=1.65, emulsifiers_kg=0.35, water=43
    ),
    air_overrun=0.5,
    include_cleaning_phase=True,
    # literature_preset_id="GIUDICI_2021_INDUSTRIAL",  # alternative to raw_materials
)

payload = {k: v for k, v in report.items() if k != "typed_report"}
print(json.dumps(payload, indent=2, default=str))
```

One-liner from repo root (after `pip install -e .`):

```bash
python -c "import json; from icecream_simulator import run_full_cycle; r=run_full_cycle(include_cleaning_phase=False); print(json.dumps({k:v for k,v in r.items() if k!='typed_report'}, indent=2, default=str))"
```

### High-signal report keys

| Key | Use |
|-----|-----|
| `efficiency_summary.mass_balance_closed` | Sanity check (should be `true`) |
| `mixer.product_to_freezer_kg`, `mixer.ice_cream_volume_L` | Throughput |
| `quality.ice_crystal_mean_um`, `quality.hardness_proxy_kPa` | Ice / texture proxies |
| `quality.log10_pathogen_reduction`, `quality.fat_globule_d32_um` | Pasteurization / homogenization |
| `cip`, `prefiltration`, `hydrodynamic_cavitation`, `wastewater_to_nanofiltration` | Wash water train (if cleaning enabled) |
| `bioconversion.bioplastic_mass_kg` | PHA from retentate sugar |
| `industrial_chain.stages_detail` | Per-stage physics |
| `inputs` | Echo of all run parameters (incl. `crystallization_parameters`) |
| `energy` | Stage energy aggregates |

Skip wastewater keys when `include_cleaning_phase=False`.

### Common parameters (`run_full_cycle`)

- **Recipe:** `raw_materials` or `literature_preset_id`
- **Freezer / ice:** `air_overrun`, `coolant_temp_K`, `freezer_residence_time_s`, `dasher_rpm`, `crystallization_parameters` or load from `examples/crystallization_parameters_example.json`
- **Plant ops:** `homogenization_pressure_bar`, `pasteurization_hold_time_s`, `interface_flush_L`, `storage_time_s`, `storage_temp_K`
- **Valorization:** `include_cleaning_phase`, `water_volume_L`, `bioplastic_yield_coefficient`, `bioconversion_model`

Full parameter list: `run_full_cycle` in `src/icecream_simulator/run_full_cycle.py`.

## Sweeps

For Monte Carlo / LHS datasets (CSV, JSONL, per-run JSON):

```python
from pathlib import Path
from icecream_simulator import diverse_industrial_spec, run_sweep

run_sweep(diverse_industrial_spec(), n=20, output_dir=Path("out/sweep"), seed=42)
```

See `examples/generate_dataset.py` and `src/icecream_simulator/scenario_runner.py`.

## Interpreting results

1. Confirm `mass_balance_closed` before drawing conclusions.
2. Treat outputs as **model proxies**, not plant guarantees (see `docs/SIMULATOR_CAPABILITIES_AND_SAMPLE_RUN.md`).
3. When comparing scenarios, fix `seed` / inputs and change one lever at a time.
4. For wastewater tuning, read `docs/WATER_TREATMENT_CAVITATION.md`.

## Tests

After code changes to the simulator:

```bash
pytest
```

## Do not

- Invent numeric results without running when the repo is available.
- Edit `industrial_physics.py` for one-off what-if runs — pass parameters to `run_full_cycle` instead.
- Assume cleaning-phase outputs exist when `--no-cleaning` was used.
