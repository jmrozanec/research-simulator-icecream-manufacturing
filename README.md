# Ice Cream Production & Waste-to-Plastic Simulator

A modular Python simulation framework for integrated **ice cream manufacturing** and **waste-to-plastic conversion**. One pipeline: **MaterialBatch** flows through the **industrial chain** (7 steps), then CIP → Filtration → Bioplastic. Mass balance includes operational loss (residue + interface flush). Wastewater comes from CIP that cleans the preparation tank (mixer at the start), the ageing vat, and the interface flush; it then feeds sugar valorization to PHA.

**Mixing vs aeration:** Blending of ingredients happens only in **step 1 (preparation mix)**, at hot temperature so sugar and stabilizers dissolve and fat is liquid. **No air** is added there. **Aeration (overrun)** is done later in **step 6 (continuous freezer)**, where air is incorporated into the cold mix. So: mix first (liquid) → pasteurize → homogenize → cool → age → freeze + aerate → harden.

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
│  Residues: prep tank + ageing vat + interface flush → combined for CIP    │
└─────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  CIP                                 │  Residue + water → WastewaterStream (TSS, BOD, FOG)
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Filtration                          │  Darcy/fouling → Permeate + Retentate (sugar concentrate)
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Bioconversion                       │  Retentate sugar → PHA (Pluggable: BioconversionModelBase)
└─────────────────────────────────────┘
```

## Features

- **Industrial chain only:** Preparation mix → Pasteurization → Homogenization → Cooling PHE → Ageing vat → Freezer (overrun) → Hardening. **Wastewater** comes from CIP: cleaning the **preparation tank** (mixer at the start), the **ageing vat**, and the **interface flush** (start-of-run discard). Each stage is simulated (heat duties, viscosity vs pressure, residue vs stirrer, etc.).
- **MaterialBatch** (mass, T, μ, composition) through all stages
- **CIP:** Wash efficiency, wastewater with TSS, BOD, FOG, dissolved sugar
- **Filtration:** Darcy-style fouling, permeate/retentate, filter saturation & maintenance
- **Bioconversion:** Mass_PHA = Mass_Sugar × yield coefficient; **pluggable** via `BioconversionModelBase`
- **Optional cleaning phase** (skip CIP/filtration/bioconversion for production-only runs)
- **Typed report** (`MaterialBatchCycleReport`), `report["industrial_chain"]["stages_detail"]` per-stage outputs, and `mass_balance_closed`

**Docs:** [Capabilities and sample run](docs/SIMULATOR_CAPABILITIES_AND_SAMPLE_RUN.md) · [Industrial flow and extensions](docs/INDUSTRIAL_FLOW_AND_EXTENSIONS.md).

## Installation

```bash
pip install -e .
# or
pip install -r requirements.txt
```

## Quick start

```python
from icecream_simulator import RawMaterials, run_full_cycle, print_report

report = run_full_cycle(
    raw_materials=RawMaterials(milk=100, cream=30, sugar=25, stabilizers=2, water=43),
    tank_surface_area_m2=10.0,
    water_volume_L=80.0,
    bioplastic_yield_coefficient=0.4,
    air_overrun=0.5,
    interface_flush_L=5.0,
)
print_report(report)
# report["mixer"]["product_to_freezer_kg"], report["industrial_chain"]["stages_detail"], report["bioconversion"]["bioplastic_mass_kg"], etc.
```

## Extensibility

Plug in your own bioplastic conversion by implementing `BioconversionModelBase`. Custom preparation rheology (e.g. PIML viscosity) can be added by extending `industrial_chain.run_preparation_mix` (which uses `mixer.run_mixer` internally).

```python
from icecream_simulator import run_full_cycle, DefaultBioconversionModel

report = run_full_cycle(
    bioconversion_model=DefaultBioconversionModel(yield_coefficient=0.35),
)
```

Other plug-in points are marked **PLUG-IN** in the source (e.g. homogenization viscosity factor, ageing residue, `bioconversion.run_bioconversion`).

## Project structure

```
src/icecream_simulator/
├── __init__.py
├── schemas.py          # RawMaterials, MassBalanceState, StageResult
├── batch_models.py     # MaterialBatch, WastewaterStream, RetentateStream, FilterState, etc.
├── mixer.py            # Rheology, P=K·μ·N²·D³, residue; MixerModelBase, DefaultMixerModel
├── cip.py              # CIP → WastewaterStream
├── filtration.py       # Darcy/fouling, permeate + retentate, filter health
├── bioconversion.py    # Sugar → PHA; BioconversionModelBase, DefaultBioconversionModel
├── run_full_cycle.py   # Full cycle (industrial chain → CIP → Filtration → Bioplastic) + report
├── industrial_chain.py # 7-step chain: preparation (mixing) → pasteurization → homogenization → cooling → ageing → freezer (aeration) → hardening
└── models/             # (Reserved for future shared abstractions)
    └── __init__.py
```

## Run the simulator

From the project root (default parameters, report to stdout):

```bash
python run.py
# or
uv run python run.py
# or
python -m icecream_simulator.run_full_cycle
```

## Running examples

```bash
python examples/basic_usage.py
python examples/custom_piml_mixing.py   # Custom bioconversion
python examples/sample_run_verbose.py  # Verbose data flow
python examples/run_material_batch_cycle.py
```

## Monitoring dashboard

```bash
pip install streamlit
streamlit run examples/dashboard.py
```

Stage-by-stage view: Industrial chain → CIP → Filtration → Bioplastic, with summary and mass balance.

## License

Apache License 2.0
