# Ice Cream Production & Waste-to-Plastic Simulator

This repository is a Python simulation of **industrial ice cream manufacture** wired together with a **wastewater and bioplastic** path: what leaves the line as wash water can be traced through **coarse pre-filtration (TSS)**, **hydrodynamic cavitation** (organic load and fragmentation proxies), **membrane filtration**, and into a simple sugar-to-PHA conversion. The idea is not to pretend every plant matches one recipe, but to give you a **consistent mass and energy story** from raw mix to packaged product, with enough physics hooks that you can align the model to papers, pilot data, or your own measurements.

Mixing and aeration are kept separate on purpose: **blending** happens hot in the preparation tank (no air), and **overrun** is applied in the continuous freezer, which matches how the literature and most plant descriptions order the steps.

### Where the process description comes from

The step order (mix → pasteurise → homogenise → cool → age → freeze with air → harden) is the one you see in reviews and textbooks. A convenient single reference for the equipment narrative is:

> Harfoush, A., Fan, Z., Goddik, L., & Haapala, K. R. (2024). A review of ice cream manufacturing process and system improvement strategies. *Manufacturing Letters*, *41*, 170–181. [https://doi.org/10.1016/j.mfglet.2024.09.021](https://doi.org/10.1016/j.mfglet.2024.09.021)

**Mapping (review Fig. 2 → this codebase):**

| Typical industrial step (review) | Simulator stage |
|-----------------------------------|-----------------|
| 1. Ingredient mixing | `preparation_mix` |
| 2. Pasteurization | `pasteurization` (+ hold / lethality in `industrial_physics`) |
| 3. Homogenization | `homogenization` |
| 4. Aging (after cooling) | `cooling_phe` then `ageing_vat` |
| 5. Flavor/color (often before freezer) | `flavor_inclusions` |
| 6. Continuous / dynamic freezing (SSHE, air) | `freezer` |
| 7. Inclusions & packing (plant-dependent) | `packaging` (after `hardening` in our chain) |
| 8. Hardening | `hardening` |

A PDF of that review is in `papers/icecream-01.pdf`. Additional PDFs in the same folder back **literature recipe presets** (Giudici, Konstantas, and reference entries for Cook–Hartel and scheduling); see `literature_recipes.py` and the [capabilities doc](docs/SIMULATOR_CAPABILITIES_AND_SAMPLE_RUN.md).

## Process flow

```
Raw Materials
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  INDUSTRIAL CHAIN                                                         │
│  1. Preparation mix (hot high-shear; blending only, no air)              │
│  2. Pasteurization (PHE ~80°C)  3. Homogenization (pressure)             │
│  4. Cooling (PHE 80→30→5°C)  5. Ageing vat (jacketed, stirrer)           │
│  6. Freezer (overrun = aeration here)  7. Hardening                      │
│  Optional: storage (distribution freezer, recrystallization)               │
│  Residues: prep tank + ageing vat + interface flush → combined for CIP     │
└─────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  CIP                                 │  Residue + water → WastewaterStream (TSS, BOD, FOG)
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Pre-filtration                      │  Coarse TSS removal (screen / bag) before HC
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Hydrodynamic cavitation             │  COD/BOD + fragmentation proxy; bioavailability → bioconv.
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Filtration (nanofiltration)         │  Darcy/fouling → Permeate + Retentate (sugar concentrate)
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Bioconversion                       │  Retentate sugar → PHA (Pluggable: BioconversionModelBase)
└─────────────────────────────────────┘
```

## Features

- **Industrial chain:** Preparation through packaging, with optional **post-hardening storage** to mimic distribution temperatures and extra ice ripening.
- **Research-grade ice path:** Separate **hydrocolloid** and **emulsifier** masses, **wall vs bulk** crystal populations, **Gompertz and Avrami** frozen-fraction models, barrel and storage **recrystallization**, and **Kelvin** reporting—see `industrial_physics.py` and the [capabilities doc](docs/SIMULATOR_CAPABILITIES_AND_SAMPLE_RUN.md).
- **Calibration without forked code:** All of those coefficients can be driven from one **`CrystallizationParameters`** object, or from **JSON / YAML** on disk, so you can fit a product line or archive settings next to lab data (details below).
- **Literature presets:** Named batches tied to papers and tables (`literature_recipes.py`); run them all with `python run.py --literature-suite`.
- **MaterialBatch** (mass, temperature, viscosity, composition) through the chain; **CIP**, **pre-filtration**, **hydrodynamic cavitation**, **filtration**, and **bioconversion** with pluggable bioconversion; **typed report** and mass balance checks. See [Wastewater cavitation train](docs/WATER_TREATMENT_CAVITATION.md) for **peer-reviewed references (Gogate & Pandit, DOIs)**, tuning knobs, and optional PDFs under [`papers/`](papers/README.md).

**Longer read:** [Capabilities and sample run](docs/SIMULATOR_CAPABILITIES_AND_SAMPLE_RUN.md) — process scope, per-stage sample outputs, presets, and ice calibration. **Wastewater train tuning:** [Wastewater cavitation and pre-filtration](docs/WATER_TREATMENT_CAVITATION.md).

### Calibrating ice and texture (JSON / YAML)

The built-in numbers are a reasonable starting point, not a claim about your plant. For work that needs to line up with microscopy, laser diffraction, or sensory data, use **`CrystallizationParameters`**:

- **In code:** `run_full_cycle(crystallization_parameters=...)` with an instance built in Python or validated from a dict.
- **From a file:** `load_crystallization_parameters_from_json("path.json")`, or `load_crystallization_parameters("path.yaml")` after `pip install ".[config]"` (adds PyYAML).

Start from `examples/crystallization_parameters_example.json`: copy it, set a descriptive `name`, and edit only the coefficients you are fitting. Omitted fields keep the library defaults. Each run stores the full parameter snapshot under `report["inputs"]["crystallization_parameters"]` so results stay traceable.

## Installation

```bash
pip install -e .
# optional: YAML loaders for calibration files
pip install -e ".[config]"
```

## Quick start

```python
from icecream_simulator import RawMaterials, run_full_cycle, print_report

report = run_full_cycle(
    raw_materials=RawMaterials(
        milk=100, cream=30, sugar=25, stabilizers=1.65, emulsifiers_kg=0.35, water=43
    ),
    tank_surface_area_m2=10.0,
    water_volume_L=80.0,
    bioplastic_yield_coefficient=0.4,
    air_overrun=0.5,
    interface_flush_L=5.0,
)
print_report(report)
# report["cip"] — CIP effluent only; report["prefiltration"], report["hydrodynamic_cavitation"],
# report["wastewater_to_nanofiltration"] — membrane feed after HC; report["filtration"], report["bioconversion"], etc.
```

## Extensibility

- **Bioplastic:** Implement `BioconversionModelBase` and pass it to `run_full_cycle`.
- **Wastewater:** Call `run_prefiltration` / `run_hydrodynamic_cavitation` with custom `PrefiltrationConfig` / `CavitationConfig`, or fork those modules; defaults are wired in `run_full_cycle` when `include_cleaning_phase=True`.
- **Mixing rheology:** Subclass `MixerModelBase` or extend `run_preparation_mix` / `mixer.run_mixer`.
- **Ice and texture:** Adjust `CrystallizationParameters` or load from file; no need to edit `industrial_physics` unless you add new physics.

```python
from icecream_simulator import run_full_cycle, DefaultBioconversionModel

report = run_full_cycle(
    bioconversion_model=DefaultBioconversionModel(yield_coefficient=0.35),
)
```

## Project structure

```
src/icecream_simulator/
├── __init__.py
├── schemas.py                    # RawMaterials, MassBalanceState, StageResult
├── crystallization_parameters.py  # CrystallizationParameters, JSON/YAML loaders
├── batch_models.py               # MaterialBatch, streams, reports
├── mixer.py
├── cip.py
├── prefiltration.py              # Coarse TSS removal before cavitation / membrane
├── cavitation.py               # Hydrodynamic cavitation (COD/BOD, fragmentation proxy)
├── filtration.py
├── bioconversion.py
├── run_full_cycle.py
├── industrial_chain.py
├── industrial_physics.py
├── literature_recipes.py
└── models/
    └── __init__.py

papers/
└── README.md                     # Optional local PDFs; cavitation DOIs & suggested filenames
```

Docs: `docs/SIMULATOR_CAPABILITIES_AND_SAMPLE_RUN.md` (capabilities and sample tables), `docs/WATER_TREATMENT_CAVITATION.md` (wastewater stage parameters and cavitation bibliography).

## Run the simulator

```bash
python run.py
python run.py --preset GIUDICI_2021_INDUSTRIAL
python run.py --literature-suite --no-cleaning
uv run python run.py
python -m icecream_simulator.run_full_cycle
```

## Running examples

```bash
python examples/basic_usage.py
python examples/custom_piml_mixing.py
python examples/sample_run_verbose.py
python examples/run_material_batch_cycle.py
python examples/literature_presets.py
```

## Monitoring dashboard

```bash
pip install streamlit
streamlit run examples/dashboard.py
```

## License

Apache License 2.0
