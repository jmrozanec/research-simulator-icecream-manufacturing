# Simplified Ice Cream + Bioplastic Pipeline

**Version:** post-refactor consolidated model (single code path).  
**Scope:** One batch mass balance: recipe → salable ice-cream mass & volume → tank residue → optional CIP washwater → membrane retentate → PHA-style bioplastic. No multi-stage industrial chain, no rheological ODEs, no crystallization kinetics.

**Math in this file:** Display and inline math use `$` / `$$` so GitHub and most Markdown previews can render it. If your viewer still shows raw code, use a KaTeX/MathJax-capable preview or open the PDF/HTML export from the same source.

---

## 1. Purpose and flow

The simulator answers: *Given a recipe and a few process knobs, how much product leaves the line, how much ends up as residue that is washed off in CIP, what kind of wastewater results, and how much bioplastic can we attribute to the sugar retained after nanofiltration?*

Execution order in `icecream_simulator.pipeline.run_full_cycle`:

1. **Production split** — total batch mass is divided between product and residue using a single residue fraction $\varphi$.  
2. **Ice-cream volume (reporting only)** — nominal litre capacity from product mass, mix density, and air overrun.  
3. **CIP** — residue is transferred into wash water with detergent-dependent efficiency; TSS, BOD, COD, FOG are inferred from composition.  
4. **Prefiltration** — multiplicative reduction of TSS.  
5. **Hydrodynamic cavitation (lumped)** — pressure-based “intensity” trims BOD/COD and raises a **bioavailability** multiplier for fermentation.  
6. **Filtration** — fixed permeate/retentate split and sugar/solids partitioning; membrane fouling state is updated for reporting.  
7. **Bioconversion** — `PHA mass = yield × bioavailability × sugar in retentate`.

If cleaning is disabled, steps 3–5 receive an empty wastewater object; filtration and bioconversion still run on zero flow (non-physical but convenient for “product-only” API consistency).

---

## 2. Assumptions (explicit)

| Topic | Assumption |
|--------|------------|
| Geometry & mixing | All preparation, pasteurisation, ageing, freezing, hardening, and packaging are **collapsed** into one effective **product mass** $M_{\mathrm{prod}} = (1-\varphi)\,M_{\mathrm{in}}$. |
| Composition | Mass fractions $(w_f,w_s,w_w,w_x)$ come **only** from **raw materials** (milk fat %, cream fat %, MSNF, etc.). Optional flavor syrup and particulates add to **total mass** $M_{\mathrm{in}}$ but **do not** change $(w_f,w_s,w_w,w_x)$ unless the recipe is encoded purely in `RawMaterials`. |
| Residue | Wall residue has the **same composition** as the bulk mix (the fractions above). |
| Wash | Single-pass CIP: fraction $\varepsilon$ of residue enters water; no multi-rinse, no detergent mass balance. |
| Cavitation | One **lumped** intensity from inlet/throat pressure; BOD/COD removal capped; bioavailability is $1 + \kappa I$ with cap implied by chosen constants. |
| Membrane | Constant volume split and constant sugar/solids rejection; **no** iterative flux solve. |
| Bioplastic | **Linear yield**; no Monod kinetics, no maintenance, no by-product mass. |

All numeric defaults live in `constants.py` for calibration.

---

## 3. Equation set (eleven explicit relations; ~10 conceptual steps)

Symbols: $M_{\mathrm{raw}} = \sum$ raw ingredient masses; $M_{\mathrm{add}}$ = flavor + inclusions; $M_{\mathrm{in}} = M_{\mathrm{raw}} + M_{\mathrm{add}}$. Milk MSNF and fat contributions use fixed industry-typical factors (see code).

**(1) Total batch mass**

$$
M_{\mathrm{in}} = M_{\mathrm{raw}} + M_{\mathrm{add}}.
$$

**(2) Composition from raw materials**

Let $m_f, m_s, m_w, m_x$ be fat, sugar, “free” water, and other solids mass in the raw recipe (egg yolk and vanilla extract split by fixed factors). With $M_{\mathrm{raw}}=\sum m_\cdot$,

$$
w_f=\frac{m_f}{M_{\mathrm{raw}}},\quad w_s=\frac{m_s}{M_{\mathrm{raw}}},\quad w_w=\frac{m_w}{M_{\mathrm{raw}}},\quad w_x=\frac{m_x}{M_{\mathrm{raw}}}.
$$

**(3) Product vs residue**

$$
M_{\mathrm{res}} = \varphi\, M_{\mathrm{in}},\qquad M_{\mathrm{prod}} = M_{\mathrm{in}} - M_{\mathrm{res}} = (1-\varphi)\,M_{\mathrm{in}}.
$$

**(4) Ice-cream volume (reporting)**

With liquid density $\rho$ and air overrun $OR$ (volume fraction of air relative to liquid),

$$
V_{\mathrm{ice}} = \frac{M_{\mathrm{prod}}}{\rho}\,(1 + OR).
$$

**(5) CIP — mass transferred to water**

Wash efficiency $\varepsilon = f_{\mathrm{wash}}(\text{detergent})$.

$$
m_{\mathrm{trans}} = \varepsilon\, M_{\mathrm{res}}.
$$

**(6) Washwater volume & TSS**

Water mass $m_{\mathrm{H_2O}} = \rho_w V_{\mathrm{wash}}$. Total liquid volume (approx. ideal mixing):

$$
V_{\mathrm{ww}} = V_{\mathrm{wash}} + \frac{m_{\mathrm{trans}}}{\rho_w}.
$$

Dissolved sugar $m_{\mathrm{sugar,ww}} = m_{\mathrm{trans}}\, w_s$. Non-water residue mass approximated as $m_{\mathrm{trans}}(1-w_w)$ drives

$$
\mathrm{TSS\,[mg/L]} = \frac{m_{\mathrm{trans}}(1-w_w)}{V_{\mathrm{ww}}}\times 10^6.
$$

**(7) BOD, COD, FOG**

$$
\mathrm{BOD} = a_s\, m_{\mathrm{sugar,ww}} + a_f\, m_{\mathrm{trans}}\, w_f,\quad \mathrm{COD} = r_{\mathrm{CB}}\,\mathrm{BOD},\quad \mathrm{FOG} \propto \frac{m_{\mathrm{trans}}\, w_f}{V_{\mathrm{ww}}}.
$$

Coefficients $a_s,a_f,r_{\mathrm{CB}}$ are `constants.py` entries.

**(8) Prefiltration**

$$
\mathrm{TSS}' = (1-r_{\mathrm{TSS}})\,\mathrm{TSS}.
$$

**(9) Cavitation**

Pressure-drop intensity $I=\min\bigl(1,\;(p_{\mathrm{in}}-p_{\mathrm{th}})/p_{\mathrm{ref}}\bigr)$.

$$
\mathrm{BOD}' = (1-f_{\mathrm{BOD}} I)\,\mathrm{BOD},\quad \mathrm{COD}' = (1-f_{\mathrm{COD}} I)\,\mathrm{COD},\quad b = 1 + \kappa I
$$

with caps $f_{\mathrm{BOD}},f_{\mathrm{COD}},\kappa$ from configuration. Factor $b$ is the **bioavailability** applied in bioconversion.

**(10) Membrane split**

Volume (and mass) fractions $\phi_p$ permeate / $\phi_r=1-\phi_p$ retentate.

$$
m_{\mathrm{sugar,R}} = \chi\, m_{\mathrm{sugar,ww}},\quad m_{\mathrm{solids,R}} = \chi_s\,(\mathrm{TSS}\cdot 10^{-6}\,V_{\mathrm{ww}}).
$$

Fouling accumulator receives a fixed fraction of retentate mass for saturation reporting (Darcy resistance is algebraic, not solved per flux).

**(11) Bioplastic**

Yield $Y$ (kg PHA per kg sugar) and bioavailability $b$:

$$
m_{\mathrm{PHA}} = Y\, b\, m_{\mathrm{sugar,R}}.
$$

**(12) Mass check (recipe closure)**

Neglecting wash water as *external* to the dairy mass balance,

$$
M_{\mathrm{in}} \approx M_{\mathrm{prod}} + M_{\mathrm{res}}\quad\text{(tolerance } \pm \delta M\text{).}
$$

Formulas (1)–(4) + (5)–(11) + (12) are the **complete** mathematical description implemented; **(8)**–**(9)** may be skipped when cleaning is off (empty stream).

---

## 4. References, equation provenance, and parameter sources

### 4.1 Core bibliography (PDF set + essentials)

Use these tags in the rest of this section and in `constants.py` comments.

| Tag | Source |
|-----|--------|
| **[H24]** | Harfoush, Y., et al. (2024). *Manufacturing Letters* **41**, 170–181. https://doi.org/10.1016/j.mfglet.2024.09.021 (`icecream-01.pdf`). |
| **[G21]** | Giudici, A.M., et al. (2021). *Foods* **10**(2), 334. https://doi.org/10.3390/foods10020334 (`icecream-02.pdf`). |
| **[K19]** | Konstantas, A., et al. (2019). *Journal of Cleaner Production* **209**, 259–272. https://doi.org/10.1016/j.jclepro.2018.10.237 (`icecream-03.pdf`). |
| **[CH10]** | Cook, R.L., & Hartel, R.W. (2010). Ice crystallization in ice cream. *Compr. Rev. Food Sci. Food Saf.* **9**(2), 189–217. https://doi.org/10.1111/j.1541-4337.2009.00101.x (`icecream-04.pdf`). |
| **[WZ19]** | Wari, Z., & Zhu, Y. (2019). *Int. J. Prod. Res.* **57**(21), 6648–6664. https://doi.org/10.1080/00207543.2019.1571250 (`icecream-05.pdf`). |
| **[USDA]** | U.S. Department of Agriculture, FoodData Central — fluid milk (~3.25–4% fat) and cream fat levels used for recipe accounting. https://fdc.nal.usda.gov/ |
| **[M14]** | Tchobanoglous, G., et al. *Wastewater Engineering: Treatment and Resource Recovery* (5th ed., McGraw-Hill). Organic load and typical COD/BOD behaviour. |
| **[PHE]** | Green, D.W., & Perry, R.H. *Perry’s Chemical Engineers’ Handbook* (8th ed., McGraw-Hill). Hold-up, heel volumes, and batch emptying losses. |

**Important.** The five ice-cream PDFs ground **recipe structure, environmental framing, and product-side physics**. Many **wastewater coefficients** (BOD multipliers, membrane splits, cavitation removal caps) are **not** copied from those papers; they follow **[M14]**-style stoichiometry and **engineering placeholders** that you should **replace with site-specific or pilot data**, in the spirit of **[K19]** life-cycle inventory practice.

---

### 4.2 Formula-to-literature map

| Eq. | What it is | Primary citations | Notes |
|-----|------------|-------------------|--------|
| (1) | Batch mass closure with additives | [H24], [G21], [K19] | Same additive accounting as formulation tables / LCI system boundary. |
| (2) | Mass fractions from recipe | [G21], [K19], [USDA] | Milk/cream fat & MSNF are **commodity defaults**; papers give **recipe totals** to cross-check. |
| (3) | Product vs residue split ($\varphi$) | [PHE], [WZ19], [K19], [H24] | **$\varphi$ is not** a universal constant from one paper. It **lumps** heel, film, and handling loss. **Good estimate:** calibrate from **plant mass balance** or pilot; **1–5 %** of batch mass is a **typical order of magnitude** for viscous dairy heel ([PHE] emptying/hold-up; [WZ19] motivates systematic **throughput vs loss** budgeting; [K19] for **waste mass** reporting). Default **2 %** = mid-range **illustrative** value. |
| (4) | Volume from mass, $\rho$, overrun | [CH10], [G21] | Overrun and mix density are core ice-cream engineering; simplified to one $\rho$ and scalar $OR$. |
| (5)–CIP wash | Mass transferred to water ($\varepsilon$) | [K19], [M14] | **Mechanism**: CIP + dilution mass balance; **$\varepsilon$** from CIP chemistry & soil — **calibrate** (not fixed in [H24]). |
| (6)–(7) | TSS, BOD, COD, FOG from composition | [M14], [K19] | **Correlation form**: organic load from sugar & fat; ratios align with **[M14]** guidance; **[K19]** motivates **characterizing** dairy-derived effluent. |
| (8) | TSS screening | [M14] | Primary removal fraction is **equipment-specific**. |
| (9) | Cavitation intensity & trims | [M14] + HC pilot literature | Lumped; **pressures/caps** illustrative — tune to **your** hydrodynamic cavitation pilot. |
| (10) | Membrane split & rejection | [M14], membrane datasheets | Fixed $\phi_p,\chi$ are **not** universal; **NF** lactose/sugar retention varies by membrane and $\Delta P$. |
| (11) | Linear PHA yield | Bioprocess reviews; [K19] narrative | **$Y \approx 0.3$–0.5** appears in many *C. necator* / mixed-culture reviews **per g substrate** under ideal lab conditions; **calibrate** to strain and retentate quality. **[K19]** supports **valorization** of co-product streams, not a single global $Y$. |
| (12) | Recipe mass check | [H24], [K19] | Closing mass around product + residue matches **integrated** simulation / LCI habit. |

---

### 4.3 Constants in `constants.py` (quick lookup)

| Constant / group | Default role | Primary citation(s) |
|------------------|--------------|---------------------|
| `MILK_FAT_FRACTION`, `CREAM_FAT_FRACTION`, `MILK_MSNF_FRACTION` | Compositional accounting | [USDA]; recipes in [G21], [K19] |
| `EGG_YOLK_*`, `VANILLA_EXTRACT_*` | Optional inclusions | [K19]-style formulations |
| `DEFAULT_RESIDUE_MASS_FRACTION` $\varphi$ | Lumped wall loss | [PHE] hold-up; [WZ19] loss budgeting; **calibrate** [K19] |
| `RHO_MIX_KG_L` | Mix density for volume | [CH10] order of magnitude |
| `WASH_EFFICIENCY`, `CIP_*` | CIP dilution | Operations; **calibrate** — concept [K19] WW |
| `BOD_*`, `COD_TO_BOD_RATIO`, `WASTEWATER_TSS_SUGAR_FRACTION` | Organic load correlation | [M14] |
| `TSS_REMOVAL_FRACTION` | Screen | [M14]; equipment spec |
| `CAVITATION_*` | HC lumped model | Pilot literature; **calibrate** |
| `PERMEATE_*`, `SUGAR_*`, `FILTER_*` | Membrane + fouling sketch | [M14]; manufacturer data |
| `DEFAULT_YIELD_COEFFICIENT` | PHA linear yield | Bioprocess literature; **calibrate**; motivation [K19] |
| `DEFAULT_RAW_MATERIALS_KG` | Demo batch | Scale comparable to [G21]/[H24]-class examples |

---

## 5. Code map (after simplification)

| Module | Role |
|--------|------|
| `constants.py` | All tunable scalars (efficiencies, splits, coefficients). |
| `domain.py` | Pydantic types: `RawMaterials`, streams, report shell. |
| `pipeline.py` | `run_full_cycle`, literature presets, `print_report`. |
| `__init__.py` | Public exports only. |

Removed: multi-stage `industrial_chain`, `industrial_physics`, `mixer` rheology stack, standalone `cip`/`filtration`/… modules, large `literature_recipes` table, crystallization parameter packs, and tests tied to deleted physics.

---

## 6. Running

```bash
pip install -e .
python run.py
python run.py --preset GIUDICI_2021_INDUSTRIAL
pytest tests/test_pipeline.py -q
```

Optional dashboard: `pip install streamlit` then `streamlit run examples/dashboard.py`.

---

*End of report (≈3 pages when printed from this Markdown).*
