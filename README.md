# Ice Cream Production & Waste-to-Plastic Simulator

A modular Python simulation framework for integrated **ice cream manufacturing** and **waste-to-plastic conversion**. One pipeline: **MaterialBatch** flows through Mixer → CIP → Filtration → Bioplastic. Mass balance includes operational loss (residue + interface flush); wastewater comes from cleaning and feeds sugar valorization to PHA.

## Process flow

```
Raw Materials (Milk, Cream, Sugar, Stabilizers, Water)
        │
        ▼
┌─────────────────────────────────────┐
│  Mixer                               │  Rheology, P = K·μ·N²·D³, residue → Product + TankResidue
│  (Pluggable: MixerModelBase)         │  Interface flush applied as additional loss
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│  CIP                                 │  Residue + water → WastewaterStream (TSS, BOD, FOG)
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│  Filtration                          │  Darcy/fouling → Permeate + Retentate (sugar concentrate)
│  Filter health, maintenance flag     │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│  Bioconversion                       │  Retentate sugar → PHA (Pluggable: BioconversionModelBase)
└─────────────────────────────────────┘
```

## Features

- **MaterialBatch** object (mass, T, μ, composition, COD/BOD) through all stages
- **Mixer:** Power Law viscosity, power \(P = K \cdot \mu \cdot N^2 \cdot D^3\), residue = f(μ, surface area); thermal outputs; air overrun; interface flush
- **CIP:** Wash efficiency, wastewater with TSS, BOD, FOG, dissolved sugar
- **Filtration:** Darcy-style fouling, permeate/retentate, filter saturation & maintenance
- **Bioconversion:** Mass_PHA = Mass_Sugar × yield coefficient (e.g. Ralstonia eutropha–style)
- **Pluggable** mixing and bioplastic models (`MixerModelBase`, `BioconversionModelBase`)
- **Optional cleaning phase** (skip CIP/filtration/bioconversion for production-only runs)
- **Typed report** (`MaterialBatchCycleReport`) and `mass_balance_closed`

For a **capabilities overview and sample run** (parameters + stage-by-stage outcomes) for researchers developing physical/chemical sub-models, see **[docs/SIMULATOR_CAPABILITIES_AND_SAMPLE_RUN.md](docs/SIMULATOR_CAPABILITIES_AND_SAMPLE_RUN.md)**.

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
# report["mixer"]["product_to_freezer_kg"], report["bioconversion"]["bioplastic_mass_kg"], etc.
```

## Extensibility

Plug in your own mixing or bioplastic conversion by implementing `MixerModelBase` or `BioconversionModelBase`:

```python
from icecream_simulator import run_full_cycle, MixerModelBase, DefaultBioconversionModel

class MyMixerModel(MixerModelBase):
    def run(self, inputs): ...  # return (ProductBatch, TankResidue, power_W)

report = run_full_cycle(
    mixing_model=MyMixerModel(),
    bioconversion_model=DefaultBioconversionModel(yield_coefficient=0.35),
)
```

Custom viscosity, power, residue, wash, Darcy, or bioconversion can also be changed where marked **PLUG-IN** in the source (e.g. `mixer.viscosity_power_law`, `bioconversion.run_bioconversion`).

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
├── run_full_cycle.py   # Full cycle + report
└── models/             # (Reserved for future shared abstractions)
    └── __init__.py
```

## Running examples

```bash
python -m icecream_simulator.run_full_cycle
python examples/basic_usage.py
python examples/custom_piml_mixing.py   # Custom MixerModelBase
python examples/sample_run_verbose.py  # Verbose data flow
python examples/run_material_batch_cycle.py
```

## Monitoring dashboard

```bash
pip install streamlit
streamlit run examples/dashboard.py
```

Stage-by-stage view: Mixer → CIP → Filtration → Bioplastic, with summary and mass balance.

## License

Apache License 2.0
