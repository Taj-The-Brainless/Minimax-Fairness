import random

import pytest

from pfair.players import (EVALS, DepthLimited, Player, depth_table, play_game, run_matches,
                           settling_depth, wilson)
from pfair.rules import Rules, Variant
from pfair.solver import solve_variant

VARIANTS = [Variant(3, 3), Variant(3, 4, partisan=True), Variant(4, 4),
            Variant(3, 4, shapes=("domino", "i3"), memory="per_player")]


@pytest.mark.parametrize("v", VARIANTS)
@pytest.mark.parametrize("name", ["zero", "mobility", "parity"])
@pytest.mark.parametrize("depth", [1, 2, 3, 5])
def test_tt_does_not_change_depth_limited_values(v, name, depth):
    rules = Rules(v)
    a = DepthLimited(rules, EVALS[name], use_tt=True).value(rules.initial_state(), depth)
    b = DepthLimited(rules, EVALS[name], use_tt=False).value(rules.initial_state(), depth)
    assert a == b


@pytest.mark.parametrize("v", VARIANTS)
def test_exhaustive_depth_table_agrees_with_exact_solver(v):
    exact = solve_variant(v)
    rules = Rules(v)
    for name in ("zero", "mobility"):
        rows, status = depth_table(rules, EVALS[name], exact.first_wins)
        assert status == "ok"
        assert rows[-1]["exhaustive"] and rows[-1]["correct"]
        d_star, nodes = settling_depth(rows, status)
        assert 1 <= d_star <= len(rows) and nodes > 0


def test_settling_depth_ignores_lucky_early_hits():
    rows = [{"depth": d, "correct": c, "nodes": 10} for d, c in enumerate([False, True, False, True, True], 1)]
    assert settling_depth(rows, "ok") == (4, 40)
    rows_ok = [{"depth": d, "correct": True, "nodes": 5} for d in (1, 2)]
    assert settling_depth(rows_ok, "ok") == (1, 5)
    assert settling_depth(rows, "node_limit") == (None, None)


def test_zero_evaluation_is_undecided_until_search_sees_the_end():
    v = Variant(4, 4)
    rules = Rules(v)
    rows, _ = depth_table(rules, EVALS["zero"], solve_variant(v).first_wins)
    assert rows[0]["predicted_first_wins"] is None and rows[0]["correct"] is False


def test_matches_are_reproducible_with_a_seed():
    rules = Rules(Variant(4, 4, partisan=True))
    a = run_matches(rules, 2, EVALS["mobility"], 20, seed=7)
    b = run_matches(rules, 2, EVALS["mobility"], 20, seed=7)
    assert a == b


def test_full_depth_player_follows_the_exact_result():
    for v in [Variant(3, 3), Variant(3, 4, partisan=True), Variant(2, 3)]:
        rules = Rules(v)
        exact = solve_variant(v).first_wins
        m = run_matches(rules, rules.max_plies_bound() + 1, EVALS["zero"], 10, seed=1)
        assert m["side0_rate"] == (1.0 if exact else 0.0)


def test_pie_game_runs_and_reports_swap():
    rules = Rules(Variant(4, 4, partisan=True, pie=True))
    rng = random.Random(3)
    players = (Player(rules, 2, EVALS["mobility"], rng), Player(rules, 2, EVALS["mobility"], rng))
    g = play_game(rules, players, rng)
    assert set(g) == {"side0_wins", "seat_a_wins", "plies", "swapped"}


def test_wilson_interval_contains_the_estimate():
    lo, hi = wilson(30, 100)
    assert lo < 0.3 < hi
    assert 0 <= lo and hi <= 1
