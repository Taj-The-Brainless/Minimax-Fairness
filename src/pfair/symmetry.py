"""Symmetry (pairing) strategy checker.

Some placement games are decided by a trivial strategy: answer every move with its mirror image.
Depth-limited players do not find such strategies, so a variant that is unfair in theory can look
balanced in practice for a reason that has nothing to do with search difficulty. This module
decides, for one Variant, whether such a strategy is PROVED to exist, so the result tables can
label those variants.

Two proofs are implemented (normal play only, see "conservative" below):

  1. second-player pairing. For some board symmetry sigma (an involution: 180-degree rotation,
     a mirror, or for square boards a diagonal mirror) every placement p of the first player has
     an image sigma(p) that (a) does not overlap p and (b) is a legal placement of the second
     player with the same shape. Then after every pair of moves the occupied cells are
     symmetric, so the second player can always answer and the first player runs out of moves
     first. Winner: second.

  2. first-player centre move + pairing. The first player has a placement c with sigma(c) = c.
     After c the position is symmetric; if every placement p of the second player that does not
     overlap c can be answered the same way, the first player always has a reply. Winner: first.

Conservative by design. "applicable = False" means only "no proof found", NOT "the variant is
fair" and NOT "no simple strategy exists". The checker refuses (applicable = False) when the
argument could break:
  * misere play (always being able to answer makes you the LAST player to place, which loses),
  * memory rules that can stop the reply from using the same shape as the move it answers
    (shared cycle with 2+ shapes, no-repeat rules, per_player cycle with memory_stuck="reset").
The pie rule is ignored on purpose: like the exact solver, this analyses the base game.

Safety net: tests/test_symmetry.py checks that whenever the checker claims a winner, the exact
solver agrees; experiments.run_variant repeats that check during every run.
"""
from __future__ import annotations

from dataclasses import dataclass

from .rules import Rules, Variant

_CYCLE_MODES = ("per_player", "shared")


@dataclass(frozen=True)
class MirrorAnalysis:
    applicable: bool          # True only if a pairing strategy was PROVED
    winner: str | None        # "first" or "second" under perfect play (None if not applicable)
    symmetry: str | None      # board symmetry used, e.g. "rot180"
    reason: str               # short explanation, for reports and debugging


def _cell_maps(width: int, height: int) -> dict:
    """Board involutions as permutations of cell indices (index = row * width + col)."""
    funcs = {
        "rot180": lambda r, c: (height - 1 - r, width - 1 - c),
        "flip_rows": lambda r, c: (height - 1 - r, c),     # up-down mirror
        "flip_cols": lambda r, c: (r, width - 1 - c),      # left-right mirror
    }
    if width == height:
        funcs["transpose"] = lambda r, c: (c, r)
        funcs["anti_transpose"] = lambda r, c: (height - 1 - c, width - 1 - r)
    maps = {}
    for name, f in funcs.items():
        perm = []
        for i in range(width * height):
            r, c = divmod(i, width)
            r2, c2 = f(r, c)
            perm.append(r2 * width + c2)
        maps[name] = perm
    return maps


def _apply(mask: int, perm: list) -> int:
    """Image of a cell bit mask under a cell permutation."""
    out = 0
    i = 0
    while mask:
        if mask & 1:
            out |= 1 << perm[i]
        mask >>= 1
        i += 1
    return out


def _second_player_memory_ok(v: Variant) -> bool:
    """Can the second player always answer with the SAME shape the first player just used?"""
    if v.memory == "off":
        return True
    if v.memory in _CYCLE_MODES and len(v.shapes) == 1:
        return True           # one shape: the cycle resets after every move, the rule does nothing
    # per_player cycles stay identical when every reply copies the shape; with "lose" the first
    # player never gets to use a blocked shape, so the second player is never forced to either.
    return v.memory == "per_player" and v.memory_stuck == "lose"


def _first_player_memory_ok(v: Variant) -> bool:
    if v.memory == "off":
        return True
    return v.memory in _CYCLE_MODES and len(v.shapes) == 1


def _pairs_every_move(side0_placements, side1_sets, perm) -> bool:
    """Proof 1: every first-player placement p has a disjoint same-shape image for the second player."""
    for s, masks in enumerate(side0_placements):
        for m in masks:
            q = _apply(m, perm)
            if q & m or q not in side1_sets[s]:
                return False
    return True


def _centre_then_pair(rules: Rules, place_sets, perm) -> bool:
    """Proof 2: a symmetric first move c after which every legal reply of the second player can be paired."""
    centres = [c for masks in rules.placements[0] for c in masks if _apply(c, perm) == c]
    if not centres:
        return False
    unanswerable = []          # second-player placements that cannot be mirrored
    for s, masks in enumerate(rules.placements[1]):
        for p in masks:
            q = _apply(p, perm)
            if q & p or q not in place_sets[0][s]:
                unanswerable.append(p)
    # a centre works if every unanswerable placement overlaps it (so it is never legal after c)
    return any(all(p & c for p in unanswerable) for c in centres)


def analyze_mirror(variant: Variant, rules: Rules | None = None) -> MirrorAnalysis:
    """Look for a proved pairing strategy in the base game of `variant`."""
    if variant.misere:
        return MirrorAnalysis(False, None, None,
                              "misere play: the player who can always answer places last and loses")
    rules = rules or Rules(variant)
    maps = _cell_maps(rules.width, rules.height)
    place_sets = [[set(masks) for masks in side] for side in rules.placements]

    if _second_player_memory_ok(variant):
        for name, perm in maps.items():
            if _pairs_every_move(rules.placements[0], place_sets[1], perm):
                return MirrorAnalysis(True, "second", name,
                                      f"second player answers every move with its {name} image")
    if _first_player_memory_ok(variant):
        for name, perm in maps.items():
            if _centre_then_pair(rules, place_sets, perm):
                return MirrorAnalysis(True, "first", name,
                                      f"first player plays a {name}-symmetric tile, then pairs every reply")
    return MirrorAnalysis(False, None, None,
                          "no pairing strategy proved (this does NOT mean the variant is fair)")


def mirror_applicable(variant: Variant) -> bool:
    return analyze_mirror(variant).applicable


def split_by_mirror(variants):
    """Return (kept, flagged): flagged = variants where a pairing strategy is proved."""
    kept, flagged = [], []
    for v in variants:
        (flagged if analyze_mirror(v).applicable else kept).append(v)
    return kept, flagged


def without_mirror(variants):
    """The variants with no proved pairing strategy (use only if you really want to drop the others)."""
    return split_by_mirror(variants)[0]
