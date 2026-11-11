"""Depth-limited alpha-beta (the "imperfect player"), settling depth d*, and matches.

Values are from the point of view of the side to move (negamax). A position with no legal
move is an exact loss (-WIN). At the depth limit, an evaluation function estimates the value.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .rules import Rules
from .solver import NodeLimitExceeded

WIN = 10 ** 6
INF = 10 ** 9


# ---- evaluation functions: (rules, state) -> int, from the side to move's view ------------
def eval_zero(rules: Rules, state) -> int:
    """No knowledge: all unfinished positions look equal. Search only sees real wins/losses."""
    return 0


def eval_mobility(rules: Rules, state) -> int:
    """Own placements minus opponent's placements (ignores the memory rule).
    Informative in partisan (Domineering-like) variants; always 0 in impartial ones."""
    occ, side, _, _ = state
    return rules.count_moves(side, occ) - rules.count_moves(1 - side, occ)


def eval_parity(rules: Rules, state) -> int:
    """Placeholder for impartial variants: +1 if the number of legal moves is odd, else -1.
    TODO(team): replace with something better, or justify keeping it (docs/rules.md)."""
    return 1 if len(rules.successors(state)) % 2 else -1


EVALS = {"zero": eval_zero, "mobility": eval_mobility, "parity": eval_parity}

_EXACT, _LOWER, _UPPER = 0, 1, 2


class DepthLimited:
    """Negamax alpha-beta with a depth limit. TT entries are keyed by (position, remaining
    depth), so a table hit gives exactly what a fresh depth-limited search would."""

    def __init__(self, rules: Rules, eval_fn, use_tt: bool = True, node_limit: int | None = None):
        self.rules = rules
        self.eval_fn = eval_fn
        self.use_tt = use_tt
        self.node_limit = node_limit
        self.tt: dict = {}
        self.nodes = 0
        self.evals = 0
        self.cutoffs = 0   # leaves where the depth limit stopped a non-terminal position

    def reset_counters(self):
        self.nodes = self.evals = self.cutoffs = 0

    def value(self, state, depth: int, alpha: int = -INF, beta: int = INF) -> int:
        self.nodes += 1
        if self.node_limit is not None and self.nodes > self.node_limit:
            raise NodeLimitExceeded
        succ = self.rules.successors(state)
        if not succ:
            return -WIN
        if depth <= 0:
            self.cutoffs += 1
            self.evals += 1
            return self.eval_fn(self.rules, state)
        key = None
        if self.use_tt:
            key = (self.rules.key(state), depth)
            hit = self.tt.get(key)
            if hit is not None:
                flag, v = hit
                if flag == _EXACT:
                    return v
                if flag == _LOWER:
                    alpha = max(alpha, v)
                else:
                    beta = min(beta, v)
                if alpha >= beta:
                    return v
        alpha0 = alpha
        best = -INF
        for _, nxt in succ:
            v = -self.value(nxt, depth - 1, -beta, -alpha)
            if v > best:
                best = v
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break
        if self.use_tt:
            flag = _EXACT if alpha0 < best < beta else (_LOWER if best >= beta else _UPPER)
            self.tt[key] = (flag, best)
        return best


def predicted_first_wins(value: int):
    """Prediction from the root value (root side = side 0): True / False / None (undecided)."""
    if value > 0:
        return True
    if value < 0:
        return False
    return None


def depth_table(rules: Rules, eval_fn, exact_first_wins: bool, node_limit: int | None = None,
                max_depth: int | None = None):
    """Run the depth-limited search at depth 1, 2, 3, ... on the initial position.

    Stops when a search is exhaustive (no depth cut-off, so it equals the exact result) or at
    max_depth / node_limit. Returns (rows, status) with status in {"ok", "node_limit", "max_depth"}.
    """
    max_depth = max_depth or rules.max_plies_bound() + 1
    rows = []
    status = "max_depth"
    for d in range(1, max_depth + 1):
        s = DepthLimited(rules, eval_fn, use_tt=True, node_limit=node_limit)
        try:
            v = s.value(rules.initial_state(), d)
        except NodeLimitExceeded:
            status = "node_limit"
            break
        pred = predicted_first_wins(v)
        exhaustive = s.cutoffs == 0
        rows.append({"depth": d, "value": v, "predicted_first_wins": pred,
                     "correct": pred is not None and pred == exact_first_wins,
                     "nodes": s.nodes, "evals": s.evals, "exhaustive": exhaustive})
        if exhaustive:
            status = "ok"
            break
    return rows, status


def settling_depth(rows, status):
    """d* = smallest depth from which the prediction is correct at every deeper depth.

    Needs status == "ok" (the last row is exhaustive, hence exact). Returns
    (d_star, nodes_to_d_star) with nodes cumulative over depths 1..d*, or (None, None).
    """
    if status != "ok" or not rows:
        return None, None
    if not rows[-1]["correct"]:
        raise AssertionError("exhaustive depth-limited search disagrees with the exact solver (bug)")
    d_star = 1
    for r in rows:
        if not r["correct"]:
            d_star = r["depth"] + 1
    nodes = sum(r["nodes"] for r in rows if r["depth"] <= d_star)
    return d_star, nodes


# ---- players and matches -------------------------------------------------------------------
class Player:
    """Picks the best move by depth-limited search; ties broken at random."""

    def __init__(self, rules: Rules, depth: int, eval_fn, rng: random.Random):
        self.rules, self.depth, self.rng = rules, depth, rng
        self.search = DepthLimited(rules, eval_fn, use_tt=True)

    def child_values(self, succ):
        return [-self.search.value(nxt, self.depth - 1) for _, nxt in succ]

    def choose(self, state):
        succ = self.rules.successors(state)
        vals = self.child_values(succ)
        best = max(vals)
        pick = self.rng.choice([i for i, v in enumerate(vals) if v == best])
        return succ[pick][1]

    def position_value(self, state) -> int:
        """Value of `state` for its side to move, searched `depth` plies."""
        return self.search.value(state, self.depth)


def play_game(rules: Rules, players, rng: random.Random, random_opening: int = 0):
    """Play one game. players = (seat A player, seat B player). Seat A moves first.

    With the pie rule: seat A picks the most balanced first move (smallest |value| for the
    reply side, by A's own search); seat B then keeps side 1 or swaps to side 0 depending on
    B's own search. Returns dict(side0_wins, seat_a_wins, plies, swapped).
    """
    state = rules.initial_state()
    seat_of_side = {0: 0, 1: 1}
    plies = 0
    swapped = False
    if rules.variant.pie:
        a = players[0]
        succ = rules.successors(state)
        if succ:
            vals = [abs(-a.search.value(nxt, max(a.depth - 1, 0))) for _, nxt in succ]
            best = min(vals)
            state = succ[rng.choice([i for i, v in enumerate(vals) if v == best])][1]
            plies += 1
            v_reply = players[1].position_value(state)   # value for side 1 (to move)
            if v_reply < 0 or (v_reply == 0 and rng.random() < 0.5):
                swapped = True
                seat_of_side = {0: 1, 1: 0}
    for _ in range(random_opening):   # extra random plies after the pie decision, for variety
        succ = rules.successors(state)
        if not succ:
            break
        state = rng.choice(succ)[1]
        plies += 1
    while True:
        succ = rules.successors(state)
        if not succ:
            loser_side = state[1]
            break
        state = players[seat_of_side[state[1]]].choose(state)
        plies += 1
    side0_wins = loser_side == 1
    winner_side = 1 - loser_side
    return {"side0_wins": side0_wins, "seat_a_wins": seat_of_side[winner_side] == 0,
            "plies": plies, "swapped": swapped}


def wilson(k: int, n: int, z: float = 1.96):
    """Wilson 95% interval for a proportion k/n."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)


def run_matches(rules: Rules, depth: int, eval_fn, n_games: int, seed: int = 0, random_opening: int = 0):
    """Both seats search `depth` plies. Returns counts plus Wilson intervals."""
    rng = random.Random(seed)
    players = (Player(rules, depth, eval_fn, rng), Player(rules, depth, eval_fn, rng))
    side0 = seat_a = swaps = 0
    for _ in range(n_games):
        g = play_game(rules, players, rng, random_opening)
        side0 += g["side0_wins"]
        seat_a += g["seat_a_wins"]
        swaps += g["swapped"]
    lo, hi = wilson(side0, n_games)
    return {"games": n_games, "side0_wins": side0, "side0_rate": side0 / n_games,
            "side0_ci_low": lo, "side0_ci_high": hi,
            "seat_a_rate": seat_a / n_games, "swap_rate": swaps / n_games}
