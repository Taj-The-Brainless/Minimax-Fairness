"""The tetromino shapes i4, l4, s4 (and t4, o4) against the independent reference solver on tiny boards."""
import itertools

from pfair.reference import reference_first_wins
from pfair.rules import Rules, Variant
from pfair.solver import solve_variant


def _variants():
    sizes = [(1, 5), (2, 4), (2, 3), (3, 3)]
    shape_sets = [("domino", "i4"), ("domino", "l4"), ("domino", "s4"), ("i4", "t4"), ("l4", "s4")]
    for (w, h), shapes, par, mem, mis in itertools.product(
            sizes, shape_sets, (False, True), ("off", "no_repeat"), (False, True)):
        v = Variant(w, h, shapes, partisan=par, memory=mem, misere=mis)
        try:
            Rules(v)
        except ValueError:
            continue
        yield v


def test_tetrominoes_match_reference():
    count = 0
    for v in _variants():
        assert solve_variant(v).first_wins == reference_first_wins(v), v.vid()
        count += 1
    assert count > 40


def test_each_tetromino_is_actually_used():
    """Guards against a typo making a shape unplaceable everywhere (both copies of the table)."""
    fits = {"i4": (1, 4), "l4": (2, 3), "s4": (2, 3), "t4": (2, 3), "o4": (2, 2)}
    for name, (w, h) in fits.items():
        assert len(Rules(Variant(w, h, (name,))).successors(Rules(Variant(w, h, (name,))).initial_state())) > 0, name
