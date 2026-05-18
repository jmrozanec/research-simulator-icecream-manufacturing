"""
Ice Cream Production and Waste-to-Plastic Conversion Simulator.

A modular simulation framework for integrated ice cream manufacturing
and bioplastic conversion from wastewater streams.

Single pipeline: Industrial chain → CIP → pre-filtration → hydrodynamic cavitation → nanofiltration → bioconversion (MaterialBatch flow).
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
from icecream_simulator.prefiltration import PrefiltrationConfig, run_prefiltration
from icecream_simulator.cavitation import CavitationConfig, run_hydrodynamic_cavitation
from icecream_simulator.literature_recipes import (
    LiteratureRecipePreset,
    LITERATURE_PRESETS,
    get_preset,
    list_preset_ids,
    run_literature_suite,
)
from icecream_simulator.mixer import MixerModelBase, DefaultMixerModel
from icecream_simulator.bioconversion import BioconversionModelBase, DefaultBioconversionModel
from icecream_simulator.crystallization_parameters import (
    CrystallizationParameters,
    DEFAULT_CRYSTALLIZATION_PARAMETERS,
    load_crystallization_parameters,
    load_crystallization_parameters_from_json,
    load_crystallization_parameters_from_yaml,
)
from icecream_simulator.provenance import Provenance, SourceKind
from icecream_simulator.sensors import (
    AccuracyKind,
    SensorSpec,
    SensorReading,
    sample_reading,
)
from icecream_simulator.events import Severity, Event, EventBus
from icecream_simulator.plant_profile import (
    PlantProfile,
    AlarmThresholds,
    StageSensors,
    build_midsize_continuous_dairy,
    load_default_profile,
    default_profile_path,
)
from icecream_simulator.instrumentation import apply_instrumentation
from icecream_simulator.energy_accounting import (
    EnergyBalance,
    aggregate_energy_report,
)
from icecream_simulator.scenario_runner import (
    Distribution,
    Uniform,
    LogUniform,
    Triangular,
    Constant,
    Discrete,
    Categorical,
    RawMaterialsDist,
    ProcessParamsDist,
    ScenarioSpec,
    SweepResult,
    run_sweep,
    diverse_industrial_spec,
)

__version__ = "0.4.0"

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
    "PrefiltrationConfig",
    "run_prefiltration",
    "CavitationConfig",
    "run_hydrodynamic_cavitation",
    "MixerModelBase",
    "DefaultMixerModel",
    "BioconversionModelBase",
    "DefaultBioconversionModel",
    "LiteratureRecipePreset",
    "LITERATURE_PRESETS",
    "get_preset",
    "list_preset_ids",
    "run_literature_suite",
    "CrystallizationParameters",
    "DEFAULT_CRYSTALLIZATION_PARAMETERS",
    "load_crystallization_parameters",
    "load_crystallization_parameters_from_json",
    "load_crystallization_parameters_from_yaml",
    # Phase-1 / Phase-2 enhancements
    "Provenance",
    "SourceKind",
    "AccuracyKind",
    "SensorSpec",
    "SensorReading",
    "sample_reading",
    "Severity",
    "Event",
    "EventBus",
    "PlantProfile",
    "AlarmThresholds",
    "StageSensors",
    "build_midsize_continuous_dairy",
    "load_default_profile",
    "default_profile_path",
    "apply_instrumentation",
    "EnergyBalance",
    "aggregate_energy_report",
    "Distribution",
    "Uniform",
    "LogUniform",
    "Triangular",
    "Constant",
    "Discrete",
    "Categorical",
    "RawMaterialsDist",
    "ProcessParamsDist",
    "ScenarioSpec",
    "SweepResult",
    "run_sweep",
    "diverse_industrial_spec",
]
