"""
Ice cream production + washwater valorization (simplified closed-form pipeline).

See docs/SIMPLIFIED_PIPELINE_REPORT.md for the equation set and assumptions.
"""

from icecream_simulator.domain import (
    BioplasticOutput,
    FilterState,
    LiteratureRecipePreset,
    MassBalanceState,
    MaterialBatchCycleReport,
    PermeateStream,
    RawMaterials,
    RetentateStream,
    StageResult,
    TankResidue,
    WastewaterStream,
)
from icecream_simulator.pipeline import (
    LITERATURE_PRESETS,
    get_preset,
    list_preset_ids,
    print_report,
    run_full_cycle,
    run_literature_suite,
)

__version__ = "1.0.0"

__all__ = [
    "RawMaterials",
    "MassBalanceState",
    "StageResult",
    "TankResidue",
    "WastewaterStream",
    "RetentateStream",
    "PermeateStream",
    "FilterState",
    "BioplasticOutput",
    "MaterialBatchCycleReport",
    "LiteratureRecipePreset",
    "LITERATURE_PRESETS",
    "run_full_cycle",
    "print_report",
    "get_preset",
    "list_preset_ids",
    "run_literature_suite",
]
