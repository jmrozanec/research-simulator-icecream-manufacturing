"""
Abstract Base Classes for pluggable simulation models.

All external models (PIML mixing, filtration, bioplastic conversion) must
implement these interfaces to be used by the SimulationRunner.
"""

from abc import ABC, abstractmethod

from icecream_simulator.schemas import (
    MixingInput,
    MixingOutput,
    FiltrationInput,
    FiltrationOutput,
    BioplasticConversionInput,
    BioplasticConversionOutput,
)


class MixingModelBase(ABC):
    """
    Abstract base class for Physics-Informed Machine Learning (PIML) mixing models.

    Predicts viscosity and thermal properties based on shear rates and ingredient ratios.
    Implement this interface to plug in custom PIML models (e.g., neural PDE solvers,
    surrogate models trained on CFD data, etc.).
    """

    @property
    def model_name(self) -> str:
        """Human-readable name for logging and reporting."""
        return self.__class__.__name__

    @abstractmethod
    def predict(self, input_data: MixingInput) -> MixingOutput:
        """
        Predict viscosity and thermal properties from mixing conditions.

        Args:
            input_data: Raw materials, shear rate, temperature, mixing time.

        Returns:
            MixingOutput with viscosity, thermal conductivity, specific heat,
            product mass, and energy consumed.
        """
        ...


class FiltrationModelBase(ABC):
    """
    Abstract base class for wastewater filtration efficiency models.

    Models the separation of product from waste stream. Implement this
    interface to plug in custom filtration models (e.g., membrane fouling
    models, empirical separation curves, etc.).
    """

    @property
    def model_name(self) -> str:
        """Human-readable name for logging and reporting."""
        return self.__class__.__name__

    @abstractmethod
    def predict(self, input_data: FiltrationInput) -> FiltrationOutput:
        """
        Predict separation efficiency and stream masses.

        Args:
            input_data: Feed mass, solids content, temperature.

        Returns:
            FiltrationOutput with product mass, wastewater mass,
            solids in wastewater, and energy consumed.
        """
        ...


class BioplasticConversionModelBase(ABC):
    """
    Abstract base class for bioplastic conversion models.

    Models chemical/microbial conversion of sugar/organics in wastewater
    into PHA, PLA, or similar bioplastics. Implement this interface to
    plug in custom conversion models.
    """

    @property
    def model_name(self) -> str:
        """Human-readable name for logging and reporting."""
        return self.__class__.__name__

    @abstractmethod
    def predict(self, input_data: BioplasticConversionInput) -> BioplasticConversionOutput:
        """
        Predict bioplastic yield from wastewater organics.

        Args:
            input_data: Wastewater mass, organic content, pathway type.

        Returns:
            BioplasticConversionOutput with bioplastic mass, residue,
            conversion yield, and energy consumed.
        """
        ...
