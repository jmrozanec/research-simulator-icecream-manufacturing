"""
Centralized parameters for the simplified ice-cream + valorization pipeline.

Symbols match docs/SIMPLIFIED_PIPELINE_REPORT.md. Each group cites where the
*idea* or *typical range* is grounded; calibrate values to your plant or lab.

Reference keys (full entries in docs/SIMPLIFIED_PIPELINE_REPORT.md §6):
  [H24] Harfoush et al., 2024 — integrated ice cream manufacturing / mass flows
  [G21] Giudici et al., 2021 — formulations, compositional tables
  [K19] Konstantas et al., 2019 — LCI, waste, cleaner production for ice cream
  [CH10] Cook & Hartel, 2010 — ice cream physico-chemistry (density/overrun context)
  [WZ19] Wari & Zhu, 2019 — production system / capacity losses (scheduling)
  [USDA] USDA FoodData Central / SR Legacy — commodity milk & cream fat (~3.25–4%, cream)
  [M14] Metcalf & Eddy, Wastewater Engineering — BOD/COD ratios, organic loads
  [PHE] Perry’s Chemical Engineers’ Handbook — hold-up, tank heel fractions (φ)
"""

from __future__ import annotations

# --- Physical / unit ---
# REF: SI / water at ~20 °C; no paper-specific claim.
WATER_DENSITY_KG_L = 1.0
# REF: [CH10]; ice cream mix often ~1.05–1.10 kg/L — mid-range for reporting volume.
RHO_MIX_KG_L = 1.05
MG_PER_KG = 1e6
KG_PER_MG = 1e-6
PERCENT = 100.0
KG_PER_TONNE = 1000.0
VOLUME_EPS_L = 1e-9

# --- Composition from raw materials (typical dairy splits) ---
# REF: Milk fat ~3.25–4% mass [USDA]; sim uses 4% as round compositional default [G21]–style recipes.
MILK_FAT_FRACTION = 0.04
# REF: Heavy cream ~36% fat typical [USDA]; used in [G21], [K19] formulation classes.
CREAM_FAT_FRACTION = 0.36
# REF: MSNF order-of-magnitude for fluid milk in ice-cream mix balances [G21], [CH10].
MILK_MSNF_FRACTION = 0.09
# REF: Egg yolk proximate splits (order-of-magnitude); [K19] premium vanilla-style mixes.
EGG_YOLK_FAT_FRACTION = 0.27
EGG_YOLK_SOLIDS_FRACTION = 0.17
EGG_YOLK_WATER_FRACTION = 0.56
# REF: Extract composition placeholder; trace in [K19] Table-style flavour ingredients.
VANILLA_EXTRACT_WATER_FRACTION = 0.85
VANILLA_EXTRACT_SOLIDS_FRACTION = 0.15

# --- Production split (wall losses; single knob replaces multi-stage residue model) ---
# REF: φ not a single universal constant in [H24]/[G21]. Collapses heel + film losses;
#       order 1–5% hold-up common for viscous foods [PHE]; [WZ19] motivate *line* loss budgeting.
#       [K19] LCI mindset: calibrate φ to plant mass balance. Default 2% is illustrative.
DEFAULT_RESIDUE_MASS_FRACTION = 0.02

# --- CIP ---
# REF: Wash volume/temperature — operational default; calibrate to site CIP SOP (not from [H24] eq.).
CIP_DEFAULT_WATER_VOLUME_L = 500.0
CIP_DEFAULT_WATER_TEMP_K = 333.15
CIP_DEFAULT_DETERGENT_TYPE = "alkaline"
# REF: ε values — engineering placeholders; dairy CIP literature varies by soil & chemistry;
#       tune using pilot CIP / COD mass balance if available [K19] waste framing.
WASH_EFFICIENCY = {"alkaline": 0.78, "neutral": 0.55, "acidic": 0.68}
WASH_EFFICIENCY_DEFAULT = 0.60
# REF: a_s, a_f — carbohydrate vs lipid contribution to BOD (order-of-magnitude) [M14]; not from ice-cream PDFs.
BOD_SUGAR_COEFFICIENT = 1.2
BOD_FAT_COEFFICIENT = 2.0
# REF: Typical domestic wastewater COD/BOD ~1.2–2.5; dairy can differ [M14]; mid-value placeholder.
COD_TO_BOD_RATIO = 1.4
# REF: Carbohydrate fraction attributed to TSS wash-off — calibrate; conceptually [M14] + [K19] WW characterization.
WASTEWATER_TSS_SUGAR_FRACTION = 0.12

# --- Prefiltration ---
# REF: Screening TSS removal — equipment-specific; ~50–70% for primary screens in some dairy WW guides; calibrate.
TSS_REMOVAL_FRACTION = 0.62

# --- Cavitation (bioavailability only; BOD/COD multipliers) ---
# REF: Hydrodynamic cavitation dairy WW — pilot literature (generic); pressures illustrative; tune to vendor map.
CAVITATION_INLET_PRESSURE_BAR = 3.5
CAVITATION_THROAT_PRESSURE_BAR = 0.5
CAVITATION_PRESSURE_REF_BAR = 2.0
# REF: Removal caps — placeholders;oxidative paths in HC reviews; not fixed in [H24].
CAVITATION_BOD_REMOVAL_MAX = 0.18
CAVITATION_COD_REMOVAL_MAX = 0.15
# REF: Bioavailability uplift for fermentation — phenomenological; calibrate to bioreactor data [K19] valorization narrative.
CAVITATION_BIOAVAILABILITY_GAIN = 0.12

# --- Membrane split ---
# REF: NF/RO flux & recovery — module-specific (datasheets); fixed split is illustrative [M14] membrane chapter concepts.
PERMEATE_VOLUME_FRACTION = 0.75
# REF: Sugar/lactose retention to retentate — order-of-magnitude for tight NF; calibrate to membrane trials.
SUGAR_FRACTION_TO_RETENTATE = 0.85
SOLIDS_REJECTION_TO_RETENTATE = 0.92
PERMEATE_TSS_PASSAGE = 0.08
FILTER_FOULING_MASS_FRACTION = 0.4
FILTER_MAX_ACCUMULATED_MASS_KG = 50.0
FILTER_BASE_RESISTANCE_M_1 = 1.0e11
FILTER_FOULING_COEFFICIENT = 5.0e10
FILTER_SATURATION_MAINTENANCE_THRESHOLD = 0.9
FILTER_PORE_SIZE_UM = 50.0
FILTER_MEMBRANE_AREA_M2 = 25.0

# --- Bioconversion ---
# REF: Cupriavidus necator / mixed culture PHA from sugars often ~0.3–0.5 g PHA/g substrate (highly strain & SRT dependent);
#       use biotech review or your strain data; [K19] motivates *valorization* not this exact Y.
DEFAULT_YIELD_COEFFICIENT = 0.4

# --- Mass balance ---
# REF: Numerical closure tolerance for recipe-scale masses — implementation choice.
MASS_BALANCE_TOLERANCE_KG = 0.5

# --- Defaults for demo run ---
# REF: Scaled demo batch; inspired by mass scales in [G21]/[H24] style recipes — adjust freely.
DEFAULT_RAW_MATERIALS_KG = {
    "milk": 100.0,
    "cream": 30.0,
    "sugar": 25.0,
    "stabilizers": 2.0,
    "emulsifiers_kg": 0.5,
    "water": 42.5,
    "cocoa_powder_kg": 0.0,
    "egg_yolk_kg": 0.0,
    "vanilla_extract_kg": 0.0,
    "vanillin_kg": 0.0,
}
