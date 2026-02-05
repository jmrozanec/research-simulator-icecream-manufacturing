"""
Example: Plugging in a Custom PIML Mixing Model

This example demonstrates how to implement and use a custom Physics-Informed
Machine Learning (PIML) mixing model in place of the default placeholder.

In production, you would replace the simple formulas below with:
- A trained neural network (e.g., PyTorch, TensorFlow)
- A surrogate model from CFD simulations
- A PINN (Physics-Informed Neural Network) for viscosity prediction
- An external service/API call to a deployed model
"""

import json
from pathlib import Path

# Add src to path for standalone execution
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from icecream_simulator.schemas import RawMaterials, MixingInput, MixingOutput
from icecream_simulator.models import (
    MixingModelBase,
    PlaceholderFiltrationModel,
    PlaceholderBioplasticModel,
    PlaceholderMixingModel,
)
from icecream_simulator.runner import SimulationRunner


# ---------------------------------------------------------------------------
# Custom PIML Mixing Model (Example Implementation)
# ---------------------------------------------------------------------------


class CustomPIMLMixingModel(MixingModelBase):
    """
    Example custom PIML mixing model.

    This model uses a Carreau-Yasuda-like shear-thinning equation combined
    with ingredient-based corrections. In a real deployment, you would:
    - Load a trained model (e.g., model.load_state_dict(...))
    - Call model.forward(...) instead of these empirical formulas
    - Optionally incorporate PDE residuals for physics consistency
    """

    def __init__(self, n_infty: float = 0.001, lambda_carreau: float = 1.0):
        """
        Args:
            n_infty: Infinite-shear viscosity (Pa·s).
            lambda_carreau: Characteristic time constant (s).
        """
        self.n_infty = n_infty
        self.lambda_carreau = lambda_carreau

    @property
    def model_name(self) -> str:
        return "CustomPIMLMixingModel"

    def predict(self, input_data: MixingInput) -> MixingOutput:
        rm = input_data.raw_materials
        total_mass = rm.total_mass
        shear_rate = input_data.shear_rate

        # Zero-shear viscosity: ingredient-based (placeholder for PIML prediction)
        # In production: zero_shear = self.neural_net(ingredient_ratios, T)
        sugar_ratio = rm.sugar / max(total_mass, 1e-9)
        stabilizer_ratio = rm.stabilizers / max(total_mass, 1e-9)
        n_0 = 0.5 + 2.0 * sugar_ratio + 1.5 * stabilizer_ratio  # Pa·s

        # Carreau-Yasuda shear-thinning (physics-informed structure)
        # η(γ̇) = η_∞ + (η_0 - η_∞) * [1 + (λγ̇)^a]^((n-1)/a)
        a = 2.0  # Yasuda exponent
        n = 0.4  # Power-law index
        reduced_shear = (self.lambda_carreau * shear_rate) ** a
        viscosity = self.n_infty + (n_0 - self.n_infty) * (
            (1 + reduced_shear) ** ((n - 1) / a)
        )

        # Thermal properties: mixture rules (placeholder for PIML)
        water_frac = rm.water / max(total_mass, 1e-9)
        fat_frac = (rm.milk * 0.04 + rm.cream * 0.36) / max(total_mass, 1e-9)
        thermal_conductivity = 0.6 * water_frac + 0.2 * fat_frac + 0.3  # W/(m·K)
        specific_heat = 4000 * water_frac + 2000 * fat_frac + 2500  # J/(kg·K)

        # Mixing energy (work input)
        energy_consumed = viscosity * shear_rate * input_data.mixing_time * total_mass

        return MixingOutput(
            viscosity=viscosity,
            thermal_conductivity=thermal_conductivity,
            specific_heat=specific_heat,
            product_mass=total_mass,
            energy_consumed=energy_consumed,
        )


# ---------------------------------------------------------------------------
# Usage: Run simulation with custom PIML model
# ---------------------------------------------------------------------------


def main() -> None:
    # 1. Instantiate models (plug in custom PIML for mixing)
    mixing_model = CustomPIMLMixingModel(n_infty=0.001, lambda_carreau=2.0)
    # Or use placeholder: mixing_model = PlaceholderMixingModel()
    filtration_model = PlaceholderFiltrationModel(product_recovery=0.88)
    bioplastic_model = PlaceholderBioplasticModel(conversion_yield=0.45)

    # 2. Create runner with pluggable models
    runner = SimulationRunner(
        mixing_model=mixing_model,
        filtration_model=filtration_model,
        bioplastic_model=bioplastic_model,
    )

    # 3. Define raw materials
    raw_materials = RawMaterials(
        milk=50.0,
        cream=20.0,
        sugar=15.0,
        stabilizers=1.0,
        water=14.0,
    )

    # 4. Run simulation
    report = runner.run(
        raw_materials=raw_materials,
        shear_rate=150.0,
        temperature=278.15,  # 5 °C
        mixing_time=360.0,
        solids_fraction=0.10,
        pathway="PHA",
    )

    # 5. Output JSON-ready report
    report_dict = report.model_dump()
    print(json.dumps(report_dict, indent=2, default=str))

    # Optional: save to file
    # with open("simulation_report.json", "w") as f:
    #     json.dump(report_dict, f, indent=2, default=str)


if __name__ == "__main__":
    main()
