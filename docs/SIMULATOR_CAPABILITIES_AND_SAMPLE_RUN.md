# Ice Cream Manufacturing & Wastewater Valorization Simulator

**Capabilities overview and sample run**

---

## 1. Purpose and scope

This simulator was written to follow one batch of ice cream mix from the tank through freezing and hardening, and then—if you enable it—into the cleaning and valorization story that often matters in research proposals: CIP water, filtration, and a simple sugar-to-bioplastic step. Nothing here replaces a pilot plant, but it keeps **mass and stage ordering** honest while exposing **quality-related proxies** you can tune or replace.

- **Upstream:** Raw ingredients → **industrial chain**: preparation mix (blending only; no air) → pasteurization → homogenization → cooling PHE → ageing vat → flavor & inclusions (optional) → interface flush → freezer (aeration/overrun here) → hardening → packaging, with an optional **storage** leg after hardening. Residues from prep, ageing, and interface flush feed CIP. **Mixing** happens only in preparation; **aeration** only in the freezer.
- **Midstream:** CIP dilutes residue into wash water (TSS, BOD, COD, FOG, dissolved sugars). **`report["cip"]`** describes this effluent **before** any further treatment.
- **Downstream:** **Pre-filtration** removes a **configurable fraction** of TSS (not 100%; default ~62%). **Hydrodynamic cavitation** applies oxidation and fragmentation proxies (COD/BOD/TSS/FOG, mean molecular-weight index, bioavailability factor). **Filtration** (membrane) yields permeate and a sugar-rich retentate; retentate feeds bioplastic conversion. Default **`DefaultBioconversionModel`** scales effective yield slightly using the cavitation **bioavailability** proxy. All of this runs only when **`include_cleaning_phase=True`** and wastewater volume is positive. See [WATER_TREATMENT_CAVITATION.md](WATER_TREATMENT_CAVITATION.md) for tuning.

The **MaterialBatch** (mass, temperature, viscosity, composition) is the thread through all stages. You can swap sub-models via `MixerModelBase` and `BioconversionModelBase`, and you can fit **ice and texture** coefficients through `CrystallizationParameters` (§6) without forking the core correlations.

### 1.1 Process structure and citations (literature alignment)

The **sequence of process steps** (ingredient mixing, pasteurization, homogenization, cooling, ageing, freezing with air incorporation, hardening) is consistent with **standard descriptions of industrial ice cream manufacture** in the food and manufacturing literature. A primary reference for the **process narrative and typical equipment** (including the ordering of mixing, pasteurization, homogenization, ageing, dynamic freezing in a scraped-surface heat exchanger, and hardening) is:

> Harfoush, A., Fan, Z., Goddik, L., & Haapala, K. R. (2024). A review of ice cream manufacturing process and system improvement strategies. *Manufacturing Letters*, *41*, 170–181. [https://doi.org/10.1016/j.mfglet.2024.09.021](https://doi.org/10.1016/j.mfglet.2024.09.021)

That review summarizes **Fig. 2** (typical industrial steps: ingredient mixing → pasteurization → homogenization → aging → flavor/color addition → continuous/dynamic freezing → inclusions and packing → hardening) and discusses **pasteurization, homogenization, and dynamic freezing** as the most studied process levers for product quality. **This simulator** maps those ideas to code stages (`industrial_chain.py`, `industrial_physics.py`) and adds a **valorization** path (CIP → pre-filtration → hydrodynamic cavitation → filtration → bioplastic) not central to the review. A local PDF copy is available at `papers/icecream-01.pdf`.

| Review (Harfoush et al., typical industrial flow) | Simulator implementation |
|---------------------------------------------------|-------------------------|
| Ingredient mixing | `preparation_mix` |
| Pasteurization | `pasteurization` (+ hold / log-reduction in physics layer) |
| Homogenization | `homogenization` |
| Cooling (implicit before ageing in many plants) | `cooling_phe` |
| Aging | `ageing_vat` |
| Flavor/color before freezing (often) | `flavor_inclusions` |
| Continuous/dynamic freezing (SSHE, air) | `freezer` |
| Hardening | `hardening` |
| Inclusions & packing (plant-dependent order) | `packaging` (after hardening here) |

**Note:** The review’s Section 4 cites additional **primary studies** on pasteurization, homogenization, and **dynamic freezing** (e.g. Russell et al. on scraped-surface heat exchangers and ice crystal dynamics). This codebase uses **aggregate** correlations in `industrial_physics.py`, not a one-to-one reproduction of every cited experiment. You can still tune those correlations for a product line; see §6 below.

---

## 2. Simulator capabilities (where to plug in models)

| Area | Current default | Extensibility |
|------|-----------------|---------------|
| **Mixing / rheology** | Power-law apparent viscosity (shear, temperature, composition); power \(P = K \mu N^2 D^3\); residue = f(μ, surface area) | Implement `MixerModelBase`: your viscosity, power number, and wall residue/fouling model. |
| **CIP / wash** | Detergent-dependent wash efficiency; dilution of residue into water; BOD/COD/FOG from composition | Replace wash-efficiency and BOD/COD/FOG correlations in the CIP module. |
| **Pre-filtration** | Fractional TSS removal (`PrefiltrationConfig.tss_removal_fraction`, capped below 100%); volume unchanged | Swap correlations or call `run_prefiltration` with your config from `run_full_cycle` if you fork the pipeline. |
| **Hydrodynamic cavitation** | Intensity from ΔP/P_in; pseudo-first-order oxidation + chain-scission proxies; bioavailability factor | Tune `CavitationConfig` or replace `cavitation.py`; see [WATER_TREATMENT_CAVITATION.md](WATER_TREATMENT_CAVITATION.md). |
| **Filtration** | Darcy-style resistance increasing with accumulated mass; fixed permeate/retentate split and sugar rejection | Replace Darcy and separation/rejection logic in the filtration module. |
| **Bioplastic** | Linear yield: mass_PHA = mass_sugar × effective yield (base coefficient × bioavailability clamp); pluggable model | Implement `BioconversionModelBase`: e.g. Monod kinetics, Ralstonia eutropha–style growth, or ML yield. |
| **Ice / SSHE / storage** | Wall–bulk populations, Gompertz & Avrami fractions, barrel and storage ripening, Kelvin, hardness proxy | Pass a `CrystallizationParameters` instance (or load JSON/YAML); see §6. |

Additional features (aligned with industrial practice):

- **Air overrun** for ice cream volume.
- **Interface flush** (start-of-run discard) as operational loss fed into the same CIP stream.
- **Optional cleaning phase** (can skip CIP, pre-filtration, cavitation, filtration, and bioconversion for “production only” runs).
- **Filter health**: saturation and a maintenance flag when saturation > 90%.
- **Mass balance check** and a **typed report** (`MaterialBatchCycleReport`) for post-processing and validation.

---

## 3. Sample parameters and process outcome by stage

Below is one **full run** with fixed inputs. All numbers are from the current default models and are for illustration only; replacing sub-models will change the outputs.

### 3.1 Global inputs (sample)

| Parameter | Value | Unit |
|-----------|--------|------|
| Raw materials (total) | 200 | kg |
| — milk | 100 | kg |
| — cream | 30 | kg |
| — sugar | 25 | kg |
| — stabilizers (hydrocolloids) | 1.65 | kg |
| — emulsifiers | 0.35 | kg |
| — water | 43 | kg |
| Tank surface area | 10 | m² |
| CIP water volume | 80 | L |
| Air overrun (requested) | 0.5 | — |
| Interface flush | 5.0 | L |
| Include cleaning phase | Yes | — |
| Homogenization pressure | 200 | bar |
| Pasteurization hold time | 15 | s |
| Ageing stirrer on | Yes | — |
| Jacket flow (ageing) | 20 | L/min |
| Preparation RPM / time | 60 / 300 | rpm / s |
| SSHE: coolant T, residence, dasher, barrel | 253.15 / 45 / 55 / 0.15 | K / s / rpm / m |
| Flavor / inclusions | 0 / 0 | kg |
| Package count | 1 | — |
| Bioplastic yield coefficient | 0.4 | g PHA / g sugar |

With **`include_cleaning_phase=True`**, the default bioconversion model applies a small **cavitation bioavailability** scaling, so the **reported** effective yield coefficient in `report["bioconversion"]` may differ slightly from 0.4 (see §3.7).

---

### 3.2 Stage 1 — Upstream (industrial chain)

**Industrial chain:** Preparation mix → pasteurization (with hold and lethality metrics) → homogenization (fat globule d32) → two-stage cooling → ageing vat (fat crystallinity) → optional flavor/inclusions → interface flush → continuous freezer (effective overrun, ice crystal mean size, dasher power) → hardening (hardness/melt proxies) → packaging. Combined residue (prep + ageing + interface flush) goes to CIP. See **`report["quality"]`** and **`report["industrial_chain"]["stages_detail"]`** for per-stage outputs.

**Inputs (conceptual):** Raw materials, tank surface area, homogenization pressure, pasteurization hold, stirrer, jacket flow, preparation RPM/time, SSHE parameters, packaging count, flavor/inclusion masses.

**Outputs (illustrative — run `python run.py` for current numbers):** Product mass after packaging, ice cream volume, residue, mixing power, **`quality`** (e.g. log₁₀ pathogen reduction, d32, crystallinity, ice crystal µm, effective overrun, dasher power, hardness/melt proxies), mixer efficiency (product / total mass including additives).

**Extend:** `MixerModelBase` for preparation rheology; physics and correlations are documented in `industrial_physics.py`.

---

### 3.3 Stage 2 — CIP (clean-in-place) & wastewater generation

**Role:** Dilute tank residue + interface flush into cleaning water; produce one wastewater stream (no longer “ice cream”) with TSS, dissolved sugars, BOD, COD, FOG.

**Inputs (conceptual):** Combined residue mass (tank residue + interface flush), composition, CIP water volume, water temperature, detergent type.

**Outputs (sample — run `python run.py` for current numbers):**

| Quantity | Value | Unit |
|----------|--------|------|
| Wastewater volume | 85.14 | L |
| Wastewater mass | 85.14 | kg |
| Dissolved sugar | 0.64 | kg |
| TSS | 47 387 | mg/L |
| BOD | 17 989 | mg/L |
| FOG | 4 467 | mg/L |

**Report key:** `report["cip"]` — values above are **after CIP only** (before pre-filtration and cavitation).

**Plug-in:** Wash efficiency (detergent/kinetics), BOD/COD/FOG correlations.

---

### 3.4 Stage 3 — Pre-filtration (coarse TSS removal)

**Role:** Remove a **fraction** of suspended solids (TSS) to protect downstream cavitation and membrane units. Default removal is **not** 100%: a tunable fraction of TSS mass is removed; volume and dissolved loads on the main stream are unchanged except for the mass tied to removed solids.

**Inputs (conceptual):** Wastewater from CIP; `PrefiltrationConfig.tss_removal_fraction`.

**Outputs (sample):**

| Quantity | Value | Unit |
|----------|--------|------|
| TSS before | 47 387 | mg/L |
| TSS after | 18 007 | mg/L |
| TSS removed (mass) | 2.50 | kg |

**Report key:** `report["prefiltration"]`.

**Plug-in:** Replace or wrap `run_prefiltration` / screen efficiency vs. particle size if you extend the model.

---

### 3.5 Stage 4 — Hydrodynamic cavitation

**Role:** Proxy for Venturi/orifice-style HC: partial COD/BOD change (oxidation path), mechanical fragmentation of a macro-organic pool (TSS/FOG proxy), optional shift in mean “molecular weight” index, and a **bioavailability factor** passed into default bioconversion.

**Inputs (conceptual):** Pre-filtration effluent; `CavitationConfig` (inlet pressure, pressure drop, residence time, kinetic caps).

**Outputs (sample):**

| Quantity | Value | Unit |
|----------|--------|------|
| COD before / after | 26 983 / 24 123 | mg/L |
| BOD before / after | 17 989 / 16 139 | mg/L |
| TSS before / after | 18 007 / 16 994 | mg/L |
| FOG before / after | 4 467 / 4 004 | mg/L |
| Mean MW index (after) | 0.819 | — |
| Bioavailability factor | 1.038 | — |
| Energy proxy | 4.05 | kWh |

**Report keys:** `report["hydrodynamic_cavitation"]`; membrane feed snapshot: `report["wastewater_to_nanofiltration"]` (TSS, COD, BOD, FOG at NF inlet).

**Plug-in:** Tune `CavitationConfig` or replace `cavitation.py`; see [WATER_TREATMENT_CAVITATION.md](WATER_TREATMENT_CAVITATION.md).

**References:** Gogate & Pandit (2004), *Advances in Environmental Research*, Parts I–II — ambient oxidation technologies for wastewater (including cavitation) and hybrid methods; Gogate & Pandit (2000), *AIChE Journal* — engineering design of hydrodynamic cavitation reactors. Full bibliographic entries and DOIs are in [WATER_TREATMENT_CAVITATION.md](WATER_TREATMENT_CAVITATION.md).

---

### 3.6 Stage 5 — Filtration (membrane, Darcy-style fouling)

**Role:** Split **post-cavitation** wastewater into permeate (clean water) and retentate (concentrated sugar/solids). Resistance increases with accumulated mass; filter health (saturation) is tracked; maintenance is flagged above a threshold (e.g. 90%).

**Inputs (conceptual):** Wastewater stream after pre-filtration and cavitation (volume, mass, TSS, dissolved sugar, BOD, COD, FOG), filter pore size, membrane area, initial filter state.

**Outputs (sample):**

| Quantity | Value | Unit |
|----------|--------|------|
| Permeate volume | 59.60 | L |
| Retentate mass | 24.79 | kg |
| Retentate sugar (for bioplastic) | 0.55 | kg |
| Filter saturation | 4.96 | % |
| Maintenance required | No | — |

**Plug-in:** Darcy resistance vs. accumulated mass, permeate/retentate split, rejection of sugar/solids.

---

### 3.7 Stage 6 — Bioconversion (sugar → bioplastic)

**Role:** Convert sugar in the retentate to bioplastic (e.g. PHA) via an effective yield coefficient. **`DefaultBioconversionModel`** combines the nominal yield with the cavitation **bioavailability** proxy (clamped), so the reported yield coefficient may differ slightly from the input `bioplastic_yield_coefficient`.

**Inputs (conceptual):** Retentate mass and sugar mass, yield coefficient (or full kinetic/model parameters); optional `bioavailability_factor` from cavitation when using the default model.

**Outputs (sample):**

| Quantity | Value | Unit |
|----------|--------|------|
| Bioplastic (PHA) produced | 0.227 | kg |
| Sugar consumed | 0.546 | kg |
| Effective yield coefficient (reported) | 0.415 | g PHA / g sugar |
| Cavitation bioavailability factor | 1.038 | — |
| Yield from sugar | 41.5 | % |
| Yield from total raw input | 0.11 | % |

**Plug-in:** Growth/yield kinetics (e.g. Monod, R. eutropha), or ML-based yield model.

---

### 3.8 Overall efficiency (sample run)

| Quantity | Value | Unit |
|----------|--------|------|
| Product recovery (product / raw input) | 97.21 | % |
| Bioplastic per tonne raw input | 1.13 | kg/tonne |
| Mass balance closed | Yes | — |

---

## 4. How to run and extend

- **Run one full cycle (default parameters):**  
  `python run.py` (from project root) or `python -m icecream_simulator.run_full_cycle`
- **Run with your parameters:**  
  Pass the usual arguments to `run_full_cycle` (materials, tank area, CIP water, SSHE settings, packaging, etc.). For ice and texture calibration, add `crystallization_parameters=...` or load from JSON/YAML (§6). Wastewater pretreatment (pre-filtration, cavitation) is on by default when `include_cleaning_phase=True`; inspect `report["prefiltration"]`, `report["hydrodynamic_cavitation"]`, and `report["wastewater_to_nanofiltration"]`.
- **Replace mixing or bioconversion:**  
  Implement `MixerModelBase` or `BioconversionModelBase` and pass instances into `run_full_cycle`.
- **Process structure and literature:**  
  See §1.1 and the main [README](../README.md).

The README is the short entry point; §5–§6 here go deeper on presets and calibration.

---

## 5. Literature presets and scope vs. the papers

### 5.1 Coded presets (`literature_recipes.py`)

The simulator ships **named batches** (typically **200 kg** total `RawMaterials`) tied to PDFs in `papers/` and to **tables or sections** in those papers. Full **DOIs** for each PDF are listed in [`papers/README.md`](../papers/README.md) and in `literature_recipes.py` module docstrings. Use `run_full_cycle(literature_preset_id="…")` or `python run.py --literature-suite` to exercise **all** presets in one go.

| Preset id (examples) | Paper (PDF) | Anchor |
|----------------------|-------------|--------|
| `HARFOUSH_2024_BASELINE` | `icecream-01.pdf` | Process flow / Fig. 2 narrative |
| `GIUDICI_2021_INDUSTRIAL`, `GIUDICI_2021_ARTISANAL` | `icecream-02.pdf` | Table 2 text (composition bounds) |
| `KONSTANTAS_2019_*` (four variants) | `icecream-03.pdf` | Table 2 (kg/kg ice cream inventory); chocolate presets use `cocoa_powder_kg` |
| `COOK_HARTEL_CRYSTALLIZATION_REFERENCE` | `icecream-04.pdf` | Cook & Hartel (2010) crystallization review; use freezer quality fields |
| `WARI_ZHU_2019_SCHEDULING_REFERENCE` | `icecream-05.pdf` | Scheduling (no formulation) |

**Konstantas Table 2** lists **life-cycle inventory** per kg of product (including upstream milk for cream and skim), not a single closed **mix recipe**. The coded batches are **illustrative** mappings for process simulation; full LCA mass closure is **out of scope** for this codebase.

### 5.2 Research-grade crystallization, emulsion aids, and storage

| Topic | Literature basis | Implementation (`industrial_physics.py`, chain) |
|-------|------------------|------------------------------------------------|
| **Hydrocolloid vs emulsifier** | Distinct roles (stabilisation vs interface) | `RawMaterials.stabilizers` (hydrocolloids) and `emulsifiers_kg`; mass fractions in batch metadata drive viscosity and ice physics |
| **Wall vs bulk ice** | Cook & Hartel (SSHE nucleation vs growth) | `ice_crystal_wall_um_sshe`, `ice_crystal_bulk_um_sshe`, volume mean `ice_crystal_volume_mean_um` with tunable `volume_fraction_wall_ice` |
| **Gompertz vs Avrami kinetics** | Giudici (Gompertz); Avrami–Erofeev (phase transformation) | Both reported; `frozen_water_fraction_kinetic_blend` is a **weighted** mix (default 50/50); weights live in `CrystallizationParameters` |
| **Barrel recrystallization** | Ostwald ripening in freezer | `ice_crystal_mean_um_after_recrystallization` on volume-mean diameter |
| **Post-hardening storage ripening** | Hartel / Livney | Optional `storage_time_s` / `storage_temp_K` → `storage_recrystallization` stage updates mean size, Kelvin ΔT, hardness |
| **Initial freezing point** | Colligative trend | `initial_freezing_point_mix_C` (empirical from sugar) |
| **Kelvin (Gibbs–Thomson)** | Small-crystal equilibrium | `kelvin_freezing_point_depression_for_mean_crystal_K` on current mean diameter |
| **Scheduling, retail LCA** | Wari; Konstantas | **Not modeled** (out of scope) |

Use `run_full_cycle(..., volume_fraction_wall_ice=0.28, storage_time_s=72*3600, storage_temp_K=248.15)` for distribution-storage studies.

---

## 6. Calibration files (ice physics and texture)

If you are doing serious work—fitting to DSC, laser diffraction, or sensory panels—you will want to stop treating the built-in numbers as universal truths. The simulator is set up for that: every coefficient that feeds the **freezer**, **hardening**, **storage**, and related **hardness / Kelvin** outputs lives in a single Pydantic model, `CrystallizationParameters`, in `crystallization_parameters.py`. The defaults are exactly what the code used before this object existed; passing `None` is the same as passing the default instance.

**Practical workflow:**

1. Copy `examples/crystallization_parameters_example.json` and give it a meaningful `name` (for example the SKU or plant line you are calibrating).
2. Change only the fields your data can constrain. Everything you omit stays at the library default—there is no need to paste a hundred numbers by hand.
3. Load the file and pass it into `run_full_cycle`:

```python
from icecream_simulator import load_crystallization_parameters_from_json, run_full_cycle

params = load_crystallization_parameters_from_json("my_line.json")
report = run_full_cycle(crystallization_parameters=params, include_cleaning_phase=False)
```

JSON works out of the box. For YAML, install the optional extra (`pip install ".[config]"` or add `pyyaml`) and use `load_crystallization_parameters` or `load_crystallization_parameters_from_yaml`.

**Reproducibility:** Each full-cycle report includes `inputs["crystallization_parameters"]`, a plain dictionary snapshot of the parameter set used for that run. That makes it straightforward to archive a simulation next to the experimental batch it was meant to match.

**What this does not replace:** Pasteurisation lethality, homogeniser geometry, bioconversion kinetics, and **wastewater** pre-filtration / cavitation parameters are still separate knobs (or pluggable modules). The crystallization file is intentionally scoped to **ice and texture** on the path from SSHE through storage.
