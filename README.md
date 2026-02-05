# Ice Cream Production & Waste-to-Plastic Simulator

A modular Python simulation framework for integrated **ice cream manufacturing** and **waste-to-plastic conversion**. Designed for pluggable Physics-Informed Machine Learning (PIML) and external process models.

## Process Flow

```
Raw Materials (Milk, Cream, Sugar, Stabilizers, Water)
        │
        ▼
┌─────────────────────────────────────┐
│  Mixing (PIML)                      │  ← Pluggable: predict viscosity, thermal properties
│  Shear rate, ingredient ratios      │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│  Wastewater Filtration              │  ← Pluggable: separation efficiency model
│  Product vs. waste stream           │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│  Bioplastic Conversion              │  ← Pluggable: PHA/PLA from organics
│  Sugar/organics → bioplastics       │
└─────────────────────────────────────┘
```

## Features

- **Modular ABC interfaces** for Mixing, Filtration, and Bioplastic Conversion models
- **Mass and energy balance** tracking across the pipeline
- **Pydantic schemas** for type-safe input/output
- **JSON-ready reports** via `SimulationReport.model_dump()`

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
    PlaceholderFiltrationModel,
    PlaceholderBioplasticModel,
)

runner = SimulationRunner(
    mixing_model=PlaceholderMixingModel(),
    filtration_model=PlaceholderFiltrationModel(product_recovery=0.85),
    bioplastic_model=PlaceholderBioplasticModel(conversion_yield=0.40),
)

raw_materials = RawMaterials(milk=100, cream=30, sugar=25, stabilizers=2, water=43)
report = runner.run(raw_materials)

# JSON-ready output
print(report.model_dump())
```

## Pluggable Models

### Custom PIML Mixing Model

Implement `MixingModelBase` and pass it to `SimulationRunner`:

```python
from icecream_simulator.models import MixingModelBase
from icecream_simulator.schemas import MixingInput, MixingOutput

class MyPIMLMixingModel(MixingModelBase):
    def predict(self, input_data: MixingInput) -> MixingOutput:
        # Your PIML / neural network / surrogate model here
        return MixingOutput(
            viscosity=...,
            thermal_conductivity=...,
            specific_heat=...,
            product_mass=input_data.raw_materials.total_mass,
            energy_consumed=...,
        )

runner = SimulationRunner(
    mixing_model=MyPIMLMixingModel(),
    filtration_model=PlaceholderFiltrationModel(),
    bioplastic_model=PlaceholderBioplasticModel(),
)
```

See `examples/custom_piml_mixing.py` for a full example with a Carreau-Yasuda-style shear-thinning model.

### Custom Filtration Model

Implement `FiltrationModelBase`:

```python
from icecream_simulator.models import FiltrationModelBase
from icecream_simulator.schemas import FiltrationInput, FiltrationOutput

class MyFiltrationModel(FiltrationModelBase):
    def predict(self, input_data: FiltrationInput) -> FiltrationOutput:
        # Your membrane/filtration model here
        return FiltrationOutput(...)
```

### Custom Bioplastic Model

Implement `BioplasticConversionModelBase`:

```python
from icecream_simulator.models import BioplasticConversionModelBase
from icecream_simulator.schemas import BioplasticConversionInput, BioplasticConversionOutput

class MyBioplasticModel(BioplasticConversionModelBase):
    def predict(self, input_data: BioplasticConversionInput) -> BioplasticConversionOutput:
        # Your conversion kinetics model here
        return BioplasticConversionOutput(...)
```

## Project Structure

```
src/icecream_simulator/
├── __init__.py
├── schemas.py          # Pydantic data models
├── runner.py           # SimulationRunner
└── models/
    ├── base.py         # ABC interfaces (MixingModelBase, etc.)
    └── placeholders.py # Default implementations

examples/
├── basic_usage.py
└── custom_piml_mixing.py
```

## Running Examples

```bash
python examples/basic_usage.py
python examples/custom_piml_mixing.py
```

## License

MIT
