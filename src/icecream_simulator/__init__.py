"""
Ice Cream Production and Waste-to-Plastic Conversion Simulator.

A modular simulation framework for integrated ice cream manufacturing
and bioplastic conversion from wastewater streams.

Mass balance model: Ice cream is a closed-loop system. Wastewater comes
from cleaning water + operational loss (shrinkage).
"""

from icecream_simulator.schemas import (
    RawMaterials,
    MixingInput,
    MixingOutput,
    BioplasticConversionInput,
    BioplasticConversionOutput,
    SimulationReport,
    MassBalanceState,
    State,
    IceCreamRecipe,
    ShrinkageResult,
    Wastewater,
)
from icecream_simulator.models import (
    MixingModelBase,
    BioplasticConversionModelBase,
    PlaceholderMixingModel,
    PlaceholderBioplasticModel,
)
from icecream_simulator.production import ProductionEngine, WasteLogic
from icecream_simulator.runner import SimulationRunner

__version__ = "0.2.0"

__all__ = [
    "RawMaterials",
    "MixingInput",
    "MixingOutput",
    "BioplasticConversionInput",
    "BioplasticConversionOutput",
    "SimulationReport",
    "MassBalanceState",
    "State",
    "IceCreamRecipe",
    "ShrinkageResult",
    "Wastewater",
    "MixingModelBase",
    "BioplasticConversionModelBase",
    "PlaceholderMixingModel",
    "PlaceholderBioplasticModel",
    "ProductionEngine",
    "WasteLogic",
    "SimulationRunner",
]
