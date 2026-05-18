#!/usr/bin/env python3
"""
Generate a diverse-scenario dataset for ML training (Phase 1).

Usage:
  python examples/generate_dataset.py                       # 200 runs, diverse_industrial_spec
  python examples/generate_dataset.py --n 1000              # bigger sweep
  python examples/generate_dataset.py --out data/my_sweep   # custom output dir
  python examples/generate_dataset.py --sampler random      # disable LHS
  python examples/generate_dataset.py --no-cleaning         # production-only runs
  python examples/generate_dataset.py --presets             # mix in literature presets

Outputs (under ``--out`` / default ``data/sweeps/<name>``):
  runs.csv         — flat row per run, ML-ready
  runs.jsonl       — same rows in JSON Lines (preserves structure)
  runs.parquet     — if pyarrow is installed
  reports/         — full per-run JSON reports (sensors, events, energy)
  manifest.json    — sweep metadata for reproducibility
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Allow running from source tree without install
_THIS = Path(__file__).resolve()
_SRC = _THIS.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from icecream_simulator import (
    diverse_industrial_spec,
    list_preset_ids,
    load_default_profile,
    run_sweep,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a diverse-scenario dataset")
    p.add_argument("--n", type=int, default=200, help="Number of runs (default: 200)")
    p.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    p.add_argument("--out", type=str, default=None,
                   help="Output directory (default: data/sweeps/<scenario_name>)")
    p.add_argument("--sampler", type=str, choices=["lhs", "random"], default="lhs",
                   help="Sampler: 'lhs' (default) for coverage, 'random' for i.i.d. baseline")
    p.add_argument("--no-cleaning", action="store_true",
                   help="Skip CIP / prefiltration / cavitation / filtration / bioconversion")
    p.add_argument("--presets", action="store_true",
                   help="Mix in all literature presets as alternate raw-material sources")
    p.add_argument("--no-reports", action="store_true",
                   help="Skip writing per-run JSON reports (smaller disk footprint)")
    p.add_argument("--name", type=str, default=None,
                   help="Override the scenario name in the manifest and default out dir")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    spec = diverse_industrial_spec()
    if args.name:
        spec.name = args.name
    if args.no_cleaning:
        spec.include_cleaning_phase = False
    if args.presets:
        spec.literature_preset_ids = list_preset_ids()

    out_dir = Path(args.out) if args.out else Path("data") / "sweeps" / spec.name
    profile = load_default_profile()

    print(f"Sweep: {spec.name}")
    print(f"  runs:     {args.n}")
    print(f"  sampler:  {args.sampler}")
    print(f"  seed:     {args.seed}")
    print(f"  profile:  {profile.name}")
    print(f"  cleaning: {spec.include_cleaning_phase}")
    print(f"  presets:  {bool(spec.literature_preset_ids)}")
    print(f"  out:      {out_dir}")
    print()

    last_print = [time.time()]
    def on_run(i: int, row: dict) -> None:
        now = time.time()
        if now - last_print[0] >= 1.0 or i == args.n - 1:
            last_print[0] = now
            worst = row.get("events_worst", "info")
            ice = row.get("q_ice_crystal_mean_um")
            ice_s = f"{ice:.1f}" if isinstance(ice, (int, float)) else "—"
            print(f"  [{i + 1:>4}/{args.n}]  worst={worst:<8}  "
                  f"ice_um={ice_s}  product_kg={row.get('product_kg', 0):.1f}")

    result = run_sweep(
        spec, n=args.n, output_dir=out_dir,
        seed=args.seed, profile=profile, sampler=args.sampler,
        save_full_reports=not args.no_reports,
        on_run=on_run,
    )

    print()
    print(f"Done in {result.elapsed_s:.1f}s — "
          f"{result.n_succeeded} ok, {result.n_failed} failed")
    print(f"  CSV:      {out_dir}/runs.csv")
    print(f"  JSONL:    {out_dir}/runs.jsonl")
    pq = out_dir / "runs.parquet"
    print(f"  Parquet:  {pq if pq.exists() else '(not written — install pandas + pyarrow)'}")
    print(f"  Reports:  {out_dir}/reports/")
    print(f"  Manifest: {out_dir}/manifest.json")
    return 0 if result.n_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
