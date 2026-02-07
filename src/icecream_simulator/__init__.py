"""
Ice Cream Production and Waste-to-Plastic Conversion Simulator.

A modular simulation framework for integrated ice cream manufacturing
and bioplastic conversion from wastewater streams.

Single pipeline: Mixing → CIP → Filtration → Bioconversion (MaterialBatch flow).
"""

from icecream_simulator.schemas import RawMaterials, MassBalanceState, StageResult
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
    MaterialBatchCycleReport,
)
from icecream_simulator.run_full_cycle import run_full_cycle, print_report
from icecream_simulator.mixer import MixerModelBase, DefaultMixerModel
from icecream_simulator.bioconversion import BioconversionModelBase, DefaultBioconversionModel

__version__ = "0.3.0"

__all__ = [
    "RawMaterials",
    "MassBalanceState",
    "StageResult",
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
    "MaterialBatchCycleReport",
    "run_full_cycle",
    "print_report",
    "MixerModelBase",
    "DefaultMixerModel",
    "BioconversionModelBase",
    "DefaultBioconversionModel",
]
