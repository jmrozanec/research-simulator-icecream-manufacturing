"""Streamlit UI for the simplified pipeline. Run: streamlit run examples/dashboard.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import streamlit as st

from icecream_simulator import RawMaterials, run_full_cycle

st.set_page_config(page_title="Ice cream + bioplastic (simplified)", layout="wide")
st.title("Ice cream production + washwater → bioplastic")

st.sidebar.header("Recipe (kg)")
milk = st.sidebar.number_input("Milk", value=100.0, min_value=0.0)
cream = st.sidebar.number_input("Cream", value=30.0, min_value=0.0)
sugar = st.sidebar.number_input("Sugar", value=25.0, min_value=0.0)
stabilizers = st.sidebar.number_input("Stabilizers", value=2.0, min_value=0.0)
water = st.sidebar.number_input("Water", value=43.0, min_value=0.0)
emulsifiers = st.sidebar.number_input("Emulsifiers", value=0.5, min_value=0.0)

st.sidebar.header("Process")
phi = st.sidebar.slider("Residue mass fraction φ (-wall loss)", 0.0, 0.15, 0.02, 0.005)
overrun = st.sidebar.slider("Air overrun (volumetric factor)", 0.0, 1.0, 0.5, 0.05)
water_L = st.sidebar.number_input("CIP water (L)", value=500.0, min_value=0.0)
yield_ = st.sidebar.slider("PHA yield Y (kg/kg sugar)", 0.1, 0.6, 0.4, 0.05)
include_clean = st.sidebar.checkbox("Include cleaning / valorization", value=True)

if st.sidebar.button("Run"):
    raw = RawMaterials(
        milk=milk,
        cream=cream,
        sugar=sugar,
        stabilizers=stabilizers,
        emulsifiers_kg=emulsifiers,
        water=water,
    )
    r = run_full_cycle(
        raw_materials=raw,
        residue_mass_fraction=phi,
        air_overrun=overrun,
        water_volume_L=water_L,
        bioplastic_yield_coefficient=yield_,
        include_cleaning_phase=include_clean,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Product (kg)", f"{r['production']['product_mass_kg']:.2f}")
    c2.metric("Bioplastic (kg)", f"{r['bioconversion']['bioplastic_mass_kg']:.4f}")
    c3.metric("Mass balance OK", str(r["summary"]["mass_balance_closed"]))
    st.json({k: v for k, v in r.items() if k != "typed_report"})
else:
    st.info("Set parameters and click **Run**.")
