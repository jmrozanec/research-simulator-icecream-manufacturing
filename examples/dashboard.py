"""
Monitoring Dashboard — Streamlit app to follow simulation stages in real time.

Run with: streamlit run examples/dashboard.py

Supports two pipelines:
  - Pipeline 1: Mass balance (ProductionEngine + WasteLogic) with PIML mixing.
  - Pipeline 2: MaterialBatch (Mixer → CIP → Filtration → Bioplastic) with pluggable models.

Requires: pip install streamlit
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import streamlit as st

from icecream_simulator import (
    RawMaterials,
    SimulationRunner,
    PlaceholderMixingModel,
    PlaceholderBioplasticModel,
    run_full_cycle,
    DefaultMixerModel,
    DefaultBioconversionModel,
)


# Page config
st.set_page_config(
    page_title="Ice Cream Simulator — Monitoring",
    page_icon="🍦",
    layout="wide",
)

st.title("🍦 Ice Cream Production & Waste-to-Plastic Simulator")
st.caption("Monitor the pipeline stages as the simulation runs")

# Sidebar: pipeline choice and run parameters
st.sidebar.header("Pipeline")
pipeline = st.sidebar.radio(
    "Select pipeline",
    ["Pipeline 1: Mass balance (PIML + ProductionEngine + WasteLogic)", "Pipeline 2: MaterialBatch (Mixer → CIP → Filtration → Bioplastic)"],
    index=0,
)
use_material_batch = "MaterialBatch" in pipeline

st.sidebar.header("Run parameters")
milk = st.sidebar.number_input("Milk (kg)", value=100.0, min_value=0.0)
cream = st.sidebar.number_input("Cream (kg)", value=30.0, min_value=0.0)
sugar = st.sidebar.number_input("Sugar (kg)", value=25.0, min_value=0.0)
stabilizers = st.sidebar.number_input("Stabilizers (kg)", value=2.0, min_value=0.0)
water = st.sidebar.number_input("Water (kg)", value=43.0, min_value=0.0)
if not use_material_batch:
    shear_rate = st.sidebar.slider("Shear rate (1/s)", 10, 300, 120)
else:
    tank_surface_m2 = st.sidebar.number_input("Tank surface (m²)", value=10.0, min_value=0.1)
    water_volume_L = st.sidebar.number_input("CIP water (L)", value=80.0, min_value=0.0)
    bioplastic_yield = st.sidebar.slider("Bioplastic yield (g PHA / g sugar)", 0.1, 0.8, 0.4, 0.05)
demo_delay = st.sidebar.slider("Stage delay (s) — for demo effect", 0.0, 3.0, 1.0, 0.5)
run_btn = st.sidebar.button("▶ Run simulation")

# Placeholders for live updates
status_container = st.empty()
progress_bar = st.progress(0, text="Idle")
stage_columns = st.columns(4)
stage_containers = [col.empty() for col in stage_columns]
summary_container = st.empty()
report_expander = st.expander("Full JSON report", expanded=False)


def render_stage_card(container, stage_name: str, title: str, result=None):
    """Render a stage card with status."""
    with container.container():
        if result is None:
            st.markdown(f"### {title}")
            st.caption(stage_name)
            st.metric("Status", "⏳ Pending")
        else:
            st.markdown(f"### {title}")
            st.caption(f"{stage_name} · {result.model_used}")
            mb = result.mass_balance
            st.metric("Mass in", f"{mb.mass_in:.2f} kg")
            st.metric("Mass out", f"{mb.mass_out:.2f} kg")
            st.metric("Product", f"{mb.mass_product:.2f} kg")
            st.metric("Energy", f"{mb.energy_consumed:.2e} J")
            if result.outputs and stage_name == "mixing":
                st.json({"viscosity": result.outputs.get("viscosity"), "thermal_conductivity": result.outputs.get("thermal_conductivity")})
            elif result.outputs and stage_name == "production":
                st.json({"total_system_shrinkage_kg": result.outputs.get("total_system_shrinkage_kg"), "adhesion_loss_kg": result.outputs.get("adhesion_loss_kg"), "interface_flush_kg": result.outputs.get("interface_flush_kg")})
            elif result.outputs and stage_name == "wastewater":
                st.json({"volume_L": result.outputs.get("volume_L"), "bod_mg_L": result.outputs.get("bod_mg_L"), "fog_mg_L": result.outputs.get("fog_mg_L")})
            elif result.outputs and stage_name == "bioplastic_conversion":
                st.json({"bioplastic_mass": result.outputs.get("bioplastic_mass"), "conversion_yield": result.outputs.get("conversion_yield")})


STAGE_TITLES_P1 = {
    "mixing": "1. Mixing (PIML)",
    "production": "2. Production",
    "wastewater": "3. Wastewater",
    "bioplastic_conversion": "4. Bioplastic",
}
STAGE_TITLES_P2 = {
    "mixer": "1. Mixer",
    "cip": "2. CIP",
    "filtration": "3. Filtration",
    "bioconversion": "4. Bioplastic",
}

if run_btn:
    status_container.info("Running simulation...")
    progress_bar.progress(0, text="Starting...")

    raw_materials = RawMaterials(milk=milk, cream=cream, sugar=sugar, stabilizers=stabilizers, water=water)

    if use_material_batch:
        stages = ["mixer", "cip", "filtration", "bioconversion"]
        stage_titles = STAGE_TITLES_P2
    else:
        stages = ["mixing", "production", "wastewater", "bioplastic_conversion"]
        stage_titles = STAGE_TITLES_P1

    stage_results_store: dict[str, object] = {}

    def on_stage_complete(stage_name: str, result, cumulative: dict) -> None:
        stage_results_store[stage_name] = result
        idx = stages.index(stage_name)
        progress_bar.progress((idx + 1) / len(stages), text=f"Completed: {stage_name}")
        for i, sn in enumerate(stages):
            render_stage_card(
                stage_containers[i],
                sn,
                stage_titles[sn],
                stage_results_store.get(sn),
            )
        time.sleep(demo_delay)

    if use_material_batch:
        report = run_full_cycle(
            raw_materials=raw_materials,
            tank_surface_area_m2=float(tank_surface_m2),
            water_volume_L=float(water_volume_L),
            bioplastic_yield_coefficient=float(bioplastic_yield),
            mixing_model=DefaultMixerModel(),
            bioconversion_model=DefaultBioconversionModel(yield_coefficient=float(bioplastic_yield)),
            on_stage_complete=on_stage_complete,
        )
        progress_bar.progress(1.0, text="Done!")
        status_container.success("Simulation complete.")
        c1, c2, c3, c4 = summary_container.columns(4)
        c1.metric("Product to freezer", f"{report['mixer']['product_to_freezer_kg']:.1f} kg")
        c2.metric("Wastewater", f"{report['cip']['wastewater_mass_kg']:.1f} kg")
        c3.metric("Bioplastic (PHA)", f"{report['bioconversion']['bioplastic_mass_kg']:.2f} kg")
        c4.metric("Plastic / tonne input", f"{report['efficiency_summary']['plastic_kg_per_tonne_input']} kg")
        if report["filtration"]["maintenance_required"]:
            st.warning("⚠️ Filter maintenance required (saturation > 90%)")
        report_expander.json(report)
    else:
        runner = SimulationRunner(
            mixing_model=PlaceholderMixingModel(),
            bioplastic_model=PlaceholderBioplasticModel(conversion_yield=0.40),
        )
        report = runner.run(
            raw_materials=raw_materials,
            shear_rate=float(shear_rate),
            on_stage_complete=on_stage_complete,
            interface_flush_L=5.0,
            cleaning_water_inflow_L=80.0,
        )
        progress_bar.progress(1.0, text="Done!")
        status_container.success("Simulation complete.")
        c1, c2, c3, c4 = summary_container.columns(4)
        c1.metric("Ice cream", f"{report.total_product_mass:.1f} kg")
        c2.metric("Wastewater", f"{report.total_wastewater_mass:.1f} kg")
        c3.metric("Bioplastic (PHA)", f"{report.total_bioplastic_mass:.2f} kg")
        c4.metric("Total energy", f"{report.total_energy_consumed:.2e} J")
        if report.mass_balance_closed:
            st.success("✅ Mass balance closed")
        else:
            st.warning("⚠️ Mass balance not closed")
        report_expander.json(report.model_dump())

else:
    status_container.info("Adjust parameters in the sidebar and click **Run simulation**.")
    pipeline_hint = "MaterialBatch" in pipeline
    titles = STAGE_TITLES_P2 if pipeline_hint else STAGE_TITLES_P1
    for i, (sn, title) in enumerate(titles.items()):
        render_stage_card(stage_containers[i], sn, title, None)
