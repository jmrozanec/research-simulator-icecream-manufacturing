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
from icecream_simulator.batch_models import (
    MaterialBatch,
    ProductBatch,
    TankResidue,
    WastewaterStream,
    RetentateStream,
    PermeateStream,
    FilterState,
    BioplasticOutput,
    Composition,
    ContaminantLoad,
)
from icecream_simulator.run_full_cycle import run_full_cycle, print_report
from icecream_simulator.mixer import MixerModelBase, DefaultMixerModel
from icecream_simulator.bioconversion import BioconversionModelBase, DefaultBioconversionModel

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
    # MaterialBatch pipeline (full cycle: Mixing → CIP → Filtration → Bioconversion)
    "MaterialBatch",
    "ProductBatch",
    "TankResidue",
    "WastewaterStream",
    "RetentateStream",
    "PermeateStream",
    "FilterState",
    "BioplasticOutput",
    "Composition",
    "ContaminantLoad",
    "run_full_cycle",
    "print_report",
    "MixerModelBase",
    "DefaultMixerModel",
    "BioconversionModelBase",
    "DefaultBioconversionModel",
]
