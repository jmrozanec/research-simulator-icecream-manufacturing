# Ice Cream Production & Waste-to-Plastic Simulator

A modular Python simulation framework for integrated **ice cream manufacturing** and **waste-to-plastic conversion**. Uses a **Mass Balance + Operational Loss** model: ice cream is a closed-loop system; wastewater comes from cleaning water and product loss (shrinkage).

## Process Flow

```
Raw Materials (Milk, Cream, Sugar, Stabilizers, Water)
        │
        ▼
┌─────────────────────────────────────┐
│  Mixing (PIML)                      │  ← Pluggable: viscosity, thermal properties
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│  Production (ProductionEngine)      │  Mass balance: Output = (Input + Air) - Shrinkage
│  Adhesion loss + Interface flush    │  CalculateShrinkage()
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│  Wastewater (WasteLogic)            │  Cleaning water + product loss → BOD, FOG
│  State: CLEANING or IDLE→RUNNING    │  GenerateWastewater()
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│  Bioplastic Conversion              │  PHA/PLA from wastewater organics
└─────────────────────────────────────┘
```

## Mass Balance Logic

- **Total_Output_Volume** = (Raw_Material_Input + Air_Overrun) - System_Shrinkage
- **Shrinkage** = Adhesion loss (tank/pipe) + Interface flush (start-of-run discard)
- **Wastewater** = Cleaning_Water_Inflow + System_Shrinkage
- **BOD/FOG** scale with product loss (recipe fat/sugar content)

If Product_Loss ↑ → Wastewater_BOD ↑, IceCream_Output ↓

## Features

- **ProductionEngine**: `CalculateShrinkage()`, mass balance
- **WasteLogic**: `GenerateWastewater()` with BOD/FOG from recipe
- **State machine**: IDLE, RUNNING, CLEANING
- **Pluggable PIML** mixing and bioplastic models
- **Pydantic schemas** for type safety

## Installation

```bash
pip install -e .
# or
pip install -r requirements.txt
```

## Quick Start

```python
from icecream_simulator import (
    RawMaterials,
    SimulationRunner,
    PlaceholderMixingModel,
    PlaceholderBioplasticModel,
)

runner = SimulationRunner(
    mixing_model=PlaceholderMixingModel(),
    bioplastic_model=PlaceholderBioplasticModel(conversion_yield=0.40),
)

raw_materials = RawMaterials(milk=100, cream=30, sugar=25, stabilizers=2, water=43)
report = runner.run(
    raw_materials,
    interface_flush_L=5.0,
    cleaning_water_inflow_L=80.0,
)
print(report.total_product_mass, report.metadata["bod_mg_L"])
```

## ProductionEngine & WasteLogic

```python
from icecream_simulator import ProductionEngine, WasteLogic, IceCreamRecipe
from icecream_simulator.schemas import RawMaterials

engine = ProductionEngine(adhesion_loss_fraction=0.005)
shrinkage = engine.calculate_shrinkage(
    mix_volume_L=200.0,
    tank_surface_area_m2=10.0,
    interface_flush_L=5.0,
)

recipe = IceCreamRecipe.from_raw_materials(raw_materials)
waste = WasteLogic().generate_wastewater(
    cleaning_water_inflow_L=80.0,
    system_shrinkage_kg=shrinkage.total_system_shrinkage_kg,
    recipe=recipe,
)
# waste.bod_mg_L, waste.fog_mg_L, waste.organic_content_kg
```

## MaterialBatch Pipeline (Full Cycle)

A second architecture centers on a **MaterialBatch** object that flows through every stage. Use it for rheology, residue, CIP, filtration (Darcy/fouling), and sugar-to-plastic conversion in one run.

- **batch_models.py** — `MaterialBatch` (mass, T, μ, composition, COD/BOD), `WastewaterStream`, `RetentateStream`, `FilterState`, etc.
- **mixer.py** — Power Law viscosity, power \(P = K \cdot \mu \cdot N^2 \cdot D^3\), residue = f(μ, surface area) → `ProductBatch` + `TankResidue`
- **cip.py** — CIP wash efficiency → `WastewaterStream` (TSS, dissolved sugars)
- **filtration.py** — Darcy resistance, filter saturation; permeate + retentate; maintenance flag when saturation > 90%
- **bioconversion.py** — \(Mass_{PHA} = Mass_{Sugar} \times Yield_{Coefficient}\) (e.g. Ralstonia eutropha logic)
- **run_full_cycle.py** — One full cycle and efficiency/plastic yield report

Run the full cycle:

```bash
python -m icecream_simulator.run_full_cycle
# or
uv run python examples/run_material_batch_cycle.py
```

```python
from icecream_simulator import RawMaterials, run_full_cycle, print_report

report = run_full_cycle(
    raw_materials=RawMaterials(milk=100, cream=30, sugar=25, stabilizers=2, water=43),
    tank_surface_area_m2=10.0,
    water_volume_L=80.0,
    bioplastic_yield_coefficient=0.4,
)
print_report(report)
```

Custom viscosity, power, residue, wash, Darcy, or bioconversion models can be plugged in where marked with **PLUG-IN** in the source (e.g. `mixer.viscosity_power_law`, `mixer.residue_mass_kg`, `bioconversion.run_bioconversion`).

## Project Structure

```
src/icecream_simulator/
├── __init__.py
├── schemas.py          # RawMaterials, IceCreamRecipe, Wastewater, ShrinkageResult, State
├── production.py       # ProductionEngine, WasteLogic
├── runner.py           # SimulationRunner
├── batch_models.py     # MaterialBatch, WastewaterStream, RetentateStream, FilterState, etc.
├── mixer.py            # Rheology, power P=K·μ·N²·D³, residue → ProductBatch + TankResidue
├── cip.py              # CIP → WastewaterStream
├── filtration.py       # Darcy/fouling, permeate + retentate, filter health
├── bioconversion.py    # Sugar → PHA (yield coefficient)
├── run_full_cycle.py   # Full cycle + report
└── models/
    ├── base.py         # MixingModelBase, BioplasticConversionModelBase
    └── placeholders.py # PlaceholderMixingModel, PlaceholderBioplasticModel
```

## Running Examples

```bash
python examples/basic_usage.py
python examples/custom_piml_mixing.py
python examples/sample_run_verbose.py   # Detailed data flow trace
```

## Monitoring Dashboard

```bash
pip install streamlit
streamlit run examples/dashboard.py
```

## License

Apache License 2.0
