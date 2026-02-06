"""
Module 4: Bioconversion — Sugar-to-Plastic (e.g. Ralstonia eutropha / PHA).

Inputs: Retentate (concentrated sugar stream).
Simulation: Mass_PHA = Mass_Sugar × Yield_Coefficient (e.g. 0.4 g plastic per 1 g sugar).
Output: Total mass of bioplastic produced.
"""

from __future__ import annotations

from icecream_simulator.batch_models import RetentateStream, BioplasticOutput


# Typical yield for PHA from sugars (e.g. Ralstonia eutropha): ~0.3–0.45 g PHA / g sugar
DEFAULT_YIELD_COEFFICIENT = 0.4  # g plastic per g sugar


def run_bioconversion(
    retentate: RetentateStream,
    yield_coefficient: float = DEFAULT_YIELD_COEFFICIENT,
) -> BioplasticOutput:
    """
    Convert sugar in retentate to bioplastic (e.g. PHA).
    Formula: Mass_PHA = Mass_Sugar × Yield_Coefficient.

    PLUG-IN: Replace with your own bioconversion model (e.g. Monod
    kinetics, Ralstonia eutropha growth model, or ML yield predictor).
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
