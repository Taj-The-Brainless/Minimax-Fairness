"""Exact solver.

Values are win/lose only (no draws), so alpha-beta pruning reduces to "stop at the first
move that leaves the opponent in a losing position". A transposition table (dict keyed by
Rules.key) stores the result for each position. use_tt=False gives the cost baseline.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from .rules import Rules, Variant


class NodeLimitExceeded(Exception):
    pass


@dataclass
class SolveResult:
    solved: bool
    first_wins: bool | None   # side 0 wins under perfect play (None if unsolved)
    nodes: int
    tt_hits: int
    tt_entries: int
    seconds: float


class ExactSolver:
    def __init__(self, rules: Rules, node_limit: int | None = None, use_tt: bool = True):
        self.rules = rules
        self.node_limit = node_limit
        self.use_tt = use_tt
        self.tt: dict = {}
        self.nodes = 0
        self.tt_hits = 0

    def wins(self, state) -> bool:
        """True if the side to move wins from `state` under perfect play."""
        self.nodes += 1
        if self.node_limit is not None and self.nodes > self.node_limit:
            raise NodeLimitExceeded
        if self.use_tt:
            k = self.rules.key(state)
            cached = self.tt.get(k)
            if cached is not None:
                self.tt_hits += 1
                return cached
        result = False
        for _, nxt in self.rules.successors(state):
            if not self.wins(nxt):
                result = True
                break
        if self.use_tt:
            self.tt[k] = result
        return result

    def solve(self) -> SolveResult:
        t0 = time.perf_counter()
        try:
            first_wins = self.wins(self.rules.initial_state())
            solved = True
        except NodeLimitExceeded:
            first_wins, solved = None, False
        return SolveResult(solved, first_wins, self.nodes, self.tt_hits, len(self.tt),
                           time.perf_counter() - t0)


def solve_variant(variant: Variant, node_limit: int | None = None, use_tt: bool = True) -> SolveResult:
    """Exact result for the base game of `variant` (the pie rule is NOT applied here, see pie_*)."""
    return ExactSolver(Rules(variant), node_limit, use_tt).solve()


def pie_second_player_always_wins(variant: Variant) -> bool:
    """Brute-force check of the pie-rule argument (docs/rules.md, risk 1).

    After side 0's first move m, the second *seat* may keep side 1 or swap to side 0.
    Exactly one side wins the position after m (no draws), so the chooser can always
    pick the winning side. Returns True if that holds for every first move.
    """
    rules = Rules(variant)
    solver = ExactSolver(rules)
    for _, nxt in rules.successors(rules.initial_state()):
        side1_wins = solver.wins(nxt)       # side 1 to move wins?
        side0_wins = not side1_wins         # no draws: the other side wins
        if not (side1_wins or side0_wins):
            return False
    return True
