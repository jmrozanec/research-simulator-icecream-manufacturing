"""
Example: Plugging in a Custom Mixing Model

Demonstrates how to implement and use a custom mixing model (e.g. PIML,
Carreau-Yasuda rheology) in place of the default Power Law mixer.

In production, you would replace the formulas below with:
- A trained neural network (e.g. PyTorch, TensorFlow)
- A surrogate from CFD simulations
- A PINN for viscosity prediction
"""

import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from icecream_simulator import RawMaterials, run_full_cycle, DefaultBioconversionModel
from icecream_simulator.mixer import MixerModelBase, MixerInput
from icecream_simulator.batch_models import ProductBatch, TankResidue, Composition


# ---------------------------------------------------------------------------
# Custom Mixing Model (example: Carreau-Yasuda–style rheology)
# ---------------------------------------------------------------------------


class CustomMixingModel(MixerModelBase):
    """
    Example custom mixer: Carreau-Yasuda–style shear-thinning with
    ingredient-based zero-shear viscosity. Returns (ProductBatch, TankResidue, power_W).
    """

    def __init__(self, n_infty: float = 0.001, lambda_carreau: float = 1.0):
        self.n_infty = n_infty
        self.lambda_carreau = lambda_carreau

    def run(self, inputs: MixerInput) -> tuple[ProductBatch, TankResidue, float]:
        rm = inputs.raw_materials
        total_mass = rm.total_mass
        if total_mass <= 0:
            comp = Composition(fat=0, sugar=0, water=0, solids=0)
            return (
                ProductBatch(mass_kg=0, temperature_K=inputs.initial_temperature_K, viscosity_Pa_s=0, composition=comp),
                TankResidue(mass_kg=0, composition=comp, viscosity_Pa_s=0),
                0.0,
            )
        # Composition from raw materials
        comp = Composition(
            fat=(rm.milk * 0.04 + rm.cream * 0.36) / total_mass,
            sugar=rm.sugar / total_mass,
            water=rm.water / total_mass,
            solids=(rm.milk * 0.09 + rm.stabilizers) / total_mass,
        )
        T = inputs.initial_temperature_K
        N_rps = inputs.rpm / 60.0
        shear_rate = N_rps * inputs.impeller_diameter_m * 10.0  # 1/s

        # Zero-shear viscosity (ingredient-based; replace with PIML)
        n_0 = 0.5 + 2.0 * comp.sugar + 1.5 * comp.solids
        # Carreau-Yasuda: η = η_∞ + (η_0 - η_∞) * [1 + (λγ̇)^a]^((n-1)/a)
        a, n = 2.0, 0.4
        reduced = (self.lambda_carreau * max(shear_rate, 1e-6)) ** a
        mu = self.n_infty + (n_0 - self.n_infty) * ((1 + reduced) ** ((n - 1) / a))

        # Power draw P = K μ N² D³
        K, D = 2.0, inputs.impeller_diameter_m
        power_W = K * mu * (N_rps**2) * (D**3)

        # Residue: f(μ, area)
        residue_kg = 0.05 * (mu**0.5) * (inputs.tank_surface_area_m2 / 10.0) * inputs.tank_surface_area_m2
        residue_kg = min(residue_kg, total_mass * 0.15)
        product_kg = total_mass - residue_kg

        product_batch = ProductBatch(
            mass_kg=product_kg, temperature_K=T, viscosity_Pa_s=mu, composition=comp,
        )
        tank_residue = TankResidue(mass_kg=residue_kg, composition=comp, viscosity_Pa_s=mu)
        return product_batch, tank_residue, power_W


def main() -> None:
    raw_materials = RawMaterials(
        milk=50.0, cream=20.0, sugar=15.0, stabilizers=1.0, water=14.0,
    )
    mixing_model = CustomMixingModel(n_infty=0.001, lambda_carreau=2.0)
    bioplastic_model = DefaultBioconversionModel(yield_coefficient=0.45)

    report = run_full_cycle(
        raw_materials=raw_materials,
        mixing_model=mixing_model,
        bioconversion_model=bioplastic_model,
        interface_flush_L=5.0,
        water_volume_L=60.0,
    )

    out = {k: v for k, v in report.items() if k != "typed_report"}
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
