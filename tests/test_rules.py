import pytest

from pfair.rules import Rules, Variant


def n_first_moves(v):
    r = Rules(v)
    return len(r.successors(r.initial_state()))


def test_domino_placements_on_2x2():
    assert n_first_moves(Variant(2, 2)) == 4                       # 2 vertical + 2 horizontal
    assert n_first_moves(Variant(2, 2, partisan=True)) == 2        # side 0 only vertical


def test_l_tromino_has_four_orientations():
    # on a 2x2 board an L-tromino fits in 4 ways (which cell is left empty)
    assert n_first_moves(Variant(2, 2, shapes=("l3",))) == 4


def test_straight_tromino_on_3x3():
    # 3 vertical + 3 horizontal placements
    assert n_first_moves(Variant(3, 3, shapes=("i3",))) == 6


def test_partisan_rejects_l_tromino():
    with pytest.raises(ValueError):
        Rules(Variant(3, 3, shapes=("domino", "l3"), partisan=True))


def test_unknown_options_rejected():
    with pytest.raises(ValueError):
        Rules(Variant(3, 3, memory="sometimes"))
    with pytest.raises(ValueError):
        Rules(Variant(3, 3, shapes=("hexomino",)))


def test_max_plies_bound():
    assert Rules(Variant(4, 4)).max_plies_bound() == 8
    assert Rules(Variant(3, 3, shapes=("domino", "i3"))).max_plies_bound() == 4


def test_memory_blocks_reuse_until_cycle_complete():
    v = Variant(4, 4, shapes=("domino", "i3"), memory="per_player")
    r = Rules(v)
    s = r.initial_state()
    (shape, mask), s1 = next((m, n) for m, n in r.successors(s) if m[0] == 0)  # side 0 uses domino
    # side 0 has now used 'domino': its next turn must use 'i3'. Play a quick side-1 move,
    # then check that side 0's moves are all i3.
    (_, s2) = r.successors(s1)[0]
    assert {m[0] for m, _ in r.successors(s2)} == {1}
    # shared memory: side 1 cannot use 'domino' right after side 0 used it
    r2 = Rules(Variant(4, 4, shapes=("domino", "i3"), memory="shared"))
    (_, t1) = next((m, n) for m, n in r2.successors(r2.initial_state()) if m[0] == 0)
    assert {m[0] for m, _ in r2.successors(t1)} == {1}


# ---- new shapes, misere, no-repeat memory ---------------------------------------------------------
def test_new_shape_placement_counts():
    assert n_first_moves(Variant(2, 2, shapes=("mono",))) == 4
    assert n_first_moves(Variant(2, 2, shapes=("o4",))) == 1
    assert n_first_moves(Variant(3, 3, shapes=("i4",))) == 0
    assert n_first_moves(Variant(4, 4, shapes=("i4",))) == 8      # 4 vertical + 4 horizontal
    assert n_first_moves(Variant(3, 3, shapes=("t4",))) == 8      # 4 orientations x 2 positions
    assert n_first_moves(Variant(3, 3, shapes=("s4",))) == 4      # 2 orientations x 2 positions
    assert n_first_moves(Variant(3, 3, shapes=("l4",))) == 8      # 4 orientations x 2 positions


def test_partisan_needs_vertical_and_horizontal_orientation():
    for name in ("mono", "o4", "l3"):
        with pytest.raises(ValueError):
            Rules(Variant(3, 3, shapes=("domino", name), partisan=True))
    Rules(Variant(4, 4, shapes=("domino", "t4"), partisan=True))   # T has both: allowed


def test_misere_changes_only_what_no_legal_move_means():
    r = Rules(Variant(1, 1, misere=True))
    assert r.successors(r.initial_state()) == []      # domino does not fit on 1x1
    assert r.stuck_wins
    assert not Rules(Variant(1, 1)).stuck_wins
    assert "misere" in Variant(2, 2, misere=True).vid()
    assert "misere" not in Variant(2, 2).vid()         # old ids (and old result files) stay valid


def test_no_repeat_own_shape_only():
    r = Rules(Variant(4, 4, shapes=("domino", "i3"), memory="no_repeat"))
    (_, s1) = next((m, n) for m, n in r.successors(r.initial_state()) if m[0] == 0)   # side 0: domino
    assert {m[0] for m, _ in r.successors(s1)} == {0, 1}      # side 1 has no history yet
    (_, s2) = next((m, n) for m, n in r.successors(s1) if m[0] == 0)                  # side 1: domino
    assert {m[0] for m, _ in r.successors(s2)} == {1}         # side 0 may not repeat its own domino


def test_no_repeat_shared_blocks_the_shape_just_played():
    r = Rules(Variant(4, 4, shapes=("domino", "i3"), memory="no_repeat_shared"))
    (_, s1) = next((m, n) for m, n in r.successors(r.initial_state()) if m[0] == 0)
    assert {m[0] for m, _ in r.successors(s1)} == {1}         # side 1 cannot copy the domino
    (_, s2) = next((m, n) for m, n in r.successors(s1) if m[0] == 1)
    assert {m[0] for m, _ in r.successors(s2)} == {0}         # side 0 cannot copy the tromino


def test_no_repeat_stuck_lose_vs_reset():
    def after_two_dominoes(stuck):
        r = Rules(Variant(1, 6, shapes=("domino", "i3"), memory="no_repeat", memory_stuck=stuck))
        s = r.initial_state()
        for mask in (0b11, 0b1100):                            # rows 0-1, then rows 2-3
            s = next(n for (sh, m), n in r.successors(s) if sh == 0 and m == mask)
        return r, s

    r, s = after_two_dominoes("lose")
    assert r.successors(s) == []                               # only a domino fits, but it was just used
    r, s = after_two_dominoes("reset")
    assert {m for (_, m), _ in r.successors(s)} == {0b110000}  # the restriction is lifted
