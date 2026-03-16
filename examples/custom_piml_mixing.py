"""
Example: Plugging in a Custom Bioconversion Model

The simulator uses the industrial chain (preparation → pasteurization →
homogenization → cooling → ageing → freezer → hardening); mixing (blending)
is only in the preparation stage and aeration (overrun) is in the freezer.
This example shows how to plug in a custom bioconversion model.

For custom preparation rheology (e.g. PIML, Carreau-Yasuda), you would
extend industrial_chain.run_preparation_mix to use your viscosity model.
"""

import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from icecream_simulator import RawMaterials, run_full_cycle, DefaultBioconversionModel


def main() -> None:
    raw_materials = RawMaterials(
        milk=50.0, cream=20.0, sugar=15.0, stabilizers=1.0, water=14.0,
    )
    bioplastic_model = DefaultBioconversionModel(yield_coefficient=0.45)

    report = run_full_cycle(
        raw_materials=raw_materials,
        bioconversion_model=bioplastic_model,
        interface_flush_L=5.0,
        water_volume_L=60.0,
    )

    out = {k: v for k, v in report.items() if k != "typed_report"}
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
