"""
Centralized constants and model parameters for the simulator.

Every numeric value used in the simulation logic lives here so it can be
inspected, calibrated, or swapped in one place. No hardcoded magic numbers
should appear in the pipeline modules.

Each constant is annotated with:
  - Unit
  - Status:
      WELL_KNOWN  — physical constant or unit conversion; do not tune.
      TYPICAL     — value from literature / industry practice; reasonable default.
      ESTIMATE    — placeholder that should be calibrated from experiment / data.
      OPERATIONAL — user-facing default (recipe, geometry, setpoint).
      NUMERICAL   — purely numerical (tolerances, floors, caps); not physical.

Two parameter packs already live in their own modules and follow the same
"declared constants" pattern, so they are NOT duplicated here:

  - ``crystallization_parameters.CrystallizationParameters`` — all ice-growth,
    Avrami / Gompertz, storage-ripening, Kelvin, and hardness coefficients.
  - ``literature_recipes.LITERATURE_PRESETS`` — paper-cited recipes.
"""

from __future__ import annotations


# =============================================================================
# Unit conversions and well-known physical constants
# =============================================================================

MG_PER_KG = 1e6
"""mg/kg. WELL_KNOWN."""

KG_PER_MG = 1e-6
"""kg/mg. WELL_KNOWN."""

SECONDS_PER_MINUTE = 60.0
"""s/min. WELL_KNOWN."""

KWH_TO_JOULES = 3.6e6
"""J/kWh. WELL_KNOWN."""

KELVIN_TO_CELSIUS_OFFSET = 273.15
"""K. WELL_KNOWN (0 °C in K)."""

SECONDS_PER_HOUR = 3600.0
"""s/h. WELL_KNOWN."""

METERS_PER_MICROMETER = 1e-6
"""m/µm. WELL_KNOWN."""

KELVIN_GIBBS_THOMSON_PREFACTOR = 4.0
"""— WELL_KNOWN. Prefactor in Gibbs–Thomson ΔT = 4·γ·T_m/(ρ·L·d) for spherical crystal."""

IFP_SUGAR_FRACTION_CAP = 0.5
"""— NUMERICAL. Cap on sugar mass fraction used in IFP correlation."""

KINETICS_TIME_FLOOR_S = 1.0
"""s. NUMERICAL. Lower clamp on residence time in kinetic models."""

PERCENT_FACTOR = 100.0
"""— WELL_KNOWN. Fraction → percent."""

KG_PER_TONNE = 1000.0
"""kg/tonne. WELL_KNOWN."""


# =============================================================================
# Densities
# =============================================================================

WATER_DENSITY_KG_L = 1.0
"""kg/L. WELL_KNOWN."""

MIX_DENSITY_KG_L = 1.05
"""kg/L. TYPICAL. Density of unaerated ice cream mix (~1.04–1.06)."""


# =============================================================================
# Raw material composition (mass fractions of incoming streams)
#   Used by mixer to derive fat / sugar / water / solids of the mix.
# =============================================================================

MILK_FAT_FRACTION = 0.04
"""— TYPICAL. Whole milk fat content (3.5–4%)."""

CREAM_FAT_FRACTION = 0.36
"""— TYPICAL. Heavy cream fat content (~36%)."""

MILK_MSNF_FRACTION = 0.09
"""— TYPICAL. Milk solids-non-fat (MSNF) fraction in milk."""

EGG_YOLK_FAT_FRACTION = 0.25
"""— TYPICAL. Egg yolk fat content."""

EGG_YOLK_SOLIDS_FRACTION = 0.10
"""— TYPICAL. Egg yolk protein/solids content."""

EGG_YOLK_WATER_FRACTION = 0.65
"""— TYPICAL. Egg yolk water content (1 - fat - solids)."""

VANILLA_EXTRACT_WATER_FRACTION = 0.65
"""— TYPICAL. Vanilla extract water content (dilute aqueous ethanol)."""

VANILLA_EXTRACT_SOLIDS_FRACTION = 0.35
"""— TYPICAL. Vanilla extract solids content."""

WASTEWATER_TSS_SUGAR_FRACTION = 0.12
"""— ESTIMATE. Sugar fraction attributed to TSS particulates in wastewater."""


# =============================================================================
# Specific heats of pure components (food engineering handbook values)
# =============================================================================

CP_WATER_J_KGK = 4180.0
"""J/(kg·K). WELL_KNOWN. Cp of liquid water."""

CP_FAT_J_KGK = 2010.0
"""J/(kg·K). TYPICAL. Cp of milk fat."""

CP_SUGAR_J_KGK = 1450.0
"""J/(kg·K). TYPICAL. Cp of sucrose."""

CP_SOLIDS_MSNF_J_KGK = 1550.0
"""J/(kg·K). TYPICAL. Cp of MSNF/solids."""


# =============================================================================
# Mixer — Rheology (Power Law fluid)
#   μ = k · γ^(n-1) · f_T · f_comp
# =============================================================================

RHEOLOGY_K_CONSISTENCY = 1.0
"""Pa·s^n. ESTIMATE. Consistency index k; needs rheometer fit."""

RHEOLOGY_POWER_INDEX_N = 0.5
"""— ESTIMATE. Flow behavior index n; <1 = shear-thinning."""

RHEOLOGY_TEMP_COEFF = -0.02
"""1/K. ESTIMATE. Linear temperature factor coefficient."""

RHEOLOGY_TEMP_REF_K = 293.0
"""K. WELL_KNOWN. Reference temperature for the temp factor (20 °C)."""

RHEOLOGY_TEMP_FACTOR_FLOOR = 0.1
"""— NUMERICAL. Lower clamp on (1 + c_T·(T-T_ref))."""

RHEOLOGY_SHEAR_RATE_FLOOR = 1e-6
"""1/s. NUMERICAL. Minimum shear rate before exponentiation."""

RHEOLOGY_LEGACY_SOLIDS_FACTOR = 2.0
"""— ESTIMATE. Legacy linear effect of stabilizers/solids on viscosity."""

RHEOLOGY_SUGAR_FACTOR = 0.5
"""— ESTIMATE. Linear effect of sugar on viscosity."""

RHEOLOGY_HYDROCOLLOID_FACTOR = 2.4
"""— ESTIMATE. Hydrocolloid effect on viscosity (raises strongly)."""

RHEOLOGY_EMULSIFIER_FACTOR = 0.85
"""— ESTIMATE. Emulsifier effect on viscosity (smaller than hydrocolloids)."""

SHEAR_RATE_TIP_MULTIPLIER = 10.0
"""1/m. ESTIMATE. γ ≈ multiplier · N · D for the impeller geometry."""


# =============================================================================
# Mixer — Power draw  →  P = K_power · μ · N² · D³
# =============================================================================

MIXING_POWER_NUMBER = 5.5
"""— TYPICAL. Impeller power number Np for a Rushton turbine in a baffled tank (turbulent Np ≈ 5–6).
Corrected from 2.0 (too low for Rushton; appropriate only for axial/pitched-blade) to 5.5.
Rushton et al. 1950 Chem. Eng. Prog. 46:395; Harnby et al. 2001 Mixing in Process Industries."""


# =============================================================================
# Mixer — Residue stuck to tank walls
#   m_residue = base · (μ/μ_ref)^p · (A/A_ref) · A
# =============================================================================

RESIDUE_BASE_KG_PER_M2 = 0.05
"""kg/m². ESTIMATE. Baseline residue per m² of tank surface."""

RESIDUE_REF_VISCOSITY_PA_S = 1.0
"""Pa·s. NUMERICAL. Reference viscosity used for normalization."""

RESIDUE_REF_AREA_M2 = 10.0
"""m². NUMERICAL. Reference area used for normalization."""

RESIDUE_VISCOSITY_EXPONENT = 0.5
"""— ESTIMATE. Exponent on viscosity ratio in residue model."""

RESIDUE_MAX_FRACTION_OF_BATCH = 0.15
"""— TYPICAL. Cap on mixer residue as a fraction of the batch (15%)."""


# =============================================================================
# Thermal properties of mix (linear in water fraction x_w)
#   k_th = a + b · x_w ;   c_p = a + b · x_w   (legacy linear PIML form)
# =============================================================================

THERMAL_CONDUCTIVITY_INTERCEPT_W_MK = 0.4
"""W/(m·K). TYPICAL. Intercept of thermal conductivity model."""

THERMAL_CONDUCTIVITY_SLOPE_W_MK = 0.2
"""W/(m·K). TYPICAL. Slope vs. water fraction."""

SPECIFIC_HEAT_INTERCEPT_J_KGK = 3500.0
"""J/(kg·K). TYPICAL. Intercept of legacy linear Cp model."""

SPECIFIC_HEAT_SLOPE_J_KGK = 500.0
"""J/(kg·K). TYPICAL. Slope vs. water fraction (legacy form)."""


# =============================================================================
# Industrial chain — process temperatures
# =============================================================================

T_PREP_K = 328.0
"""K. OPERATIONAL. Preparation mix temperature (~55 °C)."""

T_PASTEUR_K = 353.15
"""K. OPERATIONAL. HTST pasteurization outlet (~80 °C)."""

T_AFTER_COOL_STAGE1_K = 303.15
"""K. OPERATIONAL. PHE stage-1 outlet (~30 °C)."""

T_AFTER_COOL_K = 278.15
"""K. OPERATIONAL. PHE stage-2 outlet (~5 °C)."""

T_AGEING_K = 277.15
"""K. OPERATIONAL. Ageing vat hold temperature (~4 °C)."""

T_AFTER_FREEZER_K = 268.15
"""K. OPERATIONAL. Continuous freezer exit (~-5 °C)."""

T_HARDENING_K = 243.15
"""K. OPERATIONAL. Hardening tunnel outlet (~-30 °C)."""

T_STORAGE_DEFAULT_K = 248.15
"""K. OPERATIONAL. Default deep-freeze storage (~-25 °C)."""

T_FREEZER_COOLANT_K = 253.15
"""K. OPERATIONAL. SSHE coolant temperature (~-20 °C)."""


# =============================================================================
# Pasteurization
# =============================================================================

PASTEUR_D_REF_MIN = 0.2
"""min. TYPICAL. D-value (Listeria) at 72 °C reference (ICMSF dairy)."""

PASTEUR_T_REF_C = 72.0
"""°C. TYPICAL. Reference temperature for D-value model."""

PASTEUR_Z_C = 7.0
"""°C. TYPICAL. z-value for dairy pathogens."""

PASTEUR_MIN_LETHALITY_T_C = 60.0
"""°C. NUMERICAL. Below this T no lethality is credited."""

PASTEUR_LOG10_REDUCTION_CAP = 6.0
"""— NUMERICAL. Cap on log10 reduction (practical detection limit)."""


# =============================================================================
# Homogenization — Walstra-style scaling for fat globule d32
# =============================================================================

HOMOG_D32_REF_UM = 0.85
"""µm. TYPICAL. Reference d32 at p_ref."""

HOMOG_P_REF_BAR = 200.0
"""bar. TYPICAL. Reference homogenization pressure."""

HOMOG_PRESSURE_EXPONENT = 0.6
"""— TYPICAL. d32 ∝ P^(-b), Walstra & Oortwijn exponent for dairy homogenization.
Corrected from 0.45 to 0.6 (upper end confirmed by Walstra & Oortwijn 1975 Neth. Milk Dairy J. 29:263;
IDF Bulletin 1992 No. 271; range 0.55–0.65 across 10–30 MPa in milk fat systems)."""

HOMOG_VISCOSITY_EXPONENT = 0.25
"""— ESTIMATE. Pal–Rhodes exponent for emulsion viscosity."""

HOMOG_D32_INITIAL_UM = 3.0
"""µm. TYPICAL. Pre-homogenization fat globule d32."""

HOMOG_DEFAULT_PRESSURE_BAR = 200.0
"""bar. OPERATIONAL."""

HOMOG_D32_FLOOR_UM = 1e-6
"""µm. NUMERICAL. Floor for d32 to avoid divide-by-zero."""

HOMOG_PRESSURE_FLOOR_BAR = 1.0
"""bar. NUMERICAL. Lower clamp on pressure."""


# =============================================================================
# Ageing vat — fat crystallinity and residue
# =============================================================================

AGEING_X_MAX_FLOOR = 0.5
"""— TYPICAL. Lower bound for max crystallinity X_max."""

AGEING_X_MAX_UPPER = 0.75
"""— TYPICAL. Upper bound for max crystallinity X_max."""

AGEING_X_MAX_TEMP_SLOPE_PER_K = 0.25
"""— ESTIMATE. dX_max / d(T_melt - T_hold) coefficient."""

AGEING_T_MILK_FAT_REF_K = 290.0
"""K. TYPICAL. Effective milk fat melting/crystallization reference T."""

AGEING_X_MAX_TEMP_DENOMINATOR_K = 15.0
"""K. ESTIMATE. Denominator scaling temperature offset."""

AGEING_TIME_TAU_H_DEFAULT = 4.0
"""h. TYPICAL. Time constant for first-order crystallization."""

AGEING_TIME_TAU_H_FLOOR = 0.1
"""h. NUMERICAL. Lower clamp on tau."""

AGEING_TIME_H_DEFAULT = 4.0
"""h. OPERATIONAL. Default ageing duration."""

AGEING_VISCOSITY_CRYST_COEFF = 0.35
"""— ESTIMATE. μ_after = μ_in · (1 + coeff · crystallinity)."""

AGEING_VISCOSITY_COLD_MULTIPLIER = 1.15
"""— ESTIMATE. Ageing-temperature viscosity boost."""

AGEING_RESIDUE_BASE_PER_M2 = 0.02
"""kg/m². ESTIMATE. Baseline ageing-vat residue per m² of surface."""

AGEING_RESIDUE_REF_VISCOSITY_PA_S = 0.5
"""Pa·s. NUMERICAL. Reference viscosity for ageing-vat residue scaling."""

AGEING_RESIDUE_VISCOSITY_EXPONENT = 0.5
"""— ESTIMATE. Exponent on viscosity ratio in ageing residue."""

AGEING_NO_STIRRER_MULTIPLIER = 1.5
"""— ESTIMATE. Multiplier when stirrer is off (residue grows)."""

AGEING_RESIDUE_MAX_FRACTION_OF_BATCH = 0.03
"""— TYPICAL. Cap on ageing residue (3% of batch)."""

AGEING_DEFAULT_JACKET_FLOW_L_MIN = 20.0
"""L/min. OPERATIONAL."""


# =============================================================================
# Flavor and inclusions
# =============================================================================

FLAVOR_SUGAR_MASS_FRACTION = 0.45
"""— TYPICAL. Sugar fraction of flavor syrup."""

INCLUSION_SOLIDS_MASS_FRACTION = 0.92
"""— TYPICAL. Solids fraction of inclusions (chips, fruit)."""

INCLUSION_SUGAR_MASS_FRACTION = 0.08
"""— TYPICAL. Sugar fraction of inclusions."""

INCLUSION_VISCOSITY_BOOST_COEFF = 0.02
"""— ESTIMATE. Viscosity multiplier per (m_incl / m0) ratio."""

COMPOSITION_RENORM_THRESHOLD = 1.01
"""— NUMERICAL. Renormalize composition if Σ > this."""


# =============================================================================
# Freezer — overrun, dasher, SSHE
# =============================================================================

FREEZER_AIR_INJECTION_EFFICIENCY = 0.92
"""— ESTIMATE. Realized fraction of injected air."""

FREEZER_OVERRUN_SHEAR_BASE = 0.08
"""— ESTIMATE. Magnitude of shear/loss factor on overrun."""

FREEZER_OVERRUN_TIME_DECAY_S = 200.0
"""s. ESTIMATE. Residence-time decay for shear loss."""

FREEZER_OVERRUN_RPM_REF = 55.0
"""rev/min. ESTIMATE. Dasher RPM reference for overrun shear term."""

FREEZER_OVERRUN_RPM_COEFF = 0.002
"""1/(rev/min). ESTIMATE. RPM sensitivity in shear factor."""

FREEZER_OVERRUN_MIN = 0.05
"""— NUMERICAL. Floor on effective overrun."""

FREEZER_OVERRUN_MAX = 1.2
"""— NUMERICAL. Cap on effective overrun."""

FREEZER_RESIDENCE_TIME_FLOOR_S = 5.0
"""s. NUMERICAL."""

FREEZER_VISCOSITY_EXIT_MULTIPLIER = 1.08
"""— ESTIMATE. Viscosity boost from partial freezing in freezer."""

FREEZER_DASHER_POWER_NUMBER = 2.0
"""— ESTIMATE. Power number for SSHE dasher (mirrors mixer)."""

FREEZER_DEFAULT_BARREL_DIAMETER_M = 0.15
"""m. OPERATIONAL."""

FREEZER_DEFAULT_DASHER_RPM = 55.0
"""rev/min. OPERATIONAL."""

FREEZER_DEFAULT_RESIDENCE_TIME_S = 45.0
"""s. OPERATIONAL."""

FREEZER_VOLUME_FRACTION_WALL_ICE = 0.28
"""— TYPICAL. Volume fraction of ice attributed to wall nucleation (Cook & Hartel)."""

FREEZER_DEFAULT_AIR_OVERRUN = 0.5
"""— OPERATIONAL. Requested overrun fraction (0.5 = 50%)."""

FREEZER_DEFAULT_ICE_CRYSTAL_MEAN_UM = 40.0
"""µm. OPERATIONAL. Fallback ice crystal size from metadata."""


# =============================================================================
# Hardening
# =============================================================================

HARDENING_VISCOSITY_MULTIPLIER = 1.05
"""— ESTIMATE. Apparent viscosity factor after hardening."""

MELT_RATE_PROXY_NUMERATOR = 0.001
"""1/s. ESTIMATE. Numerator in melt-rate-proxy 1/hardness scaling."""


# =============================================================================
# CIP — Wash efficiency by detergent type
# =============================================================================

WASH_EFFICIENCY: dict[str, float] = {
    "alkaline": 0.92,
    "acid":     0.88,
    "neutral":  0.85,
    "enzyme":   0.95,
}
"""— ESTIMATE. Wash efficiency per detergent chemistry."""

WASH_EFFICIENCY_DEFAULT = 0.90
"""— ESTIMATE. Fallback when detergent type is unknown."""

CIP_DEFAULT_WATER_TEMP_K = 323.0
"""K. OPERATIONAL. Default CIP water temperature (~50 °C)."""

CIP_DEFAULT_WATER_VOLUME_L = 80.0
"""L. OPERATIONAL."""

CIP_DEFAULT_DETERGENT_TYPE = "alkaline"
"""— OPERATIONAL."""


# =============================================================================
# CIP — Pollution load coefficients
# =============================================================================

BOD_SUGAR_COEFFICIENT = 1.123
"""kg O₂ / kg sugar. WELL_KNOWN. Theoretical stoichiometric ThOD for lactose (C₁₂H₂₂O₁₁).
Corrected from 1.2 to 1.123 (=(12·32+22·16+11·16)/(342) ≈ 1.123); confirmed by Ruffino et al. 2014
Bioresour. Technol. 168:118; Demirel et al. 2013 J. Cleaner Prod. 54:142."""

BOD_FAT_COEFFICIENT = 2.5
"""kg O₂ / kg fat. TYPICAL. Stoichiometric ThOD for milk fat (triacylglycerols ≈ C57H110O6).
Corrected from 2.0 to 2.5 (empirical ThOD for dairy lipids 2.4–2.6); Ruffino et al. 2014;
Danalewich et al. 1998 Water Res. 32:3555."""

COD_TO_BOD_RATIO = 1.5
"""— TYPICAL. COD/BOD ratio for biodegradable organics (1.2–1.5)."""


# =============================================================================
# Prefiltration
# =============================================================================

PREFILTRATION_DEFAULT_TSS_REMOVAL = 0.62
"""— ESTIMATE. Fraction of TSS removed (typical 0.5–0.85 for dairy CIP pretreatment)."""

PREFILTRATION_TSS_REMOVAL_CAP = 0.92
"""— NUMERICAL. Upper cap on TSS removal fraction."""


# =============================================================================
# Hydrodynamic cavitation
# =============================================================================

CAV_DEFAULT_INLET_PRESSURE_BAR = 3.5
"""bar. OPERATIONAL. Upstream Venturi/orifice pressure."""

CAV_DEFAULT_PRESSURE_DROP_BAR = 1.2
"""bar. OPERATIONAL. Pressure drop across constriction."""

CAV_DEFAULT_RESIDENCE_TIME_S = 45.0
"""s. OPERATIONAL."""

CAV_DEFAULT_COD_REMOVAL_MAX = 0.32
"""— TYPICAL. Asymptotic max COD removal fraction (HC alone on dairy/food wastewater 25–35 %).
Tightened from 0.38 to 0.32 (midpoint 0.30–0.35); Padoley et al. 2012 J. Hazard. Mater. 219–220:69;
Patil et al. 2025 Curr. World Environ. 20:299."""

CAV_DEFAULT_K_OXIDATION_1_PER_S = 5e-4
"""1/s. TYPICAL. Pseudo-first-order rate scale for oxidation (HC-alone on dairy/food WW).
Corrected from 0.018 s⁻¹ (36× too high) to 5×10⁻⁴ s⁻¹ (0.03 min⁻¹); consensus range
5×10⁻⁴ – 8×10⁻⁴ s⁻¹; Gogate & Pandit 2004a Adv. Environ. Res. 8:501;
Saharan et al. 2012 IECR 51:1981; Gawande & Mali 2024 Mater. Today Proc."""

CAV_DEFAULT_CHAIN_SCISSION_MAX = 0.42
"""— TYPICAL. Max scission fraction per pass (MW reduction; Huang et al. 2013
Polym. Degrad. Stab. 98:37 — chitosan ~50 % in 30 min)."""

CAV_DEFAULT_K_SCISSION_1_PER_S = 7e-4
"""1/s. TYPICAL. Rate scale for mechanical scission.
Corrected from 0.022 s⁻¹ (31× too high) to 7×10⁻⁴ s⁻¹; Huang et al. 2013
Polym. Degrad. Stab. 98:37; Sun et al. 2017 ultrasonic dextran."""

CAV_DEFAULT_TSS_TO_DISSOLVED_COD_YIELD = 0.55
"""— ESTIMATE. kg COD released per kg TSS disrupted."""

CAV_DEFAULT_FOG_FRAGILIZATION = 0.35
"""— ESTIMATE. FOG droplets subject to emulsion breakup."""

CAV_INTENSITY_PROXY_GAIN = 1.4
"""— ESTIMATE. Gain applied to dimensionless intensity proxy."""

CAV_INTENSITY_DP_DECAY_BAR = 2.0
"""bar. ESTIMATE. Denominator in (1 - exp(-dp/this))."""

CAV_INLET_PRESSURE_FLOOR_BAR = 0.5
"""bar. NUMERICAL."""

CAV_PRESSURE_DROP_FLOOR_BAR = 0.05
"""bar. NUMERICAL."""

CAV_INTENSITY_FLOOR = 0.15
"""— ESTIMATE. Minimum effective intensity (0.15 + 0.85·intensity)."""

CAV_BOD_TO_COD_REMOVAL_RATIO = 0.6
"""— TYPICAL. BOD removal as fraction of COD removal (BOD₅/COD removal coupling).
Corrected from 0.92 to 0.60 (midpoint 0.50–0.70): dairy WW HC studies show COD drops
faster than BOD₅ (recalcitrant fraction removed first).
Padoley et al. 2012 J. Hazard. Mater. 219–220:69; Gogate & Pandit 2004a Adv. Environ. Res. 8:501."""

CAV_MACRO_TSS_FRACTION = 0.45
"""— ESTIMATE. Fraction of TSS treated as macromolecules."""

CAV_MACRO_FOG_FRACTION = 0.85
"""— ESTIMATE. Fraction of FOG treated as macromolecules."""

CAV_TSS_DISRUPTION_FRACTION = 0.55
"""— ESTIMATE. Fraction of fragmented mass that comes from TSS."""

CAV_EXTRA_COD_TO_COD_FACTOR = 0.35
"""— ESTIMATE. Net dissolved COD weighting from fragmentation."""

CAV_EXTRA_COD_TO_BOD_FACTOR = 0.12
"""— ESTIMATE. Net dissolved BOD weighting from fragmentation."""

CAV_FOG_DEPLETION_INTENSITY_COEFF = 0.8
"""— ESTIMATE. Intensity weight for FOG depletion."""

CAV_MW_INDEX_BEFORE = 1.0
"""— TYPICAL. Initial mean molecular weight index."""

CAV_MW_INDEX_SCISSION_COEFF = 0.75
"""— ESTIMATE."""

CAV_MW_INDEX_INTENSITY_COEFF = 0.2
"""— ESTIMATE."""

CAV_MW_INDEX_FLOOR = 0.12
"""— NUMERICAL."""

CAV_BIOAVAIL_SCISSION_COEFF = 0.15
"""— ESTIMATE."""

CAV_BIOAVAIL_MW_COEFF = 0.08
"""— ESTIMATE."""

CAV_OUTLET_TEMP_RISE_K = 0.5
"""K. ESTIMATE. Slight heating from cavitation work."""

CAV_PUMPING_ENERGY_COEFF_KWH = 0.011
"""kWh-derived. ESTIMATE. Pumping energy proxy coefficient."""

CAV_VOLUME_FLOOR_L = 1e-9
"""L. NUMERICAL."""

CAV_TIME_FLOOR_S = 1.0
"""s. NUMERICAL."""


# =============================================================================
# Filtration — Split ratios and rejection
# =============================================================================

PERMEATE_VOLUME_FRACTION = 0.70
"""— ESTIMATE. Fraction of feed volume passing as permeate."""

SUGAR_REJECTION_TO_RETENTATE = 0.85
"""— ESTIMATE. Fraction of dissolved sugar held back by membrane."""

SOLIDS_REJECTION_TO_RETENTATE = 0.90
"""— ESTIMATE. Fraction of suspended solids retained."""

PERMEATE_TSS_PASSAGE = 0.05
"""— ESTIMATE. Fraction of TSS that escapes into permeate (95% reject)."""

FILTER_FOULING_MASS_FRACTION = 0.10
"""— ESTIMATE. Fraction of retentate mass that fouls the membrane."""

FILTER_SATURATION_MAINTENANCE_THRESHOLD = 0.90
"""— TYPICAL. Saturation at which maintenance is flagged."""


# =============================================================================
# Filtration — Membrane / Darcy parameters
# =============================================================================

FILTER_PORE_SIZE_UM = 0.1
"""µm. OPERATIONAL. Default microfiltration pore size."""

FILTER_MEMBRANE_AREA_M2 = 10.0
"""m². OPERATIONAL. Default membrane surface area."""

FILTER_MAX_ACCUMULATED_MASS_KG = 50.0
"""kg. ESTIMATE. Mass on membrane at full saturation."""

FILTER_BASE_RESISTANCE_M_1 = 5e13
"""1/m. TYPICAL. Clean-membrane Darcy resistance (Rm) for NF/UF dairy membranes.
Corrected from 1×10¹² m⁻¹ (50–100× too low) to 5×10¹³ m⁻¹; literature range 5×10¹³ – 1×10¹⁴ m⁻¹.
Skim-milk NF: Bacchin et al. 2006 J. Membr. Sci. 281:232;
dairy UF surveys: Piry et al. 2012 J. Food Eng. 108:233."""

FILTER_FOULING_COEFFICIENT = 1e14
"""1/(m·kg). ESTIMATE. Resistance growth per kg of accumulated mass."""


# =============================================================================
# Bioconversion — Sugar → PHA
# =============================================================================

DEFAULT_YIELD_COEFFICIENT = 0.4
"""kg PHA / kg sugar. TYPICAL. Ralstonia eutropha range 0.3–0.45."""

BIOCONVERSION_BIOAVAILABILITY_LOWER = 0.85
"""— NUMERICAL. Lower clamp on cavitation bioavailability factor."""

BIOCONVERSION_BIOAVAILABILITY_UPPER = 1.35
"""— NUMERICAL. Upper clamp on cavitation bioavailability factor."""


# =============================================================================
# Default operational parameters (recipe, geometry, setpoints)
# =============================================================================

DEFAULT_RAW_MATERIALS_KG: dict[str, float] = {
    "milk": 100.0,
    "cream": 30.0,
    "sugar": 25.0,
    "stabilizers": 1.65,
    "emulsifiers_kg": 0.35,
    "water": 43.0,
}
"""kg. OPERATIONAL. Default 200 kg recipe (Harfoush 2024 baseline)."""

DEFAULT_TANK_SURFACE_AREA_M2 = 10.0
"""m². OPERATIONAL."""

DEFAULT_IMPELLER_DIAMETER_M = 0.5
"""m. OPERATIONAL."""

DEFAULT_AIR_OVERRUN = 0.5
"""— OPERATIONAL. Volume overrun fraction (0.5 = 50%)."""

DEFAULT_INTERFACE_FLUSH_L = 5.0
"""L. OPERATIONAL. Start-of-run discard."""

DEFAULT_TEMPERATURE_K = 278.0
"""K. OPERATIONAL. Initial mix temperature (~5 °C)."""

DEFAULT_MIXING_TIME_S = 300.0
"""s. OPERATIONAL."""

DEFAULT_RPM = 60.0
"""rev/min. OPERATIONAL."""

DEFAULT_STIRRER_ON = True
"""— OPERATIONAL."""

DEFAULT_PASTEURIZATION_HOLD_TIME_S = 15.0
"""s. OPERATIONAL."""

DEFAULT_PACKAGE_COUNT = 1
"""— OPERATIONAL."""

DEFAULT_FLAVOR_SYRUP_MASS_KG = 0.0
"""kg. OPERATIONAL."""

DEFAULT_INCLUSION_MASS_KG = 0.0
"""kg. OPERATIONAL."""

DEFAULT_STORAGE_TIME_S = 0.0
"""s. OPERATIONAL."""


# =============================================================================
# Numerical tolerances and floors
# =============================================================================

MASS_BALANCE_TOLERANCE_KG = 1e-5
"""kg. NUMERICAL. Closure tolerance for mass balance check."""

VOLUME_EPSILON_L = 1e-6
"""L. NUMERICAL. Floor for volume to avoid divide-by-zero."""

VOLUME_EPSILON_SMALL_L = 1e-9
"""L. NUMERICAL. Very small volume floor used in wastewater paths."""

MASS_EPSILON_KG = 1e-6
"""kg. NUMERICAL."""

GENERIC_FLOOR = 1e-6
"""— NUMERICAL. Generic small-number floor."""
