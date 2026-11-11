"""Command line:  python -m pfair.cli run --grid pilot --out results/pilot

Writes exact.csv, depth.csv, dstar.csv, matches.csv into --out (rewritten after every variant).
"""
from __future__ import annotations

import argparse

from .experiments import Config, GRIDS, run_grid


def main(argv=None):
    p = argparse.ArgumentParser(prog="pfair")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the pipeline on a grid of variants")
    r.add_argument("--grid", choices=sorted(GRIDS), default="pilot")
    r.add_argument("--out", default="results/pilot")
    r.add_argument("--stages", default="exact,depth,matches",
                   help="comma list from: exact, depth, matches (exact always runs)")
    r.add_argument("--node-limit", type=int, default=2_000_000)
    r.add_argument("--games", type=int, default=100)
    r.add_argument("--match-depths", default="1,2,3,4")
    r.add_argument("--evals", default="zero,mobility")
    r.add_argument("--random-opening", type=int, default=0)
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--limit", type=int, default=None, help="only the first N variants (quick test)")
    r.add_argument("--fresh", action="store_true", help="ignore existing CSVs in --out and start over")
    args = p.parse_args(argv)

    cfg = Config(node_limit=args.node_limit, depth_node_limit=args.node_limit,
                 evals=tuple(args.evals.split(",")),
                 match_depths=tuple(int(x) for x in args.match_depths.split(",")),
                 n_games=args.games, random_opening=args.random_opening, seed=args.seed,
                 stages=tuple(args.stages.split(",")))
    variants = GRIDS[args.grid][: args.limit]
    run_grid(variants, cfg, args.out, resume=not args.fresh)


if __name__ == "__main__":
    main()
