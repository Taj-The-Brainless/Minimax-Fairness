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
