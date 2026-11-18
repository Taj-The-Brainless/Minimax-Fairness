"""Experiment pipeline: variant grids -> exact solve -> depth table / d* -> matches -> CSV.

One call to run_variant() produces every row we need for one variant, so the pipeline is
easy to rerun for any subset of the grid. Results go to results/*.csv (see cli.py).
"""
from __future__ import annotations

import csv
import itertools
import os
import signal
import time
from dataclasses import dataclass, field, replace

from .players import EVALS, depth_table, run_matches, settling_depth
from .rules import Rules, Variant
from .solver import solve_variant, pie_second_player_always_wins  # noqa: F401  (re-export)
from .symmetry import analyze_mirror


# ---- grids ----------------------------------------------------------------------------------
def make_grid(sizes, shape_sets, partisan=(False, True), pie=(False,), memory=("off",),
              memory_stuck="lose", misere=(False,)):
    """All valid combinations. Skips: partisan + shapes without a vertical AND a horizontal
    orientation (l3, mono, o4), memory with a single shape; square boards counted twice are kept
    (rows x columns differ in partisan games)."""
    out = []
    for (w, h), shapes, par, pi, mem, mi in itertools.product(sizes, shape_sets, partisan, pie,
                                                              memory, misere):
        if par and any(name in ("l3", "mono", "o4") for name in shapes):
            continue
        if mem != "off" and len(shapes) < 2:
            continue
        out.append(Variant(w, h, tuple(shapes), partisan=par, pie=pi, memory=mem,
                           memory_stuck=memory_stuck, misere=mi))
    return out


PILOT = make_grid(
    sizes=[(2, 2), (3, 3), (3, 4), (4, 4)],
    shape_sets=[("domino",), ("domino", "i3")],
    partisan=(False, True),
    pie=(False,),
    memory=("off", "per_player"),
)

# TODO(team): fill in after the pilot (board range, shape sets, which rule combinations).
MAIN = make_grid(
    sizes=[(w, h) for w in range(2, 6) for h in range(2, 6)],
    shape_sets=[("domino",), ("domino", "i3"), ("domino", "l3")],
    partisan=(False, True),
    pie=(False, True),
    memory=("off", "per_player"),
)

GRIDS = {"pilot": PILOT, "main": MAIN}


# ---- configuration ----------------------------------------------------------------------------
@dataclass
class Config:
    node_limit: int = 2_000_000          # exact search node limit (unsolved if exceeded)
    depth_node_limit: int = 2_000_000    # node limit for each depth-limited search
    no_tt_baseline: bool = True          # also solve without TT (cost baseline) when cheap
    no_tt_node_limit: int = 500_000
    evals: tuple = ("zero", "mobility")  # names from players.EVALS
    match_depths: tuple = (1, 2, 3, 4)
    n_games: int = 100
    random_opening: int = 0
    seed: int = 0
    stages: tuple = ("exact", "depth", "matches")
    matches_unsolved: bool = False       # also play matches on variants the exact solver could not solve


# ---- one variant ------------------------------------------------------------------------------
_SOLVE_CACHE: dict = {}


def _cached_solve(variant: Variant, node_limit: int, use_tt: bool = True):
    """The exact solver ignores the pie rule, so a pie variant and its non-pie twin share a solve."""
    key = (replace(variant, pie=False), node_limit, use_tt)
    if key not in _SOLVE_CACHE:
        _SOLVE_CACHE[key] = solve_variant(variant, node_limit, use_tt)
    return _SOLVE_CACHE[key]


def run_variant(variant: Variant, cfg: Config):
    """Returns (exact_row, depth_rows, dstar_rows, match_rows) for one variant."""
    rules = Rules(variant)
    mirror = analyze_mirror(variant, rules)
    # label every row, so later analysis can separate variants with a simple pairing strategy
    base = {"variant_id": variant.vid(), **variant.to_dict(),
            "mirror_proved": mirror.applicable, "mirror_winner": mirror.winner or "",
            "mirror_symmetry": mirror.symmetry or ""}
    L = rules.max_plies_bound()

    res = _cached_solve(variant, cfg.node_limit)
    if mirror.applicable and res.solved and (mirror.winner == "first") != res.first_wins:
        raise AssertionError(f"symmetry checker disagrees with the exact solver on {variant.vid()} (bug)")
    exact = {**base, "solved": res.solved,
             "first_wins": res.first_wins,
             "winner": ("first" if res.first_wins else "second") if res.solved else "unsolved",
             "pie_exact_winner": ("second" if variant.pie else ""),  # by the pie argument
             "nodes": res.nodes, "tt_hits": res.tt_hits, "tt_entries": res.tt_entries,
             "seconds": round(res.seconds, 4), "max_plies_bound": L,
             "nodes_no_tt": ""}
    if cfg.no_tt_baseline and res.solved:
        r2 = _cached_solve(variant, cfg.no_tt_node_limit, use_tt=False)
        exact["nodes_no_tt"] = r2.nodes if r2.solved else f">{cfg.no_tt_node_limit}"

    depth_rows, dstar_rows, match_rows = [], [], []
    if res.solved and "depth" in cfg.stages:
        for name in cfg.evals:
            rows, status = depth_table(rules, EVALS[name], res.first_wins,
                                       node_limit=cfg.depth_node_limit)
            for r in rows:
                depth_rows.append({**base, "eval": name, **r})
            d_star, nodes_to = settling_depth(rows, status)
            dstar_rows.append({**base, "eval": name, "status": status, "d_star": d_star,
                               "d_star_rel": (round(d_star / L, 4) if d_star else ""),
                               "nodes_to_d_star": nodes_to, "exact_nodes": res.nodes,
                               "winner": exact["winner"]})
    if "matches" in cfg.stages and (res.solved or cfg.matches_unsolved):
        for name in cfg.evals:
            for d in cfg.match_depths:
                m = run_matches(rules, d, EVALS[name], cfg.n_games, cfg.seed, cfg.random_opening)
                if res.solved:
                    theory, theory_rate = res.first_wins, (m["side0_rate"] if res.first_wins
                                                           else 1 - m["side0_rate"])
                else:
                    theory, theory_rate = "", ""      # no ground truth: practical fairness only
                match_rows.append({**base, "eval": name, "depth": d, "solved": res.solved, **m,
                                   "theory_first_wins": theory, "theory_winner_rate": theory_rate})
    return exact, depth_rows, dstar_rows, match_rows


# ---- CSV helpers ------------------------------------------------------------------------------
def write_csv(path: str, rows: list):
    if not rows:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _read_csv(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


class VariantTimeout(Exception):
    pass


def _on_alarm(signum, frame):
    raise VariantTimeout()


def run_grid(variants, cfg: Config, out_dir: str = "results", progress=print, resume: bool = True,
             max_seconds: float | None = None, variant_timeout: float | None = None):
    """Run every variant and write exact/depth/dstar/matches CSVs into out_dir.

    With resume=True (default), variants already present in out_dir/exact.csv are skipped, so a
    stopped run can be restarted with the same command. Use a new --out folder (or delete the folder)
    to start from scratch, and keep the same settings within one folder.

    max_seconds: stop starting new variants after this many seconds (rerun to continue).
    variant_timeout: abort a single variant after this many seconds (Unix only); it is recorded
    in exact.csv as winner="timeout" and skipped on later runs.
    """
    paths = {n: os.path.join(out_dir, f"{n}.csv") for n in ("exact", "depth", "dstar", "matches")}
    exact_rows, depth_rows, dstar_rows, match_rows = ([], [], [], [])
    if resume:
        exact_rows, depth_rows = _read_csv(paths["exact"]), _read_csv(paths["depth"])
        dstar_rows, match_rows = _read_csv(paths["dstar"]), _read_csv(paths["matches"])
    done = {r["variant_id"] for r in exact_rows}
    t0 = time.perf_counter()
    todo = [v for v in variants if v.vid() not in done]
    if done:
        progress(f"resuming: {len(done)} variants already done, {len(todo)} to go")
    use_alarm = bool(variant_timeout) and hasattr(signal, "SIGALRM")
    if use_alarm:
        signal.signal(signal.SIGALRM, _on_alarm)
    for i, v in enumerate(todo, 1):
        if max_seconds is not None and time.perf_counter() - t0 > max_seconds:
            progress(f"time budget reached after {i - 1} variants; rerun the same command to continue")
            break
        t_v = time.perf_counter()
        progress(f"[{i}/{len(todo)}] starting {v.vid()} ...")
        try:
            if use_alarm:
                signal.alarm(int(variant_timeout))
            e, d, s, m = run_variant(v, cfg)
        except VariantTimeout:
            progress(f"[{i}/{len(todo)}] {v.vid()}: TIMEOUT after {variant_timeout}s, skipped")
            e = {"variant_id": v.vid(), **v.to_dict(), "solved": False, "winner": "timeout",
                 "nodes": "", "seconds": variant_timeout}
            d, s, m = [], [], []
        finally:
            if use_alarm:
                signal.alarm(0)
        exact_rows.append(e)
        depth_rows += d
        dstar_rows += s
        match_rows += m
        progress(f"[{i}/{len(todo)}] {v.vid()}: {e['winner']}, nodes={e['nodes']} "
                 f"({time.perf_counter() - t_v:.1f}s; {time.perf_counter() - t0:.0f}s total)")
        # write after every variant so a crash or Ctrl-C loses nothing
        for name, rows in (("exact", exact_rows), ("depth", depth_rows),
                           ("dstar", dstar_rows), ("matches", match_rows)):
            write_csv(paths[name], rows)
    return exact_rows, depth_rows, dstar_rows, match_rows
