"""
Module 4: Bioconversion — Sugar-to-Plastic (e.g. Ralstonia eutropha / PHA).

Inputs: Retentate (concentrated sugar stream).
Simulation: Mass_PHA = Mass_Sugar × Yield_Coefficient (e.g. 0.4 g plastic per 1 g sugar).
Output: Total mass of bioplastic produced.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from icecream_simulator.batch_models import RetentateStream, BioplasticOutput


# Typical yield for PHA from sugars (e.g. Ralstonia eutropha): ~0.3–0.45 g PHA / g sugar
DEFAULT_YIELD_COEFFICIENT = 0.4  # g plastic per g sugar


# ---------------------------------------------------------------------------
# Pluggable bioconversion model (extensibility)
# ---------------------------------------------------------------------------


class BioconversionModelBase(ABC):
    """
    Abstract base for sugar-to-plastic stage in the MaterialBatch pipeline.
    Provide your own implementation for custom kinetics or ML yield models.
    """

    @property
    def model_name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def run(self, retentate: RetentateStream, **kwargs: object) -> BioplasticOutput:
        """Convert retentate sugar to bioplastic. Return BioplasticOutput."""
        ...


def run_bioconversion(
    retentate: RetentateStream,
    yield_coefficient: float = DEFAULT_YIELD_COEFFICIENT,
) -> BioplasticOutput:
    """
    Convert sugar in retentate to bioplastic (e.g. PHA).

    Mass_PHA = Mass_Sugar × Yield_Coefficient. Use ``BioconversionModelBase``
    subclasses for Monod kinetics or other pathways.
    """
    sugar_kg = retentate.sugar_mass_kg
    # Yield in kg PHA per kg sugar
    pha_kg = sugar_kg * yield_coefficient
    return BioplasticOutput(
        mass_kg=pha_kg,
        sugar_consumed_kg=sugar_kg,
        yield_coefficient=yield_coefficient,
        metadata={"pathway": "PHA", "retentate_mass_kg": retentate.mass_kg},
    )


class DefaultBioconversionModel(BioconversionModelBase):
    """Default implementation: Mass_PHA = Mass_Sugar × yield_coefficient."""

    def __init__(self, yield_coefficient: float = DEFAULT_YIELD_COEFFICIENT):
        self.yield_coefficient = yield_coefficient

    def run(self, retentate: RetentateStream, **kwargs: object) -> BioplasticOutput:
        bio = float(kwargs.get("bioavailability_factor", 1.0))
        # Cavitation can increase labile carbon; cap so yield stays in a plausible band
        eff = self.yield_coefficient * min(1.35, max(0.85, bio))
        return run_bioconversion(retentate, yield_coefficient=eff)
