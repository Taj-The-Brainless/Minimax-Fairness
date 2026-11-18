"""Collect all data the current code can produce.

    python collect_all.py                  # full MAIN grid -> results/main (resumable)
    python collect_all.py --grid pilot     # small pilot grid, a few seconds

If it stops (Ctrl-C, closed laptop), run the same command again: finished variants are skipped.
Add --fresh to start over. Settings are the ones used for the reference results; change them
here if you change the experiment.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from pfair import analysis                                  # noqa: E402
from pfair.experiments import Config, GRIDS, run_grid       # noqa: E402
from pfair.symmetry import without_mirror                   # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--grid", choices=sorted(GRIDS), default="main")
p.add_argument("--out", default=None, help="default: results/<grid>")
p.add_argument("--fresh", action="store_true")
p.add_argument("--drop-mirror", action="store_true",
               help="leave out variants with a proved pairing strategy (default: keep and label them; "
                    "use a different --out folder)")
args = p.parse_args()
out = args.out or os.path.join("results", args.grid)

cfg = Config(node_limit=2_000_000, depth_node_limit=2_000_000,
             evals=("zero", "mobility"), match_depths=(1, 2, 3, 4),
             n_games=100, random_opening=0, seed=0)
variants = without_mirror(GRIDS[args.grid]) if args.drop_mirror else GRIDS[args.grid]
run_grid(variants, cfg, out, resume=not args.fresh)
analysis.main(out)
print("done. CSV files and plots are in", out)
