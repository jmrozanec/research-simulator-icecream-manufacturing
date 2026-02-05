"""
Simulation Runner - orchestrates the pipeline and produces JSON-ready reports.
"""

from __future__ import annotations

from icecream_simulator.schemas import (
    RawMaterials,
    MixingInput,
    MixingOutput,
    FiltrationInput,
    FiltrationOutput,
    BioplasticConversionInput,
    BioplasticConversionOutput,
    MassBalanceState,
    SimulationReport,
    StageResult,
)
from icecream_simulator.models import (
    MixingModelBase,
    FiltrationModelBase,
    BioplasticConversionModelBase,
)


class SimulationRunner:
    """
    Executes the ice cream production and waste-to-plastic pipeline in sequence.

    Accepts pluggable models for mixing (PIML), filtration, and bioplastic conversion.
    Tracks mass and energy balance across all stages and produces a comprehensive
    JSON-ready report.
    """

    def __init__(
        self,
        mixing_model: MixingModelBase,
        filtration_model: FiltrationModelBase,
        bioplastic_model: BioplasticConversionModelBase,
    ):
        """
        Args:
            mixing_model: PIML or surrogate model for mixing process.
            filtration_model: Model for wastewater/product separation.
            bioplastic_model: Model for organic-to-bioplastic conversion.
        """
        self.mixing_model = mixing_model
        self.filtration_model = filtration_model
        self.bioplastic_model = bioplastic_model

    def run(
        self,
        raw_materials: RawMaterials,
        shear_rate: float = 100.0,
        temperature: float = 273.15 + 5,
        mixing_time: float = 300.0,
        **kwargs: object,
    ) -> SimulationReport:
        """
        Execute the full simulation pipeline.

        Args:
            raw_materials: Input raw materials (milk, cream, sugar, stabilizers, water).
            shear_rate: Shear rate for mixing (1/s).
            temperature: Mixing temperature (K).
            mixing_time: Mixing duration (s).
            **kwargs: Additional parameters passed to models (e.g., filtration settings).

        Returns:
            SimulationReport with mass balance, stage results, and totals.
        """
        stage_results: list[StageResult] = []
        total_product_mass = 0.0
        total_wastewater_mass = 0.0
        total_bioplastic_mass = 0.0
        total_energy_consumed = 0.0

        # --- Stage 1: Mixing (PIML) ---
        mixing_input = MixingInput(
            raw_materials=raw_materials,
            shear_rate=shear_rate,
            temperature=temperature,
            mixing_time=mixing_time,
        )
        mixing_output = self.mixing_model.predict(mixing_input)

        mass_balance_mixing = MassBalanceState(
            stage="mixing",
            mass_in=raw_materials.total_mass,
            mass_out=mixing_output.product_mass,
            energy_consumed=mixing_output.energy_consumed,
            mass_product=mixing_output.product_mass,
            mass_waste=0.0,
            metadata={
                "viscosity": mixing_output.viscosity,
                "thermal_conductivity": mixing_output.thermal_conductivity,
                "specific_heat": mixing_output.specific_heat,
            },
        )
        stage_results.append(
            StageResult(
                stage_name="mixing",
                mass_balance=mass_balance_mixing,
                outputs=mixing_output.model_dump(),
                model_used=self.mixing_model.model_name,
            )
        )
        total_energy_consumed += mixing_output.energy_consumed

        mixed_product_mass = mixing_output.product_mass

        # --- Stage 2: Wastewater Filtration ---
        # Assume 10% solids in mixed product (simplified)
        solids_fraction = kwargs.get("solids_fraction", 0.10)
        filtration_input = FiltrationInput(
            feed_mass=mixed_product_mass,
            solids_content=solids_fraction,
            temperature=temperature,
        )
        filtration_output = self.filtration_model.predict(filtration_input)

        mass_balance_filtration = MassBalanceState(
            stage="filtration",
            mass_in=mixed_product_mass,
            mass_out=filtration_output.product_mass + filtration_output.wastewater_mass,
            energy_consumed=filtration_output.energy_consumed,
            mass_product=filtration_output.product_mass,
            mass_waste=filtration_output.wastewater_mass,
            metadata={
                "solids_in_wastewater": filtration_output.solids_in_wastewater,
            },
        )
        stage_results.append(
            StageResult(
                stage_name="filtration",
                mass_balance=mass_balance_filtration,
                outputs=filtration_output.model_dump(),
                model_used=self.filtration_model.model_name,
            )
        )
        total_product_mass = filtration_output.product_mass
        total_wastewater_mass = filtration_output.wastewater_mass
        total_energy_consumed += filtration_output.energy_consumed

        # --- Stage 3: Bioplastic Conversion ---
        bioplastic_input = BioplasticConversionInput(
            wastewater_mass=filtration_output.wastewater_mass,
            organic_content=filtration_output.solids_in_wastewater,
            pathway=kwargs.get("pathway", "PHA"),
        )
        bioplastic_output = self.bioplastic_model.predict(bioplastic_input)

        mass_balance_bioplastic = MassBalanceState(
            stage="bioplastic_conversion",
            mass_in=filtration_output.wastewater_mass,
            mass_out=bioplastic_output.bioplastic_mass + bioplastic_output.residue_mass,
            energy_consumed=bioplastic_output.energy_consumed,
            mass_product=bioplastic_output.bioplastic_mass,
            mass_waste=bioplastic_output.residue_mass,
            metadata={
                "conversion_yield": bioplastic_output.conversion_yield,
            },
        )
        stage_results.append(
            StageResult(
                stage_name="bioplastic_conversion",
                mass_balance=mass_balance_bioplastic,
                outputs=bioplastic_output.model_dump(),
                model_used=self.bioplastic_model.model_name,
            )
        )
        total_bioplastic_mass = bioplastic_output.bioplastic_mass
        total_energy_consumed += bioplastic_output.energy_consumed

        # --- Mass Balance Closure Check ---
        mass_in_total = raw_materials.total_mass
        mass_out_total = (
            total_product_mass
            + bioplastic_output.residue_mass
            + total_bioplastic_mass
        )
        mass_balance_closed = abs(mass_in_total - mass_out_total) < 1e-6

        return SimulationReport(
            raw_materials=raw_materials,
            stage_results=stage_results,
            total_product_mass=total_product_mass,
            total_wastewater_mass=total_wastewater_mass,
            total_bioplastic_mass=total_bioplastic_mass,
            total_energy_consumed=total_energy_consumed,
            mass_balance_closed=mass_balance_closed,
            metadata={
                "shear_rate": shear_rate,
                "temperature": temperature,
                "mixing_time": mixing_time,
            },
        )
