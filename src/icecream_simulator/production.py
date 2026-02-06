"""
ProductionEngine and WasteLogic — Mass Balance + Operational Loss model.

Ice cream production is a closed-loop system. Wastewater is an external
volume added during cleaning/flushing; it carries away product loss (shrinkage).
"""

from __future__ import annotations

from icecream_simulator.schemas import (
    RawMaterials,
    IceCreamRecipe,
    ShrinkageResult,
    Wastewater,
    State,
)


class ProductionEngine:
    """
    Mass balance model for ice cream production.

    Total_Output_Volume = (Raw_Material_Input + Air_Overrun) - System_Shrinkage
    Ice cream does not "produce" wastewater; wastewater is from cleaning/flushing.
    """

    # Approximate mix density (kg/L) for volume calculations
    MIX_DENSITY_KG_L: float = 1.05

    def __init__(
        self,
        adhesion_loss_fraction: float = 0.005,
    ):
        """
        Args:
            adhesion_loss_fraction: Fraction of mix lost to tank/pipe adhesion (e.g. 0.5%).
        """
        self.adhesion_loss_fraction = adhesion_loss_fraction

    def calculate_shrinkage(
        self,
        mix_volume_L: float,
        tank_surface_area_m2: float = 10.0,
        interface_flush_L: float = 5.0,
    ) -> ShrinkageResult:
        """
        Compute operational loss: adhesion + interface flush.

        Adhesion Loss: % of mix stuck to tank/pipe interior (scaled by surface area).
        Interface Flush: Start-of-run loss — first X liters discarded due to
        water/sanitizer dilution.

        Args:
            mix_volume_L: Total mix volume (L) before air overrun.
            tank_surface_area_m2: Interior surface area of tanks/pipes (m²).
            interface_flush_L: Liters discarded at start-of-run.

        Returns:
            ShrinkageResult with adhesion and interface flush (kg and L).
        """
        # Adhesion: 0.5% of volume, scaled by surface area (reference 10 m²)
        adhesion_scale = tank_surface_area_m2 / 10.0
        adhesion_loss_L = mix_volume_L * self.adhesion_loss_fraction * adhesion_scale
        adhesion_loss_kg = adhesion_loss_L * self.MIX_DENSITY_KG_L

        # Interface flush: fixed volume discarded
        interface_flush_L_clamped = min(interface_flush_L, mix_volume_L)
        interface_flush_kg = interface_flush_L_clamped * self.MIX_DENSITY_KG_L

        total_kg = adhesion_loss_kg + interface_flush_kg
        total_L = adhesion_loss_L + interface_flush_L_clamped

        return ShrinkageResult(
            adhesion_loss_kg=adhesion_loss_kg,
            interface_flush_kg=interface_flush_kg,
            adhesion_loss_L=adhesion_loss_L,
            interface_flush_L=interface_flush_L_clamped,
            total_system_shrinkage_kg=total_kg,
            total_system_shrinkage_L=total_L,
        )

    def run_mass_balance(
        self,
        raw_materials: RawMaterials,
        air_overrun: float = 0.5,
        tank_surface_area_m2: float = 10.0,
        interface_flush_L: float = 5.0,
    ) -> tuple[float, float, ShrinkageResult]:
        """
        Compute ice cream output and shrinkage.

        Total_Output_Volume = (Raw_Material_Input + Air_Overrun) - System_Shrinkage
        Output mass = Raw_Material_Mass - Shrinkage_Mass (air adds volume, not mass).

        Args:
            raw_materials: Input raw materials (kg).
            air_overrun: Volume overrun fraction (0.5 = 50%).
            tank_surface_area_m2: Tank/pipe surface area (m²).
            interface_flush_L: Start-of-run discard (L).

        Returns:
            (ice_cream_output_kg, ice_cream_output_volume_L, shrinkage_result)
        """
        mix_mass_kg = raw_materials.total_mass
        mix_volume_L = mix_mass_kg / self.MIX_DENSITY_KG_L

        shrinkage = self.calculate_shrinkage(
            mix_volume_L=mix_volume_L,
            tank_surface_area_m2=tank_surface_area_m2,
            interface_flush_L=interface_flush_L,
        )

        # Output mass: raw materials minus what we lost
        ice_cream_output_kg = mix_mass_kg - shrinkage.total_system_shrinkage_kg
        ice_cream_output_kg = max(0.0, ice_cream_output_kg)

        # Output volume: mix volume * (1 + overrun) minus shrinkage volume
        mix_volume_with_air_L = mix_volume_L * (1.0 + air_overrun)
        ice_cream_output_volume_L = mix_volume_with_air_L - shrinkage.total_system_shrinkage_L
        ice_cream_output_volume_L = max(0.0, ice_cream_output_volume_L)

        return ice_cream_output_kg, ice_cream_output_volume_L, shrinkage


class WasteLogic:
    """
    Generates wastewater from cleaning water + system shrinkage.

    BOD and FOG are derived from the Fat_Content and Sugar_Content of the
    IceCreamRecipe (product loss). If Product_Loss increases, Wastewater_BOD
    increases proportionally.
    """

    # BOD contribution: ~1.5 kg O2 per kg sugar, ~2.5 kg O2 per kg fat (typical ranges)
    BOD_SUGAR_KG_O2_PER_KG: float = 1.2
    BOD_FAT_KG_O2_PER_KG: float = 2.0

    def generate_wastewater(
        self,
        cleaning_water_inflow_L: float,
        system_shrinkage_kg: float,
        recipe: IceCreamRecipe,
        mix_density_kg_L: float = 1.05,
    ) -> Wastewater:
        """
        Generate wastewater during CLEANING or IDLE→RUNNING (interface flush).

        Wastewater volume = Cleaning_Water_Inflow + System_Shrinkage (as volume).
        BOD and FOG are calculated from product loss (shrinkage) composition.

        Args:
            cleaning_water_inflow_L: Water used for cleaning/flushing (L).
            system_shrinkage_kg: Product lost (adhesion + interface flush) (kg).
            recipe: Ice cream recipe for fat/sugar fractions.
            mix_density_kg_L: Mix density (kg/L).

        Returns:
            Wastewater with volume, BOD, FOG, organic_content.
        """
        shrinkage_volume_L = system_shrinkage_kg / mix_density_kg_L
        volume_L = cleaning_water_inflow_L + shrinkage_volume_L

        product_loss_kg = system_shrinkage_kg
        organic_content_kg = product_loss_kg  # Whole mix is organic

        if volume_L <= 0:
            return Wastewater(
                volume_L=0.0,
                product_loss_kg=0.0,
                organic_content_kg=0.0,
                bod_mg_L=0.0,
                fog_mg_L=0.0,
                bod_load_kg=0.0,
                cleaning_water_L=cleaning_water_inflow_L,
            )

        # BOD: proportional to sugar + fat in product loss
        sugar_kg = product_loss_kg * recipe.sugar_content
        fat_kg = product_loss_kg * recipe.fat_content
        bod_load_kg = (
            sugar_kg * self.BOD_SUGAR_KG_O2_PER_KG + fat_kg * self.BOD_FAT_KG_O2_PER_KG
        )
        bod_mg_L = (bod_load_kg * 1e6) / volume_L if volume_L > 0 else 0.0

        # FOG: proportional to fat in product loss
        fog_load_kg = fat_kg
        fog_mg_L = (fog_load_kg * 1e6) / volume_L if volume_L > 0 else 0.0

        return Wastewater(
            volume_L=volume_L,
            product_loss_kg=product_loss_kg,
            organic_content_kg=organic_content_kg,
            bod_mg_L=bod_mg_L,
            fog_mg_L=fog_mg_L,
            bod_load_kg=bod_load_kg,
            cleaning_water_L=cleaning_water_inflow_L,
        )

    def should_generate_wastewater(
        self,
        current_state: State,
        previous_state: State | None,
    ) -> bool:
        """
        Wastewater is generated only during CLEANING or IDLE→RUNNING transition.

        Args:
            current_state: Current production state.
            previous_state: State before transition (None if first step).

        Returns:
            True if wastewater should be generated.
        """
        if current_state == State.CLEANING:
            return True
        if previous_state == State.IDLE and current_state == State.RUNNING:
            return True  # Interface flush at start-of-run
        return False
