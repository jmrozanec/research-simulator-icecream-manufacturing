# Ice Cream Manufacturing & Wastewater Valorization Simulator

**Capabilities overview and sample run (Pipeline 2: MaterialBatch)**  
*For research groups developing physical and chemical sub-models*

---

## 1. Purpose and scope

The simulator models an **integrated ice cream production and wastewater valorization** chain in a single digital twin:

- **Upstream:** Raw ingredients → mixing (rheology, power, residue) → product to freezer and operational losses.
- **Midstream:** Clean-in-place (CIP) turns tank residue and interface flush into a wastewater stream (TSS, BOD, FOG, dissolved sugars).
- **Downstream:** Membrane filtration splits wastewater into permeate (clean water) and retentate (concentrated sugar/solids); retentate feeds a sugar-to-bioplastic conversion (e.g. PHA).

The **MaterialBatch** object (mass, temperature, viscosity, composition: fat/sugar/water/solids, and later COD/BOD) is the central data structure and passes through every stage. The code is modular and **extensible**: default correlations can be replaced by your own **physics-based or data-driven models** at clearly marked plug-in points, without changing the overall flow or duplicating phases.

---

## 2. Simulator capabilities (where to plug in models)

| Area | Current default | Extensibility |
|------|-----------------|---------------|
| **Mixing / rheology** | Power-law apparent viscosity (shear, temperature, composition); power \(P = K \mu N^2 D^3\); residue = f(μ, surface area) | Implement `MixerModelBase`: your viscosity, power number, and wall residue/fouling model. |
| **CIP / wash** | Detergent-dependent wash efficiency; dilution of residue into water; BOD/COD/FOG from composition | Replace wash-efficiency and BOD/COD/FOG correlations in the CIP module. |
| **Filtration** | Darcy-style resistance increasing with accumulated mass; fixed permeate/retentate split and sugar rejection | Replace Darcy and separation/rejection logic in the filtration module. |
| **Bioplastic** | Linear yield: mass_PHA = mass_sugar × yield_coefficient (e.g. 0.4) | Implement `BioconversionModelBase`: e.g. Monod kinetics, Ralstonia eutropha–style growth, or ML yield. |

Additional features (aligned with industrial practice):

- **Air overrun** for ice cream volume.
- **Interface flush** (start-of-run discard) as operational loss fed into the same CIP stream.
- **Optional cleaning phase** (can skip CIP/filtration/bioconversion for “production only” runs).
- **Filter health**: saturation and a maintenance flag when saturation > 90%.
- **Mass balance check** and a **typed report** (`MaterialBatchCycleReport`) for post-processing and validation.

---

## 3. Sample parameters and process outcome by stage

Below is one **full run** of the second pipeline with fixed inputs. All numbers are from the current default models and are for illustration only; replacing sub-models will change the outputs.

### 3.1 Global inputs (sample)

| Parameter | Value | Unit |
|-----------|--------|------|
| Raw materials (total) | 200 | kg |
| — milk | 100 | kg |
| — cream | 30 | kg |
| — sugar | 25 | kg |
| — stabilizers | 2 | kg |
| — water | 43 | kg |
| Tank surface area | 10 | m² |
| CIP water volume | 80 | L |
| Air overrun | 0.5 | — |
| Interface flush | 5.0 | L |
| Include cleaning phase | Yes | — |
| Mixing temperature | 278 | K |
| Mixing time | 300 | s |
| Mixer RPM | 60 | rpm |
| Bioplastic yield coefficient | 0.4 | g PHA / g sugar |

---

### 3.2 Stage 1 — Mixer (rheology & residue)

**Role:** Mix raw ingredients; compute apparent viscosity and power draw; split output into product (to freezer) and tank residue (for CIP). Interface flush is applied here as additional loss (same loss path as residue).

**Inputs (conceptual):** Raw materials, tank surface area, RPM, mixing time, initial temperature.

**Outputs (sample):**

| Quantity | Value | Unit |
|----------|--------|------|
| Product to freezer | 194.34 | kg |
| Ice cream volume (with overrun) | 277.62 | L |
| Tank residue | 0.41 | kg |
| Interface flush (mass) | 5.25 | kg |
| Mixing power | 0.17 | W |
| Apparent viscosity | 0.682 | Pa·s |
| Thermal conductivity | 0.443 | W/(m·K) |
| Specific heat | 3608 | J/(kg·K) |
| Mixer efficiency (product / input) | 97.17 | % |

**Plug-in:** Viscosity law, power number \(P = K \mu N^2 D^3\), residue/fouling as a function of μ and geometry.

---

### 3.3 Stage 2 — CIP (clean-in-place) & wastewater generation

**Role:** Dilute tank residue + interface flush into cleaning water; produce one wastewater stream (no longer “ice cream”) with TSS, dissolved sugars, BOD, COD, FOG.

**Inputs (conceptual):** Combined residue mass (tank residue + interface flush), composition, CIP water volume, water temperature, detergent type.

**Outputs (sample):**

| Quantity | Value | Unit |
|----------|--------|------|
| Wastewater volume | 85.21 | L |
| Wastewater mass | 85.21 | kg |
| Dissolved sugar | 0.65 | kg |
| TSS | 47 995 | mg/L |
| BOD | 18 220 | mg/L |
| FOG | 4 524 | mg/L |

**Plug-in:** Wash efficiency (detergent/kinetics), BOD/COD/FOG correlations.

---

### 3.4 Stage 3 — Filtration (membrane, Darcy-style fouling)

**Role:** Split wastewater into permeate (clean water) and retentate (concentrated sugar/solids). Resistance increases with accumulated mass; filter health (saturation) is tracked; maintenance is flagged above a threshold (e.g. 90%).

**Inputs (conceptual):** Wastewater stream (volume, mass, TSS, dissolved sugar, BOD, FOG), filter pore size, membrane area, initial filter state.

**Outputs (sample):**

| Quantity | Value | Unit |
|----------|--------|------|
| Permeate volume | 59.65 | L |
| Retentate mass | 25.56 | kg |
| Retentate sugar (for bioplastic) | 0.55 | kg |
| Filter saturation | 5.11 | % |
| Maintenance required | No | — |

**Plug-in:** Darcy resistance vs. accumulated mass, permeate/retentate split, rejection of sugar/solids.

---

### 3.5 Stage 4 — Bioconversion (sugar → bioplastic)

**Role:** Convert sugar in the retentate to bioplastic (e.g. PHA) via a yield coefficient (e.g. 0.4 g PHA per g sugar).

**Inputs (conceptual):** Retentate mass and sugar mass, yield coefficient (or full kinetic/model parameters).

**Outputs (sample):**

| Quantity | Value | Unit |
|----------|--------|------|
| Bioplastic (PHA) produced | 0.221 | kg |
| Sugar consumed | 0.554 | kg |
| Yield coefficient | 0.4 | g PHA / g sugar |
| Yield from sugar | 40.0 | % |
| Yield from total raw input | 0.11 | % |

**Plug-in:** Growth/yield kinetics (e.g. Monod, R. eutropha), or ML-based yield model.

---

### 3.6 Overall efficiency (sample run)

| Quantity | Value | Unit |
|----------|--------|------|
| Product recovery (product / raw input) | 97.17 | % |
| Bioplastic per tonne raw input | 1.11 | kg/tonne |
| Mass balance closed | Yes | — |

---

## 4. How to run and extend

- **Run one full cycle (default parameters):**  
  `python -m icecream_simulator.run_full_cycle`
- **Run with your parameters:**  
  Use `run_full_cycle(raw_materials=..., tank_surface_area_m2=..., water_volume_L=..., air_overrun=..., interface_flush_L=..., include_cleaning_phase=..., temperature_K=..., mixing_time_s=..., rpm=..., mixing_model=..., bioconversion_model=...)`.
- **Replace only mixing or bioconversion:**  
  Implement `MixerModelBase` or `BioconversionModelBase` and pass instances into `run_full_cycle`.  
- **Replace internal correlations:**  
  Search the codebase for **PLUG-IN** comments (e.g. viscosity, power, residue, wash efficiency, Darcy, yield) and substitute your own equations or surrogates.

This document and the sample numbers refer to **Pipeline 2 (MaterialBatch)**. For a short technical overview of both pipelines and the project structure, see the main [README](../README.md).
