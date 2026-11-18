import itertools

import pytest

from pfair.rules import Rules, Variant
from pfair.solver import solve_variant
from pfair.symmetry import analyze_mirror, split_by_mirror, without_mirror


@pytest.mark.parametrize("w,h", [(2, 2), (2, 4), (4, 2), (4, 4), (6, 6)])
def test_even_by_even_cram_second_player_by_rotation(w, h):
    a = analyze_mirror(Variant(w, h))
    assert a.applicable and a.winner == "second" and a.symmetry == "rot180"


@pytest.mark.parametrize("w,h", [(2, 3), (3, 2), (2, 5), (3, 4), (4, 3)])
def test_odd_by_even_cram_first_player_by_centre_tile(w, h):
    a = analyze_mirror(Variant(w, h))
    assert a.applicable and a.winner == "first"


def test_not_claimed_when_the_argument_breaks():
    assert not analyze_mirror(Variant(3, 3)).applicable                     # no symmetric first tile
    a = analyze_mirror(Variant(2, 2, partisan=True))        # the vertical player wins at once, by a symmetric tile
    assert a.applicable and a.winner == "first"
    assert not analyze_mirror(Variant(4, 4, partisan=True)).applicable
    assert not analyze_mirror(Variant(4, 4, misere=True)).applicable        # mirroring makes you last
    two = ("domino", "i3")
    assert not analyze_mirror(Variant(4, 4, two, memory="shared")).applicable
    assert not analyze_mirror(Variant(4, 4, two, memory="no_repeat")).applicable
    assert not analyze_mirror(Variant(4, 4, two, memory="per_player", memory_stuck="reset")).applicable


def test_per_player_cycle_with_lose_keeps_the_pairing_strategy():
    a = analyze_mirror(Variant(4, 4, ("domino", "i3"), memory="per_player"))
    assert a.applicable and a.winner == "second"


def _variants():
    sizes = [(1, 5), (2, 2), (2, 3), (3, 2), (2, 4), (4, 2), (3, 3), (4, 4)]
    shape_sets = [("domino",), ("domino", "i3"), ("domino", "l3"), ("i3", "l3"), ("mono",),
                  ("mono", "domino"), ("o4", "domino"), ("domino", "t4")]
    modes = ("off", "per_player", "shared", "no_repeat", "no_repeat_shared")
    for (w, h), shapes, par, mem, stuck, mis in itertools.product(
            sizes, shape_sets, (False, True), modes, ("lose", "reset"), (False, True)):
        if "mono" in shapes and w * h > 6:
            continue                                   # keep the exact solves small
        if (w, h) == (4, 4) and len(shapes) > 1:
            continue
        if mem == "off" and stuck == "reset":
            continue
        v = Variant(w, h, shapes, partisan=par, memory=mem, memory_stuck=stuck, misere=mis)
        try:
            Rules(v)
        except ValueError:
            continue
        yield v


def test_checker_never_contradicts_the_exact_solver():
    """Whenever a pairing strategy is claimed, the exact solver must give the same winner."""
    proved = 0
    for v in _variants():
        a = analyze_mirror(v)
        if not a.applicable:
            continue
        r = solve_variant(v)
        assert r.solved
        assert (a.winner == "first") == r.first_wins, v.vid()
        proved += 1
    assert proved > 20          # guards against passing vacuously


def test_split_and_filter_helpers():
    vs = [Variant(2, 2), Variant(3, 3), Variant(4, 4, partisan=True)]
    kept, flagged = split_by_mirror(vs)
    assert flagged == [Variant(2, 2)]
    assert len(kept) == 2
    assert without_mirror(vs) == kept
