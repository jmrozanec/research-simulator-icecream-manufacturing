#!/usr/bin/env python3
"""Run all literature-linked mix presets (batch comparison)."""

import sys
from pathlib import Path

src = Path(__file__).resolve().parents[1] / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from icecream_simulator.literature_recipes import run_literature_suite  # noqa: E402

if __name__ == "__main__":
    rows = run_literature_suite(include_cleaning_phase=False)
    for r in rows:
        print(r)
