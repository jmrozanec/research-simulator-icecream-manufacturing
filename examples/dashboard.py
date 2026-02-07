"""
Monitoring Dashboard — Streamlit app to follow simulation stages in real time.

Run with: streamlit run examples/dashboard.py

Single pipeline: Mixer → CIP → Filtration → Bioplastic (MaterialBatch flow).

Requires: pip install streamlit
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import streamlit as st

from icecream_simulator import (
    RawMaterials,
    run_full_cycle,
    DefaultMixerModel,
    DefaultBioconversionModel,
)


st.set_page_config(
    page_title="Ice Cream Simulator — Monitoring",
    page_icon="🍦",
    layout="wide",
)

st.title("🍦 Ice Cream Production & Waste-to-Plastic Simulator")
st.caption("Monitor the pipeline: Mixer → CIP → Filtration → Bioplastic")

# Sidebar: run parameters
st.sidebar.header("Run parameters")
milk = st.sidebar.number_input("Milk (kg)", value=100.0, min_value=0.0)
cream = st.sidebar.number_input("Cream (kg)", value=30.0, min_value=0.0)
sugar = st.sidebar.number_input("Sugar (kg)", value=25.0, min_value=0.0)
stabilizers = st.sidebar.number_input("Stabilizers (kg)", value=2.0, min_value=0.0)
water = st.sidebar.number_input("Water (kg)", value=43.0, min_value=0.0)
tank_surface_m2 = st.sidebar.number_input("Tank surface (m²)", value=10.0, min_value=0.1)
water_volume_L = st.sidebar.number_input("CIP water (L)", value=80.0, min_value=0.0)
bioplastic_yield = st.sidebar.slider("Bioplastic yield (g PHA / g sugar)", 0.1, 0.8, 0.4, 0.05)
air_overrun = st.sidebar.slider("Air overrun", 0.0, 1.0, 0.5, 0.05)
interface_flush_L = st.sidebar.number_input("Interface flush (L)", value=5.0, min_value=0.0)
include_cleaning_phase = st.sidebar.checkbox("Include cleaning phase", value=True)
demo_delay = st.sidebar.slider("Stage delay (s) — for demo effect", 0.0, 3.0, 1.0, 0.5)
run_btn = st.sidebar.button("▶ Run simulation")

status_container = st.empty()
progress_bar = st.progress(0, text="Idle")
stage_columns = st.columns(4)
stage_containers = [col.empty() for col in stage_columns]
summary_container = st.empty()
report_expander = st.expander("Full JSON report", expanded=False)

STAGE_TITLES = {
    "mixer": "1. Mixer",
    "cip": "2. CIP",
    "filtration": "3. Filtration",
    "bioconversion": "4. Bioplastic",
}


def render_stage_card(container, stage_name: str, title: str, result=None):
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
            if result.outputs:
                st.json(result.outputs)


if run_btn:
    status_container.info("Running simulation...")
    progress_bar.progress(0, text="Starting...")

    raw_materials = RawMaterials(milk=milk, cream=cream, sugar=sugar, stabilizers=stabilizers, water=water)
    stages = list(STAGE_TITLES)
    stage_results_store: dict[str, object] = {}

    def on_stage_complete(stage_name: str, result, cumulative: dict) -> None:
        stage_results_store[stage_name] = result
        idx = stages.index(stage_name)
        progress_bar.progress((idx + 1) / len(stages), text=f"Completed: {stage_name}")
        for i, sn in enumerate(stages):
            render_stage_card(
                stage_containers[i],
                sn,
                STAGE_TITLES[sn],
                stage_results_store.get(sn),
            )
        time.sleep(demo_delay)

    report = run_full_cycle(
        raw_materials=raw_materials,
        tank_surface_area_m2=float(tank_surface_m2),
        water_volume_L=float(water_volume_L),
        bioplastic_yield_coefficient=float(bioplastic_yield),
        mixing_model=DefaultMixerModel(),
        bioconversion_model=DefaultBioconversionModel(yield_coefficient=float(bioplastic_yield)),
        on_stage_complete=on_stage_complete,
        air_overrun=float(air_overrun),
        interface_flush_L=float(interface_flush_L),
        include_cleaning_phase=include_cleaning_phase,
    )
    progress_bar.progress(1.0, text="Done!")
    status_container.success("Simulation complete.")
    c1, c2, c3, c4 = summary_container.columns(4)
    c1.metric("Product to freezer", f"{report['mixer']['product_to_freezer_kg']:.1f} kg")
    c2.metric("Ice cream vol. (L)", f"{report['mixer'].get('ice_cream_volume_L', 0):.1f}")
    c3.metric("Bioplastic (PHA)", f"{report['bioconversion']['bioplastic_mass_kg']:.2f} kg")
    c4.metric("Plastic / tonne input", f"{report['efficiency_summary']['plastic_kg_per_tonne_input']} kg")
    if report["filtration"]["maintenance_required"]:
        st.warning("⚠️ Filter maintenance required (saturation > 90%)")
    if report["efficiency_summary"].get("mass_balance_closed", True):
        st.success("✅ Mass balance closed")
    else:
        st.warning("⚠️ Mass balance not closed")
    report_expander.json({k: v for k, v in report.items() if k != "typed_report"})
else:
    status_container.info("Adjust parameters in the sidebar and click **Run simulation**.")
    for i, (sn, title) in enumerate(STAGE_TITLES.items()):
        render_stage_card(stage_containers[i], sn, title, None)
