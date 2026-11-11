import itertools

import pytest

from pfair.reference import reference_first_wins
from pfair.rules import Variant
from pfair.solver import pie_second_player_always_wins, solve_variant


def first_wins(v, use_tt=True):
    r = solve_variant(v, use_tt=use_tt)
    assert r.solved
    return r.first_wins


# ---- hand checks / known theory -------------------------------------------------------------
def test_tiny_boards_by_hand():
    assert first_wins(Variant(2, 2)) is False                      # Cram 2x2: second player wins
    assert first_wins(Variant(2, 2, partisan=True)) is True        # Domineering 2x2: first (vertical) wins


@pytest.mark.parametrize("w,h", [(2, 2), (2, 4), (4, 2), (4, 4)])
def test_cram_even_by_even_second_player_wins(w, h):
    # rotation-symmetry strategy for the second player
    assert first_wins(Variant(w, h)) is False


@pytest.mark.parametrize("w,h", [(2, 3), (3, 2), (2, 5), (3, 4), (4, 3)])
def test_cram_odd_by_even_first_player_wins(w, h):
    # centre domino, then mirror
    assert first_wins(Variant(w, h)) is True


# TODO(team): add published results here (Breuker et al. 2000, Lachmann et al., Uiterwijk 2016/2019):
#   e.g. standard Domineering boards, with the source and the player convention in a comment.


# ---- two implementations must agree ---------------------------------------------------------
def tiny_variants():
    sizes = [(1, 5), (1, 6), (2, 2), (2, 3), (3, 2), (3, 3), (2, 4), (4, 2)]
    shape_sets = [("domino",), ("domino", "i3"), ("domino", "l3"), ("i3", "l3")]
    for (w, h), shapes, par, mem, stuck in itertools.product(
            sizes, shape_sets, (False, True), ("off", "per_player", "shared"), ("lose", "reset")):
        if par and "l3" in shapes:
            continue
        if mem == "off" and stuck == "reset":
            continue
        yield Variant(w, h, shapes, partisan=par, memory=mem, memory_stuck=stuck)


def test_fast_solver_matches_reference_on_tiny_variants():
    count = 0
    for v in tiny_variants():
        assert first_wins(v) == reference_first_wins(v), v.vid()
        count += 1
    assert count > 100


def test_first_orientation_h_matches_reference():
    for w, h in [(2, 3), (3, 3), (3, 2)]:
        v = Variant(w, h, partisan=True, first_orientation="h")
        assert first_wins(v) == reference_first_wins(v)


def test_transposition_table_on_and_off_agree():
    for v in [Variant(4, 4), Variant(3, 4, partisan=True), Variant(4, 3, shapes=("domino", "i3"), memory="per_player")]:
        assert first_wins(v, True) == first_wins(v, False)


# ---- symmetry tests -------------------------------------------------------------------------
@pytest.mark.parametrize("w,h", [(2, 5), (3, 4), (3, 3), (4, 4)])
def test_impartial_board_and_its_transpose_agree(w, h):
    assert first_wins(Variant(w, h)) == first_wins(Variant(h, w))


@pytest.mark.parametrize("w,h", [(2, 5), (3, 4), (3, 3), (4, 5)])
def test_vertical_first_on_wxh_equals_horizontal_first_on_hxw(w, h):
    a = first_wins(Variant(w, h, partisan=True, first_orientation="v"))
    b = first_wins(Variant(h, w, partisan=True, first_orientation="h"))
    assert a == b


# ---- reduction tests ------------------------------------------------------------------------
@pytest.mark.parametrize("mem", ["per_player", "shared"])
@pytest.mark.parametrize("w,h", [(3, 3), (3, 4), (4, 4)])
def test_memory_rule_with_one_shape_equals_plain_game(mem, w, h):
    assert first_wins(Variant(w, h, memory=mem)) == first_wins(Variant(w, h))


def test_unused_shape_does_not_change_the_game():
    # an L-tromino never fits on a 2 x 1 strip, so the game equals dominoes only
    assert first_wins(Variant(1, 2, shapes=("domino", "l3"))) == first_wins(Variant(1, 2))


# ---- pie rule argument (risk 1) -------------------------------------------------------------
@pytest.mark.parametrize("v", [Variant(2, 3), Variant(3, 3, partisan=True), Variant(3, 3, shapes=("domino", "i3"))])
def test_pie_rule_always_gives_second_seat_a_winning_choice(v):
    assert pie_second_player_always_wins(v)


# ---- the "stuck" decision of the memory rule is a real rule choice --------------------------
def test_stuck_modes_change_the_game_and_both_match_the_reference():
    lose = Variant(1, 6, ("domino", "i3"), memory="per_player", memory_stuck="lose")
    reset = Variant(1, 6, ("domino", "i3"), memory="per_player", memory_stuck="reset")
    assert first_wins(lose) != first_wins(reset)
    assert first_wins(lose) == reference_first_wins(lose)
    assert first_wins(reset) == reference_first_wins(reset)
