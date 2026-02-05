"""
Placeholder implementations of the pluggable models.

These provide default behavior for testing and serve as reference
implementations for users creating custom models.
"""

from icecream_simulator.models.base import (
    MixingModelBase,
    FiltrationModelBase,
    BioplasticConversionModelBase,
)
from icecream_simulator.schemas import (
    MixingInput,
    MixingOutput,
    FiltrationInput,
    FiltrationOutput,
    BioplasticConversionInput,
    BioplasticConversionOutput,
)


class PlaceholderMixingModel(MixingModelBase):
    """
    Placeholder PIML mixing model for development and testing.

    Uses simple empirical correlations as stand-ins for a real
    Physics-Informed Machine Learning model.
    """

    def predict(self, input_data: MixingInput) -> MixingOutput:
        rm = input_data.raw_materials
        total_mass = rm.total_mass

        # Empirical viscosity: higher sugar/stabilizers -> higher viscosity
        # Shear-thinning: viscosity decreases with shear rate
        sugar_effect = 1.0 + 0.5 * (rm.sugar / max(total_mass, 1e-6))
        stabilizer_effect = 1.0 + 0.3 * (rm.stabilizers / max(total_mass, 1e-6))
        shear_effect = max(0.1, 1.0 / (1.0 + input_data.shear_rate * 0.01))
        viscosity = 0.5 * sugar_effect * stabilizer_effect * shear_effect

        # Thermal properties: water-dominated
        water_fraction = rm.water / max(total_mass, 1e-6)
        thermal_conductivity = 0.4 + 0.2 * water_fraction  # W/(m·K)
        specific_heat = 3500 + 500 * water_fraction  # J/(kg·K)

        # Energy: proportional to viscosity and mixing time
        energy_consumed = viscosity * input_data.shear_rate * input_data.mixing_time * total_mass * 0.1

        return MixingOutput(
            viscosity=viscosity,
            thermal_conductivity=thermal_conductivity,
            specific_heat=specific_heat,
            product_mass=total_mass,
            energy_consumed=energy_consumed,
        )


class PlaceholderFiltrationModel(FiltrationModelBase):
    """
    Placeholder filtration model for development and testing.

    Assumes a fixed recovery fraction and simple mass split.
    """

    def __init__(self, product_recovery: float = 0.85):
        """
        Args:
            product_recovery: Fraction of feed recovered as product (0-1).
        """
        self.product_recovery = product_recovery

    def predict(self, input_data: FiltrationInput) -> FiltrationOutput:
        product_mass = input_data.feed_mass * self.product_recovery
        wastewater_mass = input_data.feed_mass - product_mass
        solids_in_wastewater = wastewater_mass * input_data.solids_content

        # Energy: simple pump/filter model
        energy_consumed = wastewater_mass * 1e4  # J per kg

        return FiltrationOutput(
            product_mass=product_mass,
            wastewater_mass=wastewater_mass,
            solids_in_wastewater=solids_in_wastewater,
            energy_consumed=energy_consumed,
        )


class PlaceholderBioplasticModel(BioplasticConversionModelBase):
    """
    Placeholder bioplastic conversion model for development and testing.

    Assumes a fixed conversion yield from organics to PHA.
    """

    def __init__(self, conversion_yield: float = 0.4):
        """
        Args:
            conversion_yield: Fraction of organics converted to bioplastic (0-1).
        """
        self.conversion_yield = conversion_yield

    def predict(self, input_data: BioplasticConversionInput) -> BioplasticConversionOutput:
        bioplastic_mass = input_data.organic_content * self.conversion_yield
        residue_mass = input_data.wastewater_mass - bioplastic_mass

        yield_frac = (
            bioplastic_mass / input_data.organic_content
            if input_data.organic_content > 0
            else 0.0
        )

        # Energy: fermentation/chemical process
        energy_consumed = bioplastic_mass * 5e6  # J per kg PHA

        return BioplasticConversionOutput(
            bioplastic_mass=bioplastic_mass,
            residue_mass=max(0, residue_mass),
            conversion_yield=yield_frac,
            energy_consumed=energy_consumed,
        )
