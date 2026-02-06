"""
Simulation Runner - orchestrates the pipeline with Mass Balance + Operational Loss.

Uses ProductionEngine and WasteLogic instead of filtration. Ice cream is a
closed-loop system; wastewater comes from cleaning + shrinkage.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from icecream_simulator.schemas import (
    RawMaterials,
    MixingInput,
    MixingOutput,
    BioplasticConversionInput,
    BioplasticConversionOutput,
    MassBalanceState,
    SimulationReport,
    StageResult,
    IceCreamRecipe,
    State,
)
from icecream_simulator.models import MixingModelBase, BioplasticConversionModelBase
from icecream_simulator.production import ProductionEngine, WasteLogic


class StageCallback(Protocol):
    """Protocol for stage completion callbacks (for monitoring/dashboards)."""

    def __call__(self, stage_name: str, stage_result: StageResult, cumulative: dict) -> None:
        ...


class SimulationRunner:
    """
    Executes the ice cream production and waste-to-plastic pipeline.

    Mass balance: IceCream_Output = (Raw_Material + Air_Overrun) - System_Shrinkage.
    Wastewater is generated only during CLEANING or IDLE→RUNNING.
    """

    def __init__(
        self,
        mixing_model: MixingModelBase,
        bioplastic_model: BioplasticConversionModelBase,
        production_engine: ProductionEngine | None = None,
        waste_logic: WasteLogic | None = None,
    ):
        """
        Args:
            mixing_model: PIML or surrogate model for mixing process.
            bioplastic_model: Model for organic-to-bioplastic conversion.
            production_engine: Mass balance + shrinkage. Defaults to ProductionEngine().
            waste_logic: Wastewater generation. Defaults to WasteLogic().
        """
        self.mixing_model = mixing_model
        self.bioplastic_model = bioplastic_model
        self.production_engine = production_engine or ProductionEngine()
        self.waste_logic = waste_logic or WasteLogic()

    def run(
        self,
        raw_materials: RawMaterials,
        shear_rate: float = 100.0,
        temperature: float = 273.15 + 5,
        mixing_time: float = 300.0,
        air_overrun: float = 0.5,
        tank_surface_area_m2: float = 10.0,
        interface_flush_L: float = 5.0,
        cleaning_water_inflow_L: float = 100.0,
        include_cleaning_phase: bool = True,
        on_stage_complete: Callable[[str, StageResult, dict], None] | None = None,
        **kwargs: object,
    ) -> SimulationReport:
        """
        Execute the full simulation pipeline.

        Flow: IDLE → RUNNING (mixing, production, interface flush) → CLEANING (wastewater) → bioplastic.

        Args:
            raw_materials: Input raw materials (milk, cream, sugar, stabilizers, water).
            shear_rate: Shear rate for mixing (1/s).
            temperature: Mixing temperature (K).
            mixing_time: Mixing duration (s).
            air_overrun: Air overrun fraction (0.5 = 50%).
            tank_surface_area_m2: Tank/pipe surface area for adhesion (m²).
            interface_flush_L: Start-of-run discard (L).
            cleaning_water_inflow_L: Water used during cleaning (L).
            include_cleaning_phase: If True, simulate CLEANING and generate wastewater.
            on_stage_complete: Optional callback for monitoring/dashboards.
            **kwargs: Additional parameters.

        Returns:
            SimulationReport with mass balance, stage results, totals.
        """
        stage_results: list[StageResult] = []
        total_energy_consumed = 0.0
        previous_state: State | None = None
        current_state = State.IDLE

        recipe = IceCreamRecipe.from_raw_materials(raw_materials)

        # --- Stage 1: Mixing (PIML) ---
        mixing_input = MixingInput(
            raw_materials=raw_materials,
            shear_rate=shear_rate,
            temperature=temperature,
            mixing_time=mixing_time,
        )
        mixing_output = self.mixing_model.predict(mixing_input)
        current_state = State.RUNNING

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
        mixing_result = StageResult(
            stage_name="mixing",
            mass_balance=mass_balance_mixing,
            outputs=mixing_output.model_dump(),
            model_used=self.mixing_model.model_name,
        )
        stage_results.append(mixing_result)
        total_energy_consumed += mixing_output.energy_consumed
        if on_stage_complete:
            on_stage_complete(
                "mixing",
                mixing_result,
                {"product_mass": mixing_output.product_mass, "energy_consumed": total_energy_consumed},
            )

        # --- Stage 2: Production (Mass Balance + Shrinkage) ---
        ice_cream_kg, ice_cream_volume_L, shrinkage = self.production_engine.run_mass_balance(
            raw_materials=raw_materials,
            air_overrun=air_overrun,
            tank_surface_area_m2=tank_surface_area_m2,
            interface_flush_L=interface_flush_L,
        )
        total_product_mass = ice_cream_kg

        mass_balance_production = MassBalanceState(
            stage="production",
            mass_in=raw_materials.total_mass,
            mass_out=ice_cream_kg + shrinkage.total_system_shrinkage_kg,
            energy_consumed=0.0,
            mass_product=ice_cream_kg,
            mass_waste=shrinkage.total_system_shrinkage_kg,
            metadata={
                "shrinkage_kg": shrinkage.total_system_shrinkage_kg,
                "adhesion_loss_kg": shrinkage.adhesion_loss_kg,
                "interface_flush_kg": shrinkage.interface_flush_kg,
                "ice_cream_volume_L": ice_cream_volume_L,
            },
        )
        production_result = StageResult(
            stage_name="production",
            mass_balance=mass_balance_production,
            outputs=shrinkage.model_dump(),
            model_used="ProductionEngine",
        )
        stage_results.append(production_result)
        if on_stage_complete:
            on_stage_complete(
                "production",
                production_result,
                {
                    "product_mass": total_product_mass,
                    "shrinkage_kg": shrinkage.total_system_shrinkage_kg,
                    "energy_consumed": total_energy_consumed,
                },
            )

        # --- Stage 3: Wastewater (CLEANING or IDLE→RUNNING) ---
        # Wastewater = Cleaning_Water + System_Shrinkage (product loss).
        # Generated during CLEANING (full) or IDLE→RUNNING (interface flush only, no cleaning water).
        cleaning_L = cleaning_water_inflow_L if include_cleaning_phase else 0.0
        wastewater = self.waste_logic.generate_wastewater(
            cleaning_water_inflow_L=cleaning_L,
            system_shrinkage_kg=shrinkage.total_system_shrinkage_kg,
            recipe=recipe,
        )

        # Wastewater mass = cleaning water + product loss (shrinkage)
        wastewater_mass_kg = (
            wastewater.cleaning_water_L * 1.0 + wastewater.product_loss_kg
        )
        total_wastewater_mass = wastewater_mass_kg

        mass_balance_wastewater = MassBalanceState(
            stage="wastewater",
            mass_in=wastewater.cleaning_water_L * 1.0 + shrinkage.total_system_shrinkage_kg,
            mass_out=wastewater_mass_kg,
            energy_consumed=0.0,
            mass_product=0.0,
            mass_waste=wastewater_mass_kg,
            metadata={
                "bod_mg_L": wastewater.bod_mg_L,
                "fog_mg_L": wastewater.fog_mg_L,
                "organic_content_kg": wastewater.organic_content_kg,
            },
        )
        wastewater_result = StageResult(
            stage_name="wastewater",
            mass_balance=mass_balance_wastewater,
            outputs=wastewater.model_dump(),
            model_used="WasteLogic",
        )
        stage_results.append(wastewater_result)
        if on_stage_complete:
            on_stage_complete(
                "wastewater",
                wastewater_result,
                {
                    "product_mass": total_product_mass,
                    "wastewater_mass": total_wastewater_mass,
                    "energy_consumed": total_energy_consumed,
                },
            )

        # --- Stage 4: Bioplastic Conversion ---
        bioplastic_input = BioplasticConversionInput(
            wastewater_mass=wastewater_mass_kg,
            organic_content=wastewater.organic_content_kg,
            pathway=kwargs.get("pathway", "PHA"),
        )
        bioplastic_output = self.bioplastic_model.predict(bioplastic_input)
        total_bioplastic_mass = bioplastic_output.bioplastic_mass

        mass_balance_bioplastic = MassBalanceState(
            stage="bioplastic_conversion",
            mass_in=wastewater_mass_kg,
            mass_out=bioplastic_output.bioplastic_mass + bioplastic_output.residue_mass,
            energy_consumed=bioplastic_output.energy_consumed,
            mass_product=bioplastic_output.bioplastic_mass,
            mass_waste=bioplastic_output.residue_mass,
            metadata={"conversion_yield": bioplastic_output.conversion_yield},
        )
        bioplastic_result = StageResult(
            stage_name="bioplastic_conversion",
            mass_balance=mass_balance_bioplastic,
            outputs=bioplastic_output.model_dump(),
            model_used=self.bioplastic_model.model_name,
        )
        stage_results.append(bioplastic_result)
        total_energy_consumed += bioplastic_output.energy_consumed
        if on_stage_complete:
            on_stage_complete(
                "bioplastic_conversion",
                bioplastic_result,
                {
                    "product_mass": total_product_mass,
                    "wastewater_mass": total_wastewater_mass,
                    "bioplastic_mass": total_bioplastic_mass,
                    "energy_consumed": total_energy_consumed,
                },
            )

        # --- Mass Balance Closure ---
        mass_in_total = raw_materials.total_mass + (cleaning_water_inflow_L * 1.0 if include_cleaning_phase else 0.0)
        mass_out_total = (
            total_product_mass
            + bioplastic_output.residue_mass
            + total_bioplastic_mass
            + (cleaning_water_inflow_L * 1.0 if include_cleaning_phase else 0.0)
        )
        # Simplified: product + bioplastic residue + bioplastic ≈ raw_materials + cleaning_water
        mass_balance_closed = abs(
            raw_materials.total_mass
            - (total_product_mass + shrinkage.total_system_shrinkage_kg)
        ) < 1e-6

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
                "shrinkage_kg": shrinkage.total_system_shrinkage_kg,
                "bod_mg_L": wastewater.bod_mg_L,
                "fog_mg_L": wastewater.fog_mg_L,
            },
        )
