# Ice cream production + washwater bioplastic (simplified simulator)

Closed-form mass-and-composition model: **recipe → product & residue → CIP wastewater → prefiltration → cavitation → membrane split → PHA yield**.

Full equation list, assumptions, citations for every formula and constant, and code map: **`docs/SIMPLIFIED_PIPELINE_REPORT.md`** (see §4 for references and $\varphi$ guidance).

## Install

```bash
pip install -e .
# optional UI
pip install streamlit
```

## Run

```bash
python run.py
python run.py --preset GIUDICI_2021_INDUSTRIAL
python run.py --literature-suite
python run.py --no-cleaning    # product only; valorization zeros
```

```python
from icecream_simulator import RawMaterials, run_full_cycle, print_report

report = run_full_cycle(
    raw_materials=RawMaterials(milk=100, cream=30, sugar=25, stabilizers=2, water=43, emulsifiers_kg=0.5),
    residue_mass_fraction=0.02,
    air_overrun=0.5,
)
print_report(report)
```

## Package layout

| Module | Role |
|--------|------|
| `constants.py` | All scalar parameters |
| `domain.py` | Pydantic models |
| `pipeline.py` | `run_full_cycle`, `print_report`, literature presets |

## Tests

```bash
PYTHONPATH=src python3 -m pytest tests/test_pipeline.py -v
```

## License

See `LICENSE`.
