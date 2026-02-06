"""
Example: Run one full MaterialBatch cycle and print the report.

  Mixing → CIP → Filtration → Bioplastic conversion

Uses the MaterialBatch-centric pipeline (batch_models, mixer, cip,
filtration, bioconversion). Customize RawMaterials and parameters
to explore efficiency and plastic yield.
"""

from icecream_simulator import RawMaterials, run_full_cycle, print_report

# Custom recipe: more sugar => more potential bioplastic from wastewater
raw = RawMaterials(
    milk=100.0,
    cream=30.0,
    sugar=25.0,
    stabilizers=2.0,
    water=43.0,
)

report = run_full_cycle(
    raw_materials=raw,
    tank_surface_area_m2=10.0,
    water_volume_L=80.0,
    bioplastic_yield_coefficient=0.4,
)

print_report(report)

# Access numeric results programmatically
print("\nKey metrics:")
print(f"  Bioplastic (kg):     {report['bioconversion']['bioplastic_mass_kg']:.4f}")
print(f"  Plastic/tonne input: {report['efficiency_summary']['plastic_kg_per_tonne_input']}")
