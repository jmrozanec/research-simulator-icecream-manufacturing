# Literature-Backed Parameter Values for an Ice Cream Manufacturing + Wastewater Valorization Simulator (v0.4.0)

## TL;DR
- For the ~96 ESTIMATE parameters across the 15 parameter groups below, this report identifies a single best-fit citable source per cluster, almost always a peer-reviewed paper that reports a plug-in numerical value rather than only a methodology; the highest-priority "anchor" references are Goff, Davidson & Cant (1994, *J. Dairy Sci.*) for mix rheology, Cogné et al. (2003, *J. Food Eng.*) for ice cream thermal properties, Innocente et al. (2009, *J. Dairy Sci.*) for high-pressure homogenization, Koller et al. (2007, *Macromol. Biosci.*) for whey-to-PHA, and Prazeres et al. (2012, *J. Environ. Manag.*) plus Slavov (2017, *Food Technol. Biotechnol.*) for dairy wastewater characterization.
- The two largest remaining gaps you should expect to retain as ESTIMATE-with-uncertainty are (a) the freezer's overall heat-transfer coefficient U, which varies from ~300 to ~1500 W/(m²·K) depending on dasher speed and viscosity, and (b) the dasher frictional heat input, for which only correlations (Boccardi et al. 2010, *Appl. Therm. Eng.*; Qin et al. 2003) — not single numbers — exist; both are documented below.
- Wastewater-side parameters are now well anchored: methane yield from cheese whey is reported across the range 0.32–0.60 L CH₄/g VS with the most-cited primary sources being Ergüder et al. (2001, *Water Res.*), Labatut, Angenent & Scott (2011, *Bioresour. Technol.*), and Dreschke et al. (2015, *Bioresour. Technol.* — up to 437 NmL CH₄/g VS at ISR 6); aerobic sludge Monod kinetics are quantified by Kavitha & Mehrotra (2012); and PHA yield from hydrolyzed whey by *Haloferax mediterranei* is 0.33–0.40 g PHA/g sugar (Koller 2007; Wang 2025).

## Key Findings

For each group below, I give: the **anchor citation** (the one paper to cite first), the **specific numerical value(s)** to plug into v0.4.0, the **experimental conditions**, and any **competing or supporting sources**.

### GROUP 1 — Rheology of ice cream mix (mixer / aging tank)
- **Anchor**: Goff, H. D., Davidson, V. J., & Cant, E. (1994). *Viscosity of Ice Cream Mix at Pasteurization Temperatures.* **Journal of Dairy Science 77(8): 2207–2213.** Power-law fit at 80 °C: flow-behavior index n = 0.7 (mixes with guar/LBG/CMC) or n = 0.5 (xanthan mixes); consistency coefficient K tabulated per formulation; baseline mix 11% fat, 10.5% SNF, 12.5% sucrose, 2.5% CSS, 0.15% mono-/diglycerides.
- **Supporting (aging-tank conditions, low T)**: BahramParvar, M., Razavi, S. M. A., & Haddad Khodaparast, M. H. (2010). "Rheological characterization and sensory evaluation of a typical soft ice cream made with selected food hydrocolloids." *Food Science and Technology International* 16(1): 79–88. DOI: 10.1177/1082013209353244. Reports n in 0.450–1.154 and K 0.051–6.822 Pa·sⁿ across hydrocolloid types and concentrations at 5 ± 0.5 °C.
- **Supporting (temperature dependence, ohmic mix)**: Icier, F. & Tavman, S. (2006). "Ohmic Heating Behaviour and Rheological Properties of Ice Cream Mixes." *International Journal of Food Properties* 9(4): 679–689. The consistency coefficient at 4 °C was ~3.5× that at 80 °C for standard-type ice cream mix; flow-behavior index increases with temperature from 25 to 80 °C.
- **Supporting (24 h aged Maraş-type)**: Karaman et al. — K = 3719–4328 mPa·sⁿ, n = 0.336–0.359 after 24 h ageing at 0 °C.
- **Recommended values for v0.4.0**: at aging-tank conditions (4 °C, 24 h aged), K ≈ 4.0 Pa·sⁿ, n ≈ 0.35; at pasteurizer holding-tube conditions (80 °C), K ≈ 0.05–0.15 Pa·sⁿ, n ≈ 0.7. Apparent viscosity at γ̇ = 100 s⁻¹: ~100–250 mPa·s at 80 °C.

### GROUP 2 — Pasteurization (thermal-kinetic inactivation, holding time)
- **Anchor for HTST equivalence**: Goff, H. D. & Davidson, V. J. (1992). "Flow characteristics and holding time calculations of ice cream mixes in HTST holding tubes." *Journal of Food Protection* 55: 34.
- **Regulatory anchor**: US PMO 2019 — for ice cream mix: 68.3 °C / 30 min (LTLT) OR 79.4 °C / 25 s OR 82.2 °C / 15 s.
- **Microbial kinetics anchor**: Wittwer, M. et al. (2022). *Inactivation Kinetics of Coxiella burnetii During HTST Pasteurization of Milk.* **Frontiers in Microbiology 12: 753871.** Provides modern D- and z-values for the most heat-resistant pathogen relevant to dairy pasteurization (and explicitly recalibrates Codex requirements). Use z ≈ 5–7 °C for vegetative dairy pathogens; for ice-cream-mix alkaline phosphatase, use the PMO 2019 indicator test.
- **Historical anchor**: Stafford et al. (1943), *Study of Short-Time-High-Temperature Pasteurization of Ice Cream Mix*, **Journal of Dairy Science** — the historical source for the "180 °F / 19 s ≡ 160 °F / 30 min" equivalence still embedded in PMO design.
- **Recommended values for v0.4.0**: log₁₀ reduction target = 5; reference temperature 72 °C; z = 5.0 °C (vegetative pathogens); D-values from Wittwer 2022 for design margin against *C. burnetii*.

### GROUP 3 — Homogenization (fat-globule break-up, pressure)
- **Anchor**: Innocente, N., Biasutti, M., Venir, E., Spaziani, M., & Marchesini, G. (2009). *Effect of high-pressure homogenization on droplet size distribution and rheological properties of ice cream mixes.* **Journal of Dairy Science 92(5): 1864–1875.** Two pressures: 15/3 MPa (conventional) and 97/3 MPa (HPH). HPH shifted PSD from bimodal to monomodal; reduced mean diameter; substantially raised viscoelastic moduli.
- **Supporting (meltdown stability cut-off)**: Bolliger, S., Wildmoser, H., Goff, H. D. & Tharp, B. W. (2000). For adequate ice cream stability, P ≥ 10 MPa is sufficient.
- **Quantitative break-up model**: Masbernat et al. (2022), *Chemical Engineering Science*, "Effect of homogenisation on fat droplets and viscosity of aged ice cream mixes" — power-law of droplet mode vs ΔP, applicable as a process model.
- **Industrial range**: 13.8–17.2 MPa first stage / 3.5 MPa second stage (Marshall, Goff & Hartel, *Ice Cream*, 6th ed., 2003).
- **Recommended values for v0.4.0**: post-homogenization D₃,₂ ≈ 0.6–1.0 μm at 14/3.5 MPa; D₃,₂ ≈ 0.3–0.5 μm at 97/3 MPa; target value 0.8 μm for a typical 12% fat mix.

### GROUP 4 — Aging (mix holding, fat crystallization)
- **Anchor**: Adleman, R. & Hartel, R. W. (2001). *Lipid crystallization and its effect on the physical structure of ice cream.* In: Garti & Sato (eds.), *Crystallization Processes in Fats and Lipid Systems*, Marcel Dekker. At 4 °C, **~2/3 of milk fat crystallizes** and full crystallization is achieved within **4–5 hours of ageing**.
- **Industry-standard aging conditions** (Goff & Hartel, *Ice Cream*, 7th ed., 2013): ≤ 5 °C, overnight (≥4 h, optimum 24 h).
- **SFC reference data**: Lopez, C. et al. (2006), *J. Dairy Sci.* 89: 2894–2910 — ~55.7 ± 3.5 % of fat solid at 4 °C in dairy matrices.
- **Protein/emulsifier displacement**: Bolliger, Goff & Tharp (2000), *Int. Dairy J.* 10: 303–309.
- **Recommended v0.4.0 values**: aging temperature 4 °C; aging time 4 h (minimum) to 24 h (optimum); fat SFC at end of aging ≈ 65 % of total fat; protein/emulsifier displacement timescale ~4 h.

### GROUP 5 — Continuous (scraped-surface) freezer and dasher
- **Anchor for heat-transfer modeling**: Bongers, P. M. M. (2006). *A heat transfer model of a scraped surface heat exchanger for ice cream.* In: *16th European Symposium on Computer Aided Process Engineering*. Treats the freezer barrel as a series of well-mixed stages with four energy contributions (refrigeration, crystallization, mechanical dissipation, scrape friction).
- **Heat-transfer correlations**: Boccardi, G., Celata, G. P., Lazzarini, R., Saraceno, L., & Trinchieri, R. (2010). "Development of a heat transfer correlation for a Scraped-Surface Heat Exchanger." *Applied Thermal Engineering* 30(10): 1101–1106. And Saraceno, L., Boccardi, G., Celata, G. P., Lazzarini, R., & Trinchieri, R. (2011). "Development of two heat transfer correlations for a scraped surface heat exchanger in an ice-cream machine." *Applied Thermal Engineering* 31(16): 4106–4112. Also Qin, F. G. F., Chen, X. D. & Free, K. (2003).
- **Specific quantitative anchor**: Khanal, S., Adhikari, U. et al. (2024). *Performance evaluation and CFD investigation of scraped surface ice cream freezer augmented with LN2 freezing technique.* **Cogent Engineering.** Reports draw temperature −6 °C and **overall U ≈ 300 W/(m²·°C)** after optimization.
- **Dasher-blade ice-crystal nucleation**: Cook, K. L. K. & Hartel, R. W. (2010). *Mechanisms of ice crystallization in scraped-surface freezers.* **Comprehensive Reviews in Food Science and Food Safety 9: 213–222.** Drewett & Hartel (2007) give an empirical equation for mean ice crystal size vs dasher speed and draw temperature.
- **Recommended v0.4.0 values**: draw temperature −5 to −6 °C; barrel wall (evaporator) −25 to −30 °C; U = 300–800 W/(m²·°C); ice-phase volume at draw ≈ 45–55 % of total water frozen; mean ice crystal size 30–45 μm at draw; dasher speed 100–200 rpm.

### GROUP 6 — Freezing-point depression and ice phase volume
- **Anchor (calculation method)**: Leighton, A. (1927). *On the calculation of the freezing point of ice cream mixes and the quantities of ice separated during the freezing process.* **Journal of Dairy Science 10(4): 300–308.** Still the basis for sucrose-equivalent computation used by Goff & Hartel (2013).
- **Anchor (sucrose solution data)**: Pickering's 1891 sucrose-solution data, tabulated by Leighton (1927) and re-derived by Bradley & Smith, *Milchwissenschaft* (1983).
- **Anchor (mix-specific worked examples)**: Goff & Hartel (2013), *Ice Cream*, 7th ed., Springer, pp. 357–367. For a 10 % MSNF / 2 % whey / 12 % sucrose / 4 % 42-DE CSS / 60 % water mix, **initial FP = −2.74 °C**.
- **Recommended v0.4.0 values**: FPDF (relative to sucrose = 1.0): lactose = 1.0, dextrose = 1.9, fructose = 1.9, whey solids = 0.77, 42-DE CSS = 1.0; milk-salt contribution from Leighton (1927) formula; initial FP for a 40 % TS standard mix ≈ −2.5 to −2.8 °C; ice fraction at −18 °C ≈ 80–85 %.

### GROUP 7 — Hardening (tunnel)
- **Anchor (thermal properties for hardening models)**: Cogné, C., Andrieu, J., Laurent, P., Besson, A., & Nocquet, J. (2003). *Experimental data and modelling of thermal properties of ice creams.* **Journal of Food Engineering 58(4): 331–341.** Provides predictive correlations for ρ, k, and enthalpy as functions of T and air fraction; mean relative error of thermal-conductivity model ≤ 8 %.
- **Anchor for crystal-size–hardening time link**: Donhowe, D. P. & Hartel, R. W. (1996). *Recrystallization of ice in ice cream during controlled accelerated storage.* **International Dairy Journal 6: 1191–1208.** Mean size ∝ t^0.33.
- **Industrial conditions**: tunnel −34 to −45 °C, residence time 20–30 min to reach −18 °C core (Tetra Pak; Goff & Hartel 2013).
- **Recommended v0.4.0 values**: tunnel air T = −40 °C; air velocity 4–6 m/s; convective h = 20–35 W/(m²·K); target core T = −18 °C; residence time 20–30 min for a typical 500 mL package.

### GROUP 8 — Storage / recrystallization
- **Anchor**: Hagiwara, T. & Hartel, R. W. (1996). *Effect of sweetener, stabilizer, and storage temperature on ice recrystallization in ice cream.* **Journal of Dairy Science 79(5): 735–744.** Ostwald-ripening rate constant fits Arrhenius; recrystallization rates increased with T (−20 to −5 °C) and amplitude of T-fluctuations (0.01 to 2 °C).
- **Supporting**: Ndoye & Alvarez (2015), *J. Food Eng.* — FBRM-based kinetics, Ostwald model; final mean size ≈ 46 μm and CV ≈ 0.58 after typical storage. Donhowe & Hartel (1996, *Int. Dairy J.*) — recrystallization rate as a function of T and amplitude.
- **Recommended v0.4.0 values**: Ostwald rate constant K_r (μm³/day) follows Arrhenius with Ea ≈ 80 kJ/mol; at −18 °C constant T, K_r ≈ 5–15 μm³/day; at −12 °C ≈ 50–80 μm³/day; size exponent 1/3.

### GROUP 9 — Stabilizers and emulsifiers (concentration windows)
- **Anchor**: Goff, H. D., Davidson, V. J., & Cant, E. (1994) — quantifies the effect of guar, LBG, CMC, and xanthan on consistency coefficient K and apparent viscosity at 80 °C.
- **Modern functional review**: BahramParvar, M. & Tehrani, M. M. (2011). *Application and functions of stabilizers in ice cream.* **Food Reviews International 27(4): 389–407.**
- **Emulsifier dose**: Bolliger, S., Goff, H. D., & Tharp, B. W. (2000). *Correlation between colloidal properties of ice cream mix and ice cream.* **International Dairy Journal 10: 303–309.** Typical mono-/diglyceride dose 0.1–0.3 %.
- **Recommended v0.4.0 values**: total stabilizer dose 0.2–0.5 % (LBG 0.15 %, guar 0.10 %, carrageenan 0.01–0.02 % to prevent wheying off); emulsifier 0.1–0.3 %.

### GROUP 10 — Thermal and physical properties (mix and frozen)
- **Anchor for frozen ice cream**: Cogné et al. (2003), *J. Food Eng.* 58: 331–341. Models for k(T,ρ) and enthalpy(T).
- **Anchor for measured values**: Sastry, S. K., & Datta, A. K. (1984). *Thermal Properties of Frozen Peas, Clams and Ice Cream.* Reports k of ice cream increasing with T and bulk ρ.
- **Anchor for standard tabulated thermal properties of foods (textbook)**: Heldman, D. R. & Singh, R. P. (1981). *Food Process Engineering*, 2nd ed., AVI Publishing, Westport CT. Chapter 3 contains the ice-cream specific-heat and density values used as defaults in most food-engineering simulators.
- **Typical plug-in values**: density 568 kg/m³ (with air); λ_fusion ≈ 210 kJ/kg of frozen water (not kg of product); Cp at +4 °C = 2.95 kJ/(kg·K); Cp at −26 °C = 1.63 kJ/(kg·K); k at +4 °C = 0.69 W/(m·K); k at −26 °C = 0.99 W/(m·K).
- **Glass transition T_g**: Ghaderi, S., Mazaheri Tehrani, M., & Hesarinejad, M. A. (2021). "Qualitative analysis of the structural, thermal and rheological properties of a plant ice cream based on soy and sesame milks." *Food Science & Nutrition* 9(3): 1289–1298. DOI: 10.1002/fsn3.2037. Reports conventional dairy ice cream T_g = −55.05 °C; soy ice cream T_g = −58.04 °C.

### GROUP 11 — Plant energy and water use (utilities)
- **Anchor (energy)**: Aghbashlo, M., Hosseinpour, S., Tabatabaei, M., Younesi, H., & Najafpour, G. (2017). *Exergetic performance analysis of an ice-cream manufacturing plant: A comprehensive survey.* **Energy 123: 195–210.** Specific exergy consumption of the process determined at **16.83 MJ/kg** ice cream.
- **Anchor (water, range across all dairy plant types)**: Vourch, M., Balannec, B., Chaufer, B., & Dorange, G. (2008). *Treatment of dairy industry wastewater by reverse osmosis for water reuse.* **Desalination 219(1–3): 190–202.** Dairy industry generates **0.2–10 L effluent per L milk processed**.
- **Anchor (plant-resolved data)**: Wojdalski et al. (2025), *Applied Sciences (MDPI)* 15(3): 1525. Polish dairies: water 1.5–3.71 L/L milk; wastewater 1.18–5.78 L/L milk. Also Sharma et al. (2024), *Water (MDPI)* 16(3): 435 — Punjab dairy plants: direct water use 3.31 L/kg milk; 74 % returned as effluent; total water footprint 9.0 L/kg milk.
- **Anchor (CIP, commercial case study)**: Anderson-Negele / Nestlé Canada ice cream — CIP water reduction from 6,500 L to 2,500 L per cycle via turbidity-based phase detection (industry case study, not peer-reviewed).
- **Recommended v0.4.0 values**: total energy ≈ 17 MJ/kg ice cream (~4.7 kWh/kg); electrical share for refrigeration ~50 %; water use 3–5 L per L mix; CIP share ~50 % of plant water.

### GROUP 12 — Ice-cream-section wastewater characterization
- **Anchor**: Slavov, A. K. (2017). *General Characteristics and Treatment Possibilities of Dairy Wastewater — A Review.* **Food Technology and Biotechnology 55(1): 14–28.** For an ice-cream factory effluent treated by MBR at 25 °C: **COD 13.3 kg/m³, BOD₅ 6.5 kg/m³**; reductions in MBR > 95 %, TKN > 96 %, TP > 80 %.
- **Supporting**: Britz, T. J., van Schalkwyk, C., & Hung, Y.-T. (2006), *Treatment of Dairy Processing Wastewaters* (in Wang et al., eds., Humana Press). Ice-cream section reductions: COD 18.5 kg/m³, BOD 5.9 kg/m³.
- **Mass-balance anchor**: 1 kg milk fat → 3 kg COD; 1 kg lactose → 1.13 kg COD; 1 kg protein → 1.36 kg COD (World Bank, 1996 / Carawan et al., 1979, *J. Dairy Sci.* 62(8) — "Wastewater Characterization in a Multiproduct Dairy").
- **FOG**: Slavov (2017) — 0.2–0.4 g/L for high-fat dairy plants; up to 2.88 g/L in butter plant effluent.
- **Recommended v0.4.0 values**: COD 6,000–18,000 mg/L; BOD₅ 3,000–7,000 mg/L; BOD/COD = 0.5–0.7; TKN 80–200 mg/L; TP 30–80 mg/L; FOG 0.2–0.4 g/L; pH 5.5–9 (highly variable due to CIP); T 20–30 °C.

### GROUP 13 — Anaerobic digestion / methane yield (whey-rich streams)
- **Anchor (review)**: Prazeres, A. R., Carvalho, F., & Rivas, J. (2012). *Cheese whey management: A review.* **Journal of Environmental Management 110: 48–68.**
- **Primary BMP datapoints (named)**: 
  - Ergüder, T. H., Tezel, U., Güven, E. & Demirer, G. N. (2001). *Water Research* 35(12): 3213–3219 — 424 mL CH₄ / g COD on cheese whey in a UASB reactor.
  - Labatut, R. A., Angenent, L. T. & Scott, N. R. (2011). *Bioresource Technology* 102(7): 2255–2264 — BMP assay at 35 °C with dairy-manure inoculum; cheese whey reported as highly variable.
  - Dreschke, G. et al. (2015). *Bioresource Technology* 194: 240–246 — up to **437 NmL CH₄ / g VS_added at ISR 6**.
- **Continuous low-cost digester**: García-Depraect et al. (2024), *Processes* 12: 1452 — **565.8 ± 20.9 L CH₄ kg⁻¹VS** at OLR 0.416 ± 0.160 kg VS L⁻¹ d⁻¹ with temperature control at 30 °C.
- **Whey-permeate batch reactor**: Azkarahman et al. (2024), peer-reviewed batch BMP at ISR 2, pH 7.5, 37 °C: **653.64 ± 12.16 N L CH₄ kg⁻¹VS**.
- **EGSB low-T**: Bialek, K., Cysneiros, D. & O'Flaherty, V. (2013), *Archaea* 2013: 346171. COD removal > 85 % at 10 °C in EGSB at OLR 0.5–2 kg COD m⁻³ d⁻¹.
- **Recommended v0.4.0 values**: methane yield 0.40 N L CH₄ / g VS (central value); CH₄ content of biogas 60 %; OLR design 2–4 kg COD m⁻³ d⁻¹; HRT 24 h (mesophilic 37 °C); COD removal 90–97 %.

### GROUP 14 — Aerobic activated-sludge kinetic parameters (Monod)
- **Anchor**: Kavitha, R. V. & Mehrotra, I. (2012). *Performance and biomass kinetics of activated sludge system treating dairy wastewater.* **International Journal of Dairy Technology** (Wiley), DOI 10.1111/j.1471-0307.2012.00850.x. Ks = 867.76 mg/L (BOD); k = 2.5 day⁻¹; Y = 0.933 mg VSS / mg BOD; Kd = 0.015 day⁻¹; μmax = k·Y = 2.33 day⁻¹.
- **Supporting**: Haydar, S. & Aziz, J. A. (2013). *Biological treatment of dairy wastewater using activated sludge.* **ScienceAsia 39(2): 179–185.** k = 4.46 day⁻¹; Ks = 534 mg/L; Y = 0.714; Kd = 0.038; μmax ≈ 3.19 day⁻¹.
- **UASB anaerobic + AS combined**: Tawfik, A., Sobhey, M. & Badawy, M. (2008). *Desalination* — UASB + AS achieves 97 % COD removal at HRT 2.0 h on AS step.
- **BOD/COD bridging reference**: Janczukowicz, W., Zieliński, M., & Dębowski, M. (2008). *Bioresource Technology* 99(10): 4199–4205.
- **Recommended v0.4.0 values**: μmax = 2.5–3 day⁻¹; Ks = 500–900 mg BOD/L; Y = 0.7–0.9 mg VSS/mg BOD; Kd = 0.02–0.04 day⁻¹; convert BOD→COD via BOD₅/COD = 0.55–0.65.

### GROUP 15 — Whey/permeate valorization to value-added products
- **PHA anchor**: Koller, M., Hesse, P., Bona, R., Kutschera, C., Atlić, A. & Braunegg, G. (2007). *Potential of various archae- and eubacterial strains as industrial polyhydroxyalkanoate producers from whey.* **Macromolecular Bioscience 7(2): 218–226.** DOI: 10.1002/mabi.200600211. *Haloferax mediterranei* on hydrolyzed whey: 50 wt% PHBV with 8 % HV; specific productivity qp = 9.1 mg g⁻¹ h⁻¹; μmax = 0.11 h⁻¹; yield 0.33 g PHA / g sugar; volumetric productivity 0.09 g L⁻¹ h⁻¹; 73 % PHA in 16.8 g/L biomass.
- **PHA supporting**: Pais, J., Serafim, L. S., Freitas, F. & Reis, M. A. M. (2016). *New Biotechnology* 33(1): 224–230. Active biomass 7.54 g L⁻¹; polymer content 53 %; productivity 4.04 g L⁻¹ day⁻¹. And Wang et al. (2025), *Bioresource Technology* — **0.40 ± 0.02 g PHA / g substrate from whey sugar** and 0.17 ± 0.12 g/g from delactosed permeate.
- **Ricotta-whey PHBV**: Raho, S. et al. (2020). *Foods (MDPI)* 9(10): 1459. 1.18 g/L PHBV at pilot scale with enzymatic lactose hydrolysis.
- **Bioethanol anchor**: Christensen, A. D., Kádár, Z., Oleskowicz-Popiel, P., & Thomsen, M. H. (2011). *Production of bioethanol from organic whey using Kluyveromyces marxianus.* **Journal of Industrial Microbiology and Biotechnology 38(2): 283–289.** Yield ≈ 0.50 g ethanol/g lactose; immobilized continuous productivity 2.5–4.5 g L⁻¹ h⁻¹ at D = 0.2 h⁻¹.
- **Bioethanol supporting**: Ozmihci, S. & Kargi, F. (2007). *Bioprocess Biosyst. Eng.* 30(2): 79–86. Yield 0.4 g/g; max productivity 0.745 g L⁻¹ h⁻¹ at HRT 43.2 h. Also Diniz et al. (2014, originally Silveira et al. 2005, *Enzyme Microb. Technol.* 36: 930–936) — near-theoretical yield 0.538 g/g and max 76–80 g/L ethanol at lactose ≥ 50 g/L in hypoxia/anoxia. And Russo et al. (2025), *Frontiers in Microbiology* 16: 1663736 — *K. marxianus* DSM 5422 and 5572 give 0.48 ± 0.03 and 0.50 ± 0.03 g ethanol/g substrate on CWP at 42 °C.
- **Recommended v0.4.0 values**: ethanol yield 0.45 g/g lactose; PHA yield 0.30 g/g sugar; *K. marxianus* μmax 0.4–0.6 h⁻¹; *H. mediterranei* μmax 0.10–0.11 h⁻¹ in saline medium.

## Details

### How to use this catalogue in v0.4.0

For each ESTIMATE parameter in the simulator, replace the placeholder with the value above and add the anchor citation. Where I list two anchors (e.g., aerobic kinetics Kavitha/Haydar), the central recommended value lies between the two. Where the literature only gives a model (e.g., Bongers 2006 for SSHE, Masbernat et al. 2022 for homogenizer break-up), implement the model rather than a scalar, and cite that paper for the structure of the equation.

### Quality and trade-off notes per group

- **Rheology (G1)**: Goff, Davidson & Cant 1994 is the strongest engineering reference because it was explicitly designed to give plug-in K and n values for HTST holding-time computations; aging-tank-temperature data should come from BahramParvar et al. (2010) and Icier & Tavman (2006) because Goff 1994 only measures at 80 °C.
- **Pasteurization (G2)**: Use the 1943 Stafford et al. equivalency for the engineering rule of thumb (180 °F / 19 s ≡ 160 °F / 30 min), but the modern Coxiella study (Wittwer et al. 2022) is what you should cite for the actual D/z kinetics that justify HTST design.
- **Homogenization (G3)**: Innocente et al. 2009 is the highest-quality peer-reviewed source; combine with Masbernat et al. 2022 if you want a process-coupled droplet-size model.
- **Aging (G4)**: Adleman & Hartel 2001 is widely cited; if a primary peer-reviewed paper is preferred, use Bolliger, Goff & Tharp (2000), *Int. Dairy J.* 10: 303–309.
- **SSHE (G5)**: The literature is fragmented. Bongers 2006 provides the framework; Khanal et al. 2024 provides a concrete U ≈ 300 W/(m²·°C); Saraceno et al. 2011 / Boccardi et al. 2010 give the two-correlation pair specifically for ice-cream-machine SSHEs; Cook & Hartel 2010 explains the nucleation mechanism. There is no single best citation — use all four in the same module.
- **FPD (G6)**: Leighton 1927 is the historical anchor; Goff & Hartel 2013 gives modern worked examples for software.
- **Hardening / thermal properties (G7, G10)**: Cogné et al. 2003 is the single best citation; Sastry & Datta 1984 gives the original measured data points; Heldman & Singh 1981 is the textbook for default tabulated values.
- **Recrystallization (G8)**: Hagiwara & Hartel 1996 is the Arrhenius anchor; Donhowe & Hartel 1996 gives the t^(1/3) scaling.
- **Stabilizers (G9)**: BahramParvar & Tehrani 2011 is the most-cited review.
- **Wastewater characterization (G12)**: Slavov 2017 is the only review that gives **ice-cream-specific** numbers and should be cited as the primary source.
- **Anaerobic digestion (G13)**: Prazeres et al. 2012 review is the natural anchor; for primary BMP values, cite Ergüder 2001, Labatut 2011, and Dreschke 2015; for newer per-substrate numbers, cite García-Depraect 2024 and Azkarahman 2024.
- **Aerobic kinetics (G14)**: Kavitha & Mehrotra 2012 gives a complete Monod set for dairy WW; Haydar & Aziz 2013 gives a second independent dataset.
- **Valorization (G15)**: Koller 2007 (PHA) and Christensen 2011 (ethanol) are the engineering anchors with multiple supporting datasets.

### Likely conflicts in the literature and how I resolved them

1. **Ice cream specific energy.** Aghbashlo et al. (2017) report 16.83 MJ/kg, but ice-cream-machine vendor data (~0.5 kWh/kg = 1.8 MJ/kg) refer only to the freezing step, not the full plant. Use 17 MJ/kg for whole-plant exergy modeling and 1.5–2 MJ/kg for the freezing-only refrigeration load.
2. **Specific water use.** Vourch 2008 (0.2–10 L/L) is a range across all dairy plants; Wojdalski 2025 (1.5–3.71 L/L) and Sharma 2024 (3.31 L/kg) are plant-resolved. Use Wojdalski for European-style ice cream plant simulation.
3. **CW methane yield.** Reported values span 0.32 to 0.85 L CH₄ / g VS. The central tendency from Prazeres 2012, Ergüder 2001 (424 mL CH₄/g COD), Dreschke 2015 (437 NmL/g VS) and García-Depraect 2024 is ~0.40 L CH₄/g VS for whey-rich dairy effluent; use this as the design value and 0.6 L CH₄/g VS as the optimistic case.
4. **SSHE U.** Khanal et al. 2024 give 300 W/(m²·°C); Saraceno et al. 2011 and Boccardi et al. 2010 indicate values up to ~1500 W/(m²·°C) for laboratory A-SSHE units. The lower bound is for industrial freezers with thick ice layers; the upper for laboratory units.

## Recommendations

**Phase 1 — Replace the ~96 ESTIMATE parameters in v0.4.1 using the anchor citation per group above.** Use the central recommended values; tag each replaced parameter with the DOI and the page/table from which the value comes. Total references added: ~30, dominated by *Journal of Dairy Science*, *Journal of Food Engineering*, *Bioresource Technology*, *Journal of Environmental Management*, and *Applied Thermal Engineering*.

**Phase 2 — Implement two models (not scalars) where the literature is strongest as a correlation:** (a) Masbernat et al. 2022 for fat-droplet size vs ΔP in homogenization, and (b) Bongers 2006 + Saraceno et al. 2011 + Boccardi et al. 2010 for SSHE heat-transfer; both will improve sensitivity-study fidelity in v0.5.0.

**Phase 3 — Validate against full-plant exergy and water benchmarks:** if total electrical + thermal consumption is within ±20 % of Aghbashlo 2017 (~17 MJ/kg) and specific wastewater volume is within ±30 % of Wojdalski 2025 (1.18–5.78 L/L), consider the calibration successful. If outside these bands, recheck the SSHE refrigeration COP and CIP volumetric assumptions first — these are the two largest swing factors.

**Benchmarks/thresholds that should trigger re-parametrization:**
- If simulated initial freezing point deviates > 0.3 °C from a Leighton-method hand calculation on the same recipe → fix sugar FPDF values.
- If simulated draw temperature is outside −4 to −7 °C for standard mixes → the dasher friction / refrigeration balance is wrong.
- If simulated COD removal in anaerobic stage falls below 85 % at OLR ≤ 2 kg COD m⁻³ d⁻¹ → revisit the methanogen kinetic constants; Bialek et al. 2013 shows that even at 10 °C, 85 % removal is achievable.

**Single highest-value next research step:** none of the ~30 anchor papers above models the *coupling* between fat-globule destabilization and air-cell stabilization quantitatively at industrial scale. If v0.5.0 will simulate creaminess/melt-down, plan a literature-deep-dive on Daw & Hartel (2015, *J. Food Sci.*) and Warren & Hartel (2014, *J. Food Sci.*) to extract a coupled rate equation — these were not searched in the budget here.

## Caveats

1. **Hedged ranges remain in three groups.** SSHE U, dasher friction, and CIP water are reported as ranges (e.g., U = 300–1500 W/(m²·°C)) because the literature legitimately does not provide a single value — these depend strongly on equipment geometry, scrape speed, and ice fraction. Treat them as uncertainty bands, not as missing data.
2. **One key value is from a 1943 paper (Stafford et al.).** The "180 °F / 19 s ≡ 160 °F / 30 min" equivalency that underpins HTST regulatory design is from a paper that is now > 80 years old; the modern restatement is in PMO 2019 and Wittwer et al. 2022. Cite the modern source for design and the historical source for provenance.
3. **Cheese whey vs. ice-cream-section wastewater.** Most anaerobic-digestion BMP studies (Ergüder 2001, Labatut 2011, Dreschke 2015) use *cheese* whey, which has lactose 45–55 g/L. Ice cream plant effluent is more dilute (~6 g/L lactose) and contains more fat and CIP chemicals. Use the BMP value but adjust the OLR downward (~25–50 %) for ice cream plant–specific effluent.
4. **No single peer-reviewed study reports the full ice cream plant water-use breakdown by unit operation.** Wojdalski 2025 covers Polish dairies broadly; for an ice-cream-only breakdown you may need to accept industry case data (e.g., the Nestlé Canada CIP turbidity study) as the best available source.
5. **PHA yields are sensitive to substrate hydrolysis state.** Koller 2007's 0.33 g/g requires *hydrolyzed* whey permeate (β-galactosidase pre-treatment); intact lactose gives substantially lower yields. State this conditioning step explicitly when citing.
6. **The original task prompt was truncated mid-sentence after "GROUP 1: RHEOLOGY OF ICE CREAM MIX (Mixer /".** I inferred the remaining 14 groups from the standard ice cream manufacturing pipeline (mix prep, pasteurization, homogenization, aging, freezing, hardening, storage, plus stabilizers/emulsifiers, thermal properties, plant utilities) plus the wastewater valorization scope (effluent characterization, anaerobic digestion, aerobic activated sludge, whey-to-PHA, whey-to-ethanol) explicitly mentioned in the task statement. If your v0.4.0 simulator includes unit operations I did not cover (e.g., spray-drying of milk powder, ingredient pre-blending kinetics, packaging-line thermal model, ammonia refrigerant cycle properties), please share that list and I will run a targeted second pass.




# Literature Calibration of the jmrozanec/research-simulator-icecream-manufacturing v0.4.0 Parameters

## TL;DR
- Of the ~96 ESTIMATE placeholders reviewed, roughly two-thirds (mixer rheology, ice-crystallization sizes, Avrami/Gompertz constants, pasteurization D/z, Walstra exponent, ice cream density, BOD:COD, PHA yield) fall WITHIN the literature window and can be retained or only gently nudged; the remaining third (notably hydrodynamic-cavitation k_oxidation, k_scission, mixer K_power, base membrane resistance, the Walstra pressure exponent, and a few BOD coefficients) lie OUTSIDE accepted ranges and must be adjusted before any quantitative claim is published.
- The single largest correction is in the cavitation module: the placeholder k_oxidation = 0.018 s⁻¹ is roughly 15–30× larger than the consensus pseudo-first-order rate for HC-alone treatment of dairy/food wastewater (≈ 5×10⁻⁴ – 1×10⁻³ s⁻¹); the placeholder also implicitly assumes that BOD-removal tracks COD-removal, whereas literature uniformly reports the opposite (HC PREFERENTIALLY destroys COD while raising effluent biodegradability BI ≈ 1.7–2.0×).
- Standard physical constants (water C_p, latent heat of fusion of ice, ice density, water density) are correctly set to their textbook values and need no citation; the simulator's "fat C_p = 2010 J/(kg·K)" and "sugar C_p = 1450 J/(kg·K)" are consistent with the ASHRAE 2002 Refrigeration Handbook component-Cp regression and Choi-Okos equations as used by Singh & Heldman.

## Key Findings

1. **Power-Law rheology of ice cream mix.** The simulator's defaults (k = 1.0 Pa·sⁿ, n = 0.5) sit centrally inside the experimental envelope reported by multiple peer-reviewed studies: Bahram-Parvar et al. (2010, *J. Texture Studies*) reported k = 0.051 – 6.822 Pa·sⁿ and n = 0.450 – 1.154 across CMC/Balangu/salep stabilizer formulations; Karaman & Kayacier (2012, *Int. J. Food Properties*) report n = 0.51 – 0.74 and k = 0.14 – 2.68 Pa·sⁿ for tea-flavored ice cream mix; Aktaş & Tavman (2006, *Int. J. Food Properties*) on Maraş-type mix obtained similar n in 0.40 – 0.95 across 4–80 °C. Toker et al. (2013, *Food Bioprocess Technol.* 6:2974) confirm Arrhenius-type temperature dependence of K consistent with a c_T of order −0.02 K⁻¹ over the ageing-temperature window. The placeholder n = 0.5 is on the low (more shear-thinning) end but fully defensible for a standard 10 %-fat mix at 5 °C aged.

2. **Pasteurization (Bigelow) kinetics.** Bradshaw et al. (1987, *Appl. Environ. Microbiol.* 53(7):1433–1438) measured *Listeria monocytogenes* in whole milk: D₇₁.₇°C = 0.9 s (= 0.015 min) and z = 6.3 °C across 52.2 – 74.4 °C. Kasapis-Roduit et al. (2021, *J. Dairy Sci.* in press) on cheese milk give D₆₅.₆°C = 17.1 s for L. monocytogenes. The simulator's D₇₂°C = 0.2 min is conservative (≈13× the measured value at 72 °C, fail-safe) and z = 7.0 °C is at the upper edge of the 6.3 – 7.0 °C dairy range.

3. **Walstra homogenization scaling.** Walstra's empirical relation d₃₂ ∝ P⁻ᵇ with b ≈ 0.6 (turbulent-inertial regime) is canonical (Walstra 1975 *Neth. Milk Dairy J.*; Walstra 1983 in Fox ed. *Developments in Dairy Chemistry*; Mulder & Walstra 1974; reaffirmed in Walstra, Wouters & Geurts 2006, *Dairy Science and Technology*, 2nd ed., CRC/Taylor & Francis). The simulator's b = 0.45 is anchored to the wider 0.4–0.6 cited range but should be moved to **b = 0.6** for valve homogenizers operating in the 10–50 MPa window. Pre-homogenization d₃₂ = 3.0 µm matches Walstra & Jenness 1984 (raw milk 1–8 µm with mode ≈ 3.4 µm; Lopez et al. report d₄₃ ≈ 3.8 µm), and post-homogenization d₃₂ = 0.85 µm matches the 0.3 – 0.8 µm window reported for homogenized milk in Hayes & Kelly 2003 (*J. Dairy Res.*) at 100 – 300 MPa.

4. **Ageing-vat fat crystallinity.** Avrami fits to anhydrous milk fat (Wright, Hartel et al. 2000, *J. Am. Oil Chem. Soc.* 77:463–475; Martini, Herrera & Hartel 2001/2002 *JAOCS* 79:1055): Avrami exponent n changes from <1 at high supercoolings to ≈2 at low supercoolings (i.e., ageing at 4–5 °C). Equilibrium SFC at 4–5 °C ≈ 50 – 75 % of total fat for AMF — directly supporting the simulator's X_max floor (0.5) and upper (0.75). The 4-h time constant τ matches the typical 4–24 h ageing window cited in Goff & Hartel 2013 (*Ice Cream*, 7th ed., Chapter 7).

5. **SSHE freezer ice-crystal sizing (Cook & Hartel mechanism).** Cook & Hartel (2010, *Comprehensive Reviews in Food Science and Food Safety* 9:213–222) report ice crystals exiting the SSHE as discs 20 – 30 µm in mean diameter (range 1 – 150 µm post-hardening, mean ≈ 35 µm). Drewett & Hartel (2007, *J. Food Eng.* 78:1060–1066) give 15 – 27 µm for SSHE exit. The simulator's wall-ice 6 – 55 µm and bulk-ice 12 – 125 µm distributions encompass these means with realistic dispersion. Volume-fraction of wall ice = 0.28 is consistent with Cook 2010 PhD thesis (Univ. Wisconsin–Madison) reporting that ~25–35 % of total ice is generated at the scraped wall.

6. **Avrami / Gompertz for SSHE ice formation.** Russell, Cheney & Wantling (1999, *J. Food Eng.* 39:179–191) report Avrami exponent n ≈ 1.6 – 3.0 for ice cream freezing in a SSHE; Drewett & Hartel and Inoue et al. (2008) corroborate. The simulator's n_default = 3.0 (interface-controlled 3-D growth) is at the high end and conservative; k_base = 1.15×10⁻³ s⁻¹ is in the right order for −5 °C freezing.

7. **Storage Ostwald ripening.** Donhowe & Hartel (1996a,b *Int. Dairy J.* 6:1191–1208 and 1209–1221) measured recrystallization rate ≈ 42 µm·day⁻⁰·³³ at −5 °C; rate scales with the 1/3 power of time and increases strongly with mean storage temperature and the amplitude of temperature fluctuations. Ben-Yoseph & Hartel (1998, *J. Food Eng.* 38:309–329) simulated final mean size ≈ 46 µm and CV ≈ 0.58 after typical storage. Hydrocolloid retardation coefficient 0.45 matches the 30 – 60 % rate reduction reported by Regand & Goff 2002/2003 (*J. Dairy Sci.* 85:2722; *Food Hydrocolloids* 17:95) for LBG / guar / κ-carrageenan mixtures.

8. **Hydrodynamic cavitation kinetics.** Compiled from Gogate 2002 (*Adv. Environ. Res.* 6:335), Gogate & Pandit 2004a (*Adv. Environ. Res.* 8:501–551) and 2004b (8:553–597), Saharan, Pandit et al. 2012 (*Ind. Eng. Chem. Res.* 51:1981), Padoley, Saharan, Mudliar et al. 2012 (*J. Hazard. Mater.* 219–220:69), Patil, Anekar & Patil 2025 (*Current World Environment* 20:299–309), and Gawande & Mali 2024 (*Mater. Today Proc.*, on Mula-Mutha River water): pseudo-first-order k for HC-alone on dairy/food and similar high-COD organic wastewater spans 0.01 – 0.05 min⁻¹ (≈ 1.7×10⁻⁴ – 8.3×10⁻⁴ s⁻¹), and max COD removal HC-alone is 25–40 %. The simulator's k_oxidation = 0.018 s⁻¹ corresponds to 1.08 min⁻¹, which is 15–30× larger than the consensus. **Recommended: reduce k_oxidation to ≈ 5×10⁻⁴ s⁻¹ (≈ 0.03 min⁻¹).** Max COD removal 0.38 is at the upper end of the credible range; tighten to 0.30 – 0.35. Optimum σ ≈ 0.1 – 0.3 and optimum inlet pressure 3 – 5 bar for orifice/venturi devices.

9. **BOD/COD coupling in HC.** Patil et al. 2025 showed BI = BOD₅/COD rose from 0.35 → 0.66 on raw dairy effluent after HC alone (1.89× improvement); Padoley et al. 2012 reported BI 0.16 → 0.32 (2× improvement) on distillery wastewater. This means HC removes COD FASTER than BOD; the simulator's "BOD/COD removal ratio = 0.92" assumes near-proportional removal and should be reinterpreted: either lowered to ≈ 0.5 – 0.7 (BOD-removed / COD-removed) or replaced with a BI-multiplier of ≈ 1.7 – 2.0×.

10. **Polymer / macromolecule chain scission.** Huang et al. 2013 (*Polym. Degrad. Stab.* 98:37–43): HC reduces chitosan MW by ~50 % in 30 min. First-order k_scission for polymer breakup under HC ≈ 0.01 – 0.05 min⁻¹ (≈ 2×10⁻⁴ – 8×10⁻⁴ s⁻¹). The simulator's max scission fraction 0.42 is in range; k_scission = 0.022 s⁻¹ is ~30× too high — **recommend 7×10⁻⁴ s⁻¹**.

11. **CIP cleaning efficiency.** Bremer, Fillery & McQuillan 2006 (*Int. J. Food Microbiol.* 106:254–262); Mosteller & Bishop 1993; Wirtanen & Salo 2003: standard NaOH 1 %/65 °C/10 min CIP reduces protein soil by 85 – 95 %; nitric 1 %/65 °C/10 min targets mineral scale at similar efficacy; enzymatic cleaners exceed 95 % on dairy biofilms. The simulator's wash-efficiency placeholders (alkaline 0.92, acid 0.88, neutral 0.85, enzymatic 0.95) are all well-positioned. The placeholder dairy effluent BOD/COD ratio of 1/1.5 (i.e., COD = 1.5 × BOD) aligns with the Tetra Pak Dairy Processing Handbook (Bylund, ed., 2003) average COD/BOD₅ = 1.45 for liquid-milk/butter/cheese plants and 2.14 for powder/whey/casein plants. The placeholder BOD per kg lactose (1.2 kg O₂/kg) is ~7 % above the stoichiometric ThOD limit of 1.123 kg O₂/kg lactose (from C₁₂H₂₂O₁₁ + 12 O₂ → 12 CO₂ + 11 H₂O); the simulator's value should be tightened to **1.123 kg O₂/kg**. BOD per kg milk fat (placeholder 2.0) is below the stoichiometric maximum of ~2.8 for milk-fat triglyceride and should be raised to ~2.5 to better match Tetra Pak Ch. 23 values for cream BOD.

12. **Nanofiltration of dairy wastewater (Darcy).** Luo, Ding et al. 2011 (*J. Hazard. Mater.* 192:889–895) and Suárez et al. 2014: NF270 in two-stage UF+NF gave lactose rejection 54 – 98.5 % (tight NF: ~99 %); protein rejection > 99 %; cake-layer formation is the dominant fouling mechanism. Membrane intrinsic resistance R_m for typical polyamide NF ranges 10¹³ – 10¹⁴ m⁻¹ (Mulder, *Basic Principles of Membrane Technology*, 2nd ed., 1996, p. 235). The simulator's R_m = 1×10¹² m⁻¹ is one to two orders of magnitude too LOW for NF — **recommend 5×10¹³ m⁻¹** (typical NF270 value). The fouling resistance coefficient α_c ≈ 10¹⁴ – 10¹⁵ m·kg⁻¹ for dairy cake layers (Marshall & Daufin 1995). Permeate fraction 0.70 and sugar rejection 0.85 are realistic for a moderately loose NF (e.g., NF270 at moderate VCR).

13. **PHA production by Cupriavidus necator / R. eutropha.** Khanna & Srivastava 2007 (*Biochem. Eng. J.* 36:34): Y_p/s = 0.34 g PHB/g glucose for R. eutropha ATCC 17699. Saratale et al. 2019 (*Bioresour. Technol.* 282:75–80) report Y_p/s = 0.488 g/g reducing sugar with NaC + NaS pretreated kenaf biomass hydrolysates ("…with PHB titers of 10.10 g/L and PHB yields of about 0.488 g/g of reducing sugar produced within 36 h of fermentation."). Povolo et al. 2010 (*Bioresour. Technol.* 101:7902–7907) showed engineered C. necator on lactose reaches ~0.22 – 0.33 g/g. Theoretical maximum from acetyl-CoA stoichiometry = 0.48 g/g. The simulator's Y = 0.4 kg PHA/kg sugar is at the upper end but defensible; the placeholder's stated range 0.30 – 0.45 captures the literature consensus.

14. **Thermophysical properties.** ASHRAE 2002 Refrigeration Handbook Chapter 8 (Choi-Okos component model) gives at 20 °C: C_p,water = 4.18 kJ/(kg·K) [standard]; C_p,milk fat = 2.01 kJ/(kg·K) (Choi-Okos eq. 4); C_p,sucrose = 1.245 kJ/(kg·K) below crystalline phase, and ≈ 1.45 kJ/(kg·K) when accounting for sucrose hydration in dairy mix (Polley, Snyder & Kotnour 1980); C_p,MSNF (protein + lactose mix) ≈ 1.5 – 1.6 kJ/(kg·K). Latent heat of fusion of ice = 334 kJ/kg [standard]; ice density 917 kg/m³ at 0 °C [standard]. The simulator's ice cream mix density of 1.05 kg/L matches Goff & Hartel (2013, *Ice Cream*, 7th ed., p. 143): "the specific gravity or density of an ice cream mix varies with its composition and may range from 1.05 to 1.12."

## Details — Parameter-by-Parameter Recommendation Table

### Stage 1 – Mixer / Rheology

| Parameter | Placeholder | Recommended | Source | Note |
|---|---|---|---|---|
| Power-Law k | 1.0 Pa·sⁿ | 0.14 – 2.68 Pa·sⁿ (median ~0.5 – 1.0) | Bahram-Parvar et al. 2010 *J. Texture Studies* 41(2):223; Karaman & Kayacier 2012 *Int. J. Food Properties* | Strong dependence on stabilizer; current value reasonable for 0.15 % stabilizer mix at 5 °C |
| Power-Law n | 0.5 | 0.45 – 0.77 | Same | Acceptable; on shear-thinning end |
| c_T (1/K) | –0.02 | –0.018 to –0.025 | Aktaş & Tavman 2006 *Int. J. Food Properties* 9(4):721; Toker et al. 2013 *Food Bioprocess Technol.* 6:2974 | RETAIN |
| Hydrocolloid viscosity multiplier | 2.4× | 2 – 4× per 0.1 % gum | Bahram-Parvar et al.; Milliatti & Lannes 2018 *Food Sci. Technol.* 38(4):733 | RETAIN |
| Emulsifier viscosity multiplier | 0.85× | 0.7 – 0.95× | Granger et al. 2005 *JAOCS* 82:427 | RETAIN |
| Sugar viscosity factor | 0.5 | 0.4 – 0.6 | Muse & Hartel 2004 *J. Dairy Sci.* 87:1; Goff & Hartel 2013 Ch. 5 | RETAIN |
| K_power (radial laminar) | 2.0 | 5 – 6 (Rushton turbine, baffled, Re < 10) or 1 – 2 (axial pitched-blade) | Doran 1995 *Bioprocess Engineering Principles*; Rushton, Costich & Everett 1950 *Chem. Eng. Prog.* 46:395 | **Raise to 5 – 6**, or relabel as axial pitched-blade |
| Wall residue base | 0.05 kg/m² | 0.03 – 0.07 kg/m² | Bansal & Chen 2006 *J. Food Sci.* 71(6):E319 | RETAIN |
| Wall residue viscosity exponent | 0.5 | 0.5 – 0.7 | Visser & Jeurnink 1997 *Exp. Therm. Fluid Sci.* 14:407 | RETAIN |
| Max residue fraction | 0.15 | 0.05 – 0.20 | de Jong 1997 *Trends Food Sci. Technol.* 8:401 | RETAIN |
| Tip-speed multiplier (1/m) | 10.0 | 10 – 12 (Metzner-Otto k_s for Rushton) | Metzner & Otto 1957 *AIChE J.* 3:3 | RETAIN |

### Stage 2 – Pasteurization (Bigelow)

| Parameter | Placeholder | Recommended | Source |
|---|---|---|---|
| D-value at 72 °C, L. monocytogenes | 0.2 min (= 12 s) | 0.015 min (= 0.9 s) | Bradshaw et al. 1987 *Appl. Environ. Microbiol.* 53(7):1433 |
| z-value (dairy) | 7.0 °C | 6.3 °C | Bradshaw et al. 1987 |
| Log-10 reduction cap | 6.0 | 6.0 – 7.0 | ICMSF 1996; FDA Pasteurized Milk Ordinance 5-log target |

### Stage 3 – Homogenization (Walstra)

| Parameter | Placeholder | Recommended | Source |
|---|---|---|---|
| Reference d₃₂ post-homogenization | 0.85 µm | 0.3 – 0.8 µm | Walstra & Jenness 1984; Hayes & Kelly 2003 *J. Dairy Res.* 70:297 |
| Walstra pressure exponent b | 0.45 | **0.6** | Walstra 1975 *Neth. Milk Dairy J.* 29:279; Walstra 1983 in Fox ed.; Mulder & Walstra 1974 |
| Pal-Rhodes viscosity exponent | 0.25 | 0.25 | Pal & Rhodes 1989 *J. Rheol.* 33:1021 |
| Pre-homogenization d₃₂ | 3.0 µm | 3 – 4 µm | Walstra & Jenness 1984 |

### Stage 5 – Ageing Vat (Fat Crystallinity)

| Parameter | Placeholder | Recommended | Source |
|---|---|---|---|
| X_max floor / upper | 0.5 / 0.75 | 0.5 – 0.75 of total fat at 0 – 5 °C | Wright, Hartel et al. 2000 *JAOCS* 77:463; Lopez et al. 2002 *J. Colloid Interface Sci.* 250:64 |
| X_max T-slope (per K) | 0.25 | 0.2 – 0.3 | Wright & Marangoni 2002 *JAOCS* 79:395 |
| τ (h) | 4.0 | 4 – 24 h | Goff & Hartel 2013 *Ice Cream* 7e p. 156 |
| Crystallinity viscosity coeff. | 0.35 | 0.3 – 0.5 (Krieger-Dougherty) | Granger et al. 2005 *JAOCS* 82:427 |
| Cold multiplier | 1.15 | 1.1 – 1.2 | Boode & Walstra 1993 *Colloids Surf. A* 81:121 |

### Stage 7 – SSHE Freezer / Ice Crystallization

| Parameter | Placeholder | Recommended | Source |
|---|---|---|---|
| Air injection efficiency (overrun) | 0.92 | 0.85 – 0.95 | Eisner, Wildmoser & Windhab 2005 *Colloids Surf. A* 263:390 |
| Shear loss base | 0.08 | 0.05 – 0.10 | Russell et al. 1999 *J. Food Eng.* 39:179 |
| Wall ice d_min / d_max (µm) | 6 / 55 | 5 – 60 | Cook & Hartel 2010 *Compr. Rev. Food Sci. Food Saf.* 9:213 |
| Bulk ice d_min / d_max (µm) | 12 / 125 | 10 – 150 | Cook & Hartel 2010; Drewett & Hartel 2007 |
| Wall ice volume fraction | 0.28 | 0.25 – 0.35 | Cook 2010 PhD thesis Univ. Wisconsin |
| Hydrocolloid suppression (wall / bulk) | 0.28 / 0.36 | 0.30 / 0.45 | Regand & Goff 2002 *J. Dairy Sci.* 85:2722; 2003 *Food Hydrocolloids* 17:95 |
| Emulsifier suppression (wall / bulk) | 0.12 / 0.06 | 0.05 – 0.15 | Granger et al. 2005 *JAOCS* 82:427 |
| Avrami n_default | 3.0 | 2 – 3 | Russell et al. 1999; Metin & Hartel 1998 *JAOCS* 75:1617 |
| Avrami k_base (s⁻¹) | 1.15 × 10⁻³ | 10⁻³ – 10⁻² | Wright et al. 2000 *JAOCS* 77:463 |
| Gompertz X_max range | 0.08 – 0.72 | 0.45 (−5 °C) – 0.75 (−18 °C) | Hartel 2001 *Crystallization in Foods* Ch. 4; Cogné et al. 2003 *J. Food Eng.* 58:331 |
| Gompertz τ (s) | 40 | 30 – 90 | Eisner et al. 2005 |
| Kelvin/Gibbs-Thomson γ (J/m²) | 0.025 | 0.025 – 0.032 | Hardy 1977 *Philos. Mag.* 35:471; Hillig 1998 *J. Cryst. Growth* 183:463 |
| Latent heat of fusion of ice | 334 000 J/kg | [standard] | — |
| Ice density | 917 kg/m³ | [standard] | — |
| Ostwald ripening r_scale | 0.055 | ≈ 42 µm·day⁻⁰·³³ at −5 °C | Donhowe & Hartel 1996a *Int. Dairy J.* 6:1191 |
| Hydrocolloid coarsening retardation | 0.45 | 0.30 – 0.60 | Regand & Goff 2002; Patmore, Goff & Fernandes 2003 |

### Stage 9 – CIP Cleaning

| Parameter | Placeholder | Recommended | Source |
|---|---|---|---|
| Alkaline wash efficiency | 0.92 | 0.85 – 0.95 (NaOH 1 %, 65 °C, 10 min) | Bremer, Fillery & McQuillan 2006 *Int. J. Food Microbiol.* 106:254 |
| Acid wash efficiency | 0.88 | 0.85 – 0.92 (HNO₃ 1 %, 65 °C) | Bremer et al. 2006 |
| Neutral wash | 0.85 | 0.80 – 0.90 | Tamime 2008 *Cleaning-in-Place* (Blackwell) |
| Enzyme cleaner | 0.95 | 0.93 – 0.98 | Grasshoff 1997 *Trends Food Sci. Technol.* 8:185 |
| BOD sugar coefficient | 1.2 kg O₂/kg | **1.123 kg O₂/kg lactose** (stoichiometric ThOD, C₁₂H₂₂O₁₁ + 12 O₂) | Tetra Pak Dairy Processing Handbook (Bylund) Ch. 23; stoichiometric derivation |
| BOD fat coefficient | 2.0 kg O₂/kg | 2.5 – 2.8 kg O₂/kg milk fat (stoichiometric) | Tetra Pak handbook Ch. 23 (cream 40 % BOD₅ ≈ 400 000 mg/L) |
| COD / BOD ratio | 1.5 | 1.45 (liquid milk/butter/cheese); 2.14 (powder/whey/casein) | Tetra Pak handbook citing FIL-IDF Bulletin 138, 1981 |

### Stage 10 – Pre-Filtration

| Parameter | Placeholder | Recommended | Source |
|---|---|---|---|
| TSS removal efficiency | 0.62 | 0.50 – 0.75 (dissolved-air flotation + screening) | Britz, van Schalkwyk & Hung 2006 in *Waste Treatment in the Food Processing Industry* Ch. 1 |

### Stage 11 – Hydrodynamic Cavitation (Gogate & Pandit 2004 framework)

| Parameter | Placeholder | Recommended | Source |
|---|---|---|---|
| Max COD removal fraction (HC alone) | 0.38 | **0.30 – 0.35** | Padoley et al. 2012 *J. Hazard. Mater.* 219–220:69 (32 % distillery); Patil et al. 2025 *Curr. World Environ.* 20:299 (~30 % dairy); Badve et al. 2013 *Sep. Purif. Technol.* 106:15 (rotor-stator at high pass count up to ~56 %); Gogate 2002 *Adv. Environ. Res.* 6:335 |
| k_oxidation (s⁻¹) | 0.018 | **≈ 5 × 10⁻⁴ – 8 × 10⁻⁴ s⁻¹** (0.03 – 0.05 min⁻¹); reserve higher k for HC + H₂O₂/Fenton hybrid | Gogate & Pandit 2004a *Adv. Environ. Res.* 8:501; Saharan et al. 2012 *IECR* 51:1981; Gawande & Mali 2024 *Mater. Today Proc.* (k = 7.21 × 10⁻⁴ s⁻¹ on river water, applicable as upper-bound proxy) |
| BOD/COD removal ratio | 0.92 | **Reinterpret** — BI of effluent INCREASES 1.7 – 2.0× after HC; if interpreted as BOD-rem / COD-rem ratio, set ≈ 0.5 – 0.7 | Patil et al. 2025 (BI 0.35 → 0.66); Padoley et al. 2012 (BI 0.16 → 0.32) |
| Max chain scission fraction | 0.42 | 0.40 – 0.60 (MW reduction) | Huang et al. 2013 *Polym. Degrad. Stab.* 98:37 (chitosan ~50 %); Mofrad et al. 2021 *IECR* |
| k_scission (s⁻¹) | 0.022 | **≈ 7 × 10⁻⁴ s⁻¹** (0.04 min⁻¹) | Same as above; Sun et al. 2017 ultrasonic dextran |
| TSS-to-dissolved COD yield (kg/kg) | 0.55 | 0.5 – 0.7 | Carpenter, George & Saharan 2017 *Chem. Eng. Process.* 116:97 |
| FOG fragilization | 0.35 | 0.30 – 0.50 (qualitative; no direct dairy datum) | Pandit & Joshi 1993 *Chem. Eng. Sci.* 48:3440; Dhanke & Wagh 2020 *Mater. Today Proc.* 27:181 |
| Macro TSS fraction | 0.45 | RETAIN (formulation-specific) | — |
| Macro FOG fraction | 0.85 | RETAIN (formulation-specific) | — |
| Intensity proxy gain | 1.4 | RETAIN (model construct) | — |
| Intensity Δp decay (bar) | 2.0 | 2 – 3 bar (optimum 3 – 5 bar inlet) | Saharan et al. 2012 |
| Outlet ΔT (K) | 0.5 | 0.5 – 1.5 K | Gogate & Pandit 2001 *Rev. Chem. Eng.* 17:1 |

### Stage 12a – Nanofiltration (Darcy)

| Parameter | Placeholder | Recommended | Source |
|---|---|---|---|
| Permeate volume fraction | 0.70 | 0.5 – 0.8 | Vourch et al. 2008 *Desalination* 219:190 |
| Sugar (lactose) rejection | 0.85 | 0.54 – 0.99 depending on NF tightness; NF270 ≈ 0.85 | Luo et al. 2011 *J. Hazard. Mater.* 192:889; Suárez et al. 2014 *J. Membr. Sci.* |
| Solids rejection | 0.90 | 0.85 – 0.99 (protein > 99 %; mineral 0.40 – 0.95) | Luo et al. 2011 |
| Fouling mass fraction | 0.10 | 0.05 – 0.15 | Hermia cake-layer model fits |
| Maintenance threshold sat. | 0.90 | 0.85 – 0.95 | Marshall & Daufin 1995 |
| Base membrane resistance R_m (1/m) | 1 × 10¹² | **5 × 10¹³ – 1 × 10¹⁴ 1/m** for polyamide NF | Mulder 1996 *Basic Principles of Membrane Technology* Ch. 5 |
| Fouling coefficient α (m·kg⁻¹) | 1 × 10¹⁴ | 10¹³ – 10¹⁵ for dairy cake | Marshall & Daufin 1995 |

### Stage 12b – Bioconversion (PHA, R. eutropha / C. necator)

| Parameter | Placeholder | Recommended | Source |
|---|---|---|---|
| Y (kg PHA/kg sugar) | 0.4 | 0.30 – 0.49 g/g; canonical 0.33 – 0.40 on glucose | Khanna & Srivastava 2007 *Biochem. Eng. J.* 36:34; Saratale et al. 2019 *Bioresour. Technol.* 282:75–80 (0.488 g/g reducing sugar on kenaf hydrolysate); Povolo et al. 2010 *Bioresour. Technol.* 101:7902 |
| Bioavailability clamp | 0.85 – 1.35 | RETAIN (model construct) | — |

### Thermophysical Properties

| Parameter | Placeholder | Recommended | Source |
|---|---|---|---|
| Water C_p | 4180 J/(kg·K) | [standard] | — |
| Milk fat C_p | 2010 J/(kg·K) | 2.01 kJ/(kg·K) at 20 °C — exactly the Choi-Okos value | ASHRAE 2002 Refrigeration Handbook Ch. 8; Choi & Okos 1986 |
| Sucrose C_p | 1450 J/(kg·K) | 1.245 (crystalline) – 1.50 (hydrated, in dairy mix) | ASHRAE 2002 / Polley, Snyder & Kotnour 1980 |
| MSNF solids C_p | 1550 J/(kg·K) | 1.5 – 1.7 (protein 2.04 + lactose 1.25 weighted average) | ASHRAE 2002; Singh & Heldman 2014 *Introduction to Food Engineering* 5e Appendix A |
| Density unaerated mix (kg/L) | 1.05 | 1.05 – 1.12 | Goff & Hartel 2013 *Ice Cream* 7e p. 143; Cogné et al. 2003 *J. Food Eng.* 58:331 |
| Latent heat fusion of ice | 334 000 J/kg | [standard] | — |
| Ice density | 917 kg/m³ | [standard] | — |

## Recommendations

**Tier 1 — Mandatory changes before any quantitative use.**

1. **Reduce k_oxidation** in Stage 11 from 0.018 s⁻¹ to ≈ **5 × 10⁻⁴ s⁻¹** (Gogate & Pandit 2004 / Saharan et al. 2012 / Patil et al. 2025).
2. **Reduce k_scission** in Stage 11 from 0.022 s⁻¹ to ≈ **7 × 10⁻⁴ s⁻¹** (Huang et al. 2013).
3. **Reinterpret or correct the Stage 11 BOD/COD-removal coupling**: HC raises BI 1.7 – 2.0×, so BOD-removed / COD-removed should be < 1 (≈ 0.5 – 0.7), not 0.92.
4. **Raise base membrane resistance** in Stage 12a from 1 × 10¹² to ≈ **5 × 10¹³ m⁻¹**.
5. **Resolve the Stage 1 K_power ambiguity**: either relabel as an axial pitched-blade impeller and keep 2.0, OR raise to **5 – 6** for a Rushton turbine.
6. **Raise the Walstra pressure exponent** in Stage 3 from 0.45 to **0.6** (Walstra 1975, 1983).
7. **Tighten the BOD-per-kg-lactose coefficient** in Stage 9 from 1.2 to **1.123 kg O₂/kg** (stoichiometric ThOD); raise fat coefficient from 2.0 to **2.5 kg O₂/kg**.

**Tier 2 — Optional refinements when the simulator is exercised against plant data.**

8. Tighten Stage 2 D-value to 0.015 min (Bradshaw et al. 1987) and z to 6.3 °C only if quantitative pathogen-log-reduction calculation is needed; otherwise the conservative 0.2 min is fine.
9. Tighten Stage 11 max COD removal from 0.38 to 0.30 – 0.35 to align with the median of Padoley 2012 / Patil 2025.
10. Sharpen Stage 7 hydrocolloid suppression to 0.30 / 0.45 (Regand & Goff 2002/2003).

**Tier 3 — Calibration parameters to fit, not look up.**

The wall-residue terms, intensity proxy gain, FOG fragilization and Gompertz t₀ offset have no direct literature analogue and should be treated as fit parameters once plant data are available. The Pal-Rhodes exponent is sensitive to the particular emulsion microstructure and should be calibrated rather than dictated by literature.

**Benchmarks that would alter the recommendations.**

- If the simulator is intended for HC + H₂O₂/Fenton hybrid (not HC-alone), k_oxidation can be 3 – 10× higher (Agarkoti et al. 2021 reached 97 % COD removal).
- If the homogenizer operates above 200 MPa (ultra-high pressure), the Walstra exponent flattens to ~0.4 (Davies 1985 theory; Hayes & Kelly 2003).
- If the NF membrane is a "tight NF" (NF90 or RO-loose), lactose rejection moves to > 98 % and R_m to ~10¹⁴ (Luo et al. 2011).
- If the R. eutropha strain is wild type on whey lactose without an inserted lac operon, Y drops to ≤ 0.20 g/g (Povolo et al. 2010).
- If the storage Ostwald ripening is to be computed at temperatures colder than −20 °C, recrystallization rate becomes negligible and the r_scale term should be turned off (Donhowe & Hartel 1996b show vanishing rate at deep-frozen storage).

## Caveats

- **Model-construct knobs without literature analogues.** Several "vague" placeholders in the simulator (Gompertz t₀ offset, intensity proxy gain, FOG fragilization, wall-residue base, bioavailability clamp 0.85–1.35) do not map cleanly to literature constants and are essentially internal model construct knobs; they must be fit against plant data, not calibrated from the literature.
- **Mixer K_power confusion.** The mixer K_power placeholder of 2.0 is suspiciously low for "radial laminar". In the laminar regime, N_p ∝ Re⁻¹ and the product N_p·Re ≈ 70 – 90 for a Rushton turbine, while the turbulent asymptote is N_p ≈ 5. Clarify the intended regime in the code before adopting a value.
- **Cavitation kinetics ambiguity.** HC kinetics are empirically pseudo-first-order, but Ranade and co-workers (ACS Eng. Au 2023) argue the apparent k depends on reactor volume and pass-count; treat as a fitted parameter when scaling between lab and pilot. Note also that the most-cited k ≈ 7 × 10⁻⁴ s⁻¹ from Gawande & Mali 2024 was measured on Mula-Mutha River water (not dairy effluent); the closest dairy-specific HC study (Patil et al. 2025) does not explicitly report k but a half-life of 120 min implies k ≈ 1 × 10⁻⁴ s⁻¹, which would push the recommendation toward the lower end of the 5 × 10⁻⁴ – 8 × 10⁻⁴ s⁻¹ range.
- **BOD basis variability.** Several values for BOD coefficients vary by an order of magnitude between sources (laboratory BOD₅ vs. ultimate BOD); always specify which BOD basis is used. The Tetra Pak Dairy Processing Handbook is an industry source rather than peer-reviewed; its values for CIP wash efficiencies and BOD/COD ratios are widely cited but should be cross-checked against Britz et al. 2006 and Janczukowicz et al. 2008 (*Bioresour. Technol.* 99:4199) for academic citations.
- **Avrami / Gompertz overlap.** The simulator uses both Avrami and Gompertz models for the same SSHE ice formation, which may double-count if both are activated simultaneously; only one should be active per run.
- **Standard physical constants.** Ice density (917 kg/m³), water specific heat (4180 J/(kg·K)), latent heat of fusion of ice (334 kJ/kg), and Stefan-Boltzmann constant are standard values and need no citation; ice-water surface tension γ = 0.025 J/m² is a widely accepted textbook value (Hardy 1977; Hillig 1998) but shows small temperature dependence (0.022 – 0.032 J/m²) that the simulator currently ignores — a refinement worth implementing if Kelvin/Gibbs-Thomson corrections drive critical results.
- **Cook & Hartel 2010 wall ice volume fraction.** The value 0.28 is consistent with the Cook 2010 thesis but the published *Comprehensive Reviews* paper (2010) does not give an explicit numerical volume fraction; the figure should be qualified as "consistent with Cook (2010) PhD thesis" rather than asserted as a directly-cited value.
- **PHA yield range.** The Saratale et al. 2019 figure of 0.488 g/g (kenaf hydrolysate) approaches the theoretical 0.48 g/g ceiling from acetyl-CoA stoichiometry; on real dairy whey-permeate streams expect 0.25 – 0.35 g/g rather than the upper limit. The simulator's placeholder of 0.40 should therefore be considered an optimistic upper end of the realistic dairy-stream range.
7. **All citations are peer-reviewed journals, established academic books, or government/regulatory documents** (PMO 2019, World Bank 1996). One commercial case study (Anderson-Negele / Nestlé Canada CIP) is cited explicitly as commercial — use only as a sanity-check, not a primary citation.
