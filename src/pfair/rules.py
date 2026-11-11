"""Rule engine for placement games.

A *variant* is described by a few parameters (Variant). Rules turns a Variant into
precomputed tile placements and gives move generation. Nothing in this file searches.

Conventions (see docs/rules.md for the written decisions):
  * Players alternate placing one tile. The player who cannot place loses (no draws).
  * Side 0 moves first. In partisan (Domineering-like) variants, side 0 places
    vertical tiles and side 1 horizontal ones (swap with first_orientation="h").
  * State is a plain tuple (occupied_mask, side_to_move, mem0, mem1) for speed.
  * Memory rule: a shape cannot be used again until every shape has been used once;
    then the cycle resets. mem0/mem1 are bit masks over shapes already used in the
    current cycle ("per_player": own mask per side; "shared": mem0 for both).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

# Base cells (row, col) of each shape, in one orientation.
SHAPES = {
    "domino": ((0, 0), (1, 0)),
    "i3": ((0, 0), (1, 0), (2, 0)),   # straight tromino
    "l3": ((0, 0), (1, 0), (1, 1)),   # L-shaped tromino
}


@dataclass(frozen=True)
class Variant:
    width: int
    height: int
    shapes: tuple = ("domino",)
    partisan: bool = False          # False: Cram-like, True: Domineering-like
    first_orientation: str = "v"    # partisan only: orientation of side 0 ("v" or "h")
    pie: bool = False               # second player may swap sides after the first move
    memory: str = "off"             # "off" | "per_player" | "shared"
    memory_stuck: str = "lose"      # if only used shapes fit: "lose" or "reset" the cycle

    def vid(self) -> str:
        """Short readable id used in result files."""
        parts = [f"{self.width}x{self.height}", "+".join(self.shapes),
                 ("partisan-" + self.first_orientation) if self.partisan else "impartial"]
        if self.pie:
            parts.append("pie")
        if self.memory != "off":
            parts.append(f"mem-{self.memory}-{self.memory_stuck}")
        return "_".join(parts)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["shapes"] = "+".join(self.shapes)
        return d


def _normalize(cells):
    mr = min(r for r, c in cells)
    mc = min(c for r, c in cells)
    return frozenset((r - mr, c - mc) for r, c in cells)


def _orientations(cells):
    """All distinct rotations of a shape."""
    cur = _normalize(cells)
    seen = []
    for _ in range(4):
        if cur not in seen:
            seen.append(cur)
        cur = _normalize([(c, -r) for r, c in cur])
    return seen


def _orientation_class(cells) -> str:
    h = max(r for r, c in cells) + 1
    w = max(c for r, c in cells) + 1
    if h > w:
        return "v"
    if w > h:
        return "h"
    return "s"  # square bounding box (L-tromino)


class Rules:
    """Precomputed rules for one Variant."""

    def __init__(self, variant: Variant):
        v = variant
        if v.memory not in ("off", "per_player", "shared"):
            raise ValueError(f"unknown memory mode {v.memory!r}")
        if v.memory_stuck not in ("lose", "reset"):
            raise ValueError(f"unknown memory_stuck {v.memory_stuck!r}")
        if v.first_orientation not in ("v", "h"):
            raise ValueError("first_orientation must be 'v' or 'h'")
        for name in v.shapes:
            if name not in SHAPES:
                raise ValueError(f"unknown shape {name!r}")
        self.variant = v
        self.width, self.height = v.width, v.height
        self.cells = v.width * v.height
        self.n_shapes = len(v.shapes)
        self.all_shapes_mask = (1 << self.n_shapes) - 1
        self.memory = v.memory
        self.stuck = v.memory_stuck
        self.mem_on = v.memory != "off"
        self.areas = [len(SHAPES[n]) for n in v.shapes]

        # placements[side][shape_index] -> list of bit masks
        self.placements = []
        for side in (0, 1):
            if v.partisan:
                own = v.first_orientation if side == 0 else ("h" if v.first_orientation == "v" else "v")
                allowed = {own}
            else:
                allowed = {"v", "h", "s"}
            per_shape = []
            for name in v.shapes:
                masks = set()
                for orient in _orientations(SHAPES[name]):
                    if _orientation_class(orient) not in allowed:
                        continue
                    h = max(r for r, c in orient) + 1
                    w = max(c for r, c in orient) + 1
                    for r0 in range(v.height - h + 1):
                        for c0 in range(v.width - w + 1):
                            m = 0
                            for r, c in orient:
                                m |= 1 << ((r0 + r) * v.width + (c0 + c))
                            masks.add(m)
                per_shape.append(sorted(masks))
            self.placements.append(per_shape)
        if v.partisan:
            for name in v.shapes:
                if not (_has_class(name, "v") and _has_class(name, "h")):
                    raise ValueError(f"shape {name!r} has no vertical and horizontal orientation, "
                                     "use it only in impartial variants")

        self._key_has_side = v.partisan or v.memory == "per_player"

    # ---- states -------------------------------------------------------
    def initial_state(self):
        return (0, 0, 0, 0)

    def key(self, state):
        """Hashable key for transposition tables (drops information that cannot matter)."""
        occ, side, m0, m1 = state
        if not self.mem_on:
            return (occ, side) if self._key_has_side else occ
        if self.memory == "shared":
            return (occ, side, m0) if self._key_has_side else (occ, m0)
        return (occ, side, m0, m1)

    def max_plies_bound(self) -> int:
        """Upper bound on game length in plies (cells / smallest tile)."""
        return self.cells // min(self.areas)

    # ---- moves --------------------------------------------------------
    def successors(self, state):
        """List of (move, next_state); move = (shape_index, mask). Empty list = side to move loses."""
        occ, side, m0, m1 = state
        if self.mem_on:
            slot = 0 if self.memory == "shared" else side
            mem = m0 if slot == 0 else m1
        else:
            slot, mem = 0, 0
        out = self._gen(state, mem, slot)
        if not out and self.mem_on and self.stuck == "reset" and mem:
            out = self._gen(state, 0, slot)
        return out

    def _gen(self, state, mem, slot):
        occ, side, m0, m1 = state
        out = []
        own = self.placements[side]
        for s in range(self.n_shapes):
            if mem >> s & 1:
                continue
            for mask in own[s]:
                if mask & occ:
                    continue
                if self.mem_on:
                    nm = mem | (1 << s)
                    if nm == self.all_shapes_mask:
                        nm = 0
                    nxt = (occ | mask, 1 - side, nm, m1) if slot == 0 else (occ | mask, 1 - side, m0, nm)
                else:
                    nxt = (occ | mask, 1 - side, 0, 0)
                out.append(((s, mask), nxt))
        return out

    def count_moves(self, side, occ) -> int:
        """Placements available to `side` on this board, ignoring the memory rule."""
        n = 0
        for masks in self.placements[side]:
            for mask in masks:
                if not mask & occ:
                    n += 1
        return n


def _has_class(shape_name, cls) -> bool:
    return any(_orientation_class(o) == cls for o in _orientations(SHAPES[shape_name]))
