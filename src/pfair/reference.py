"""Deliberately simple reference solver, used only to validate the fast one.

It shares NO code with rules.py / solver.py: its own shape tables, its own move
generation on a set of occupied cells, plain minimax with no table and no pruning.
Only usable on tiny boards. Handles the base game (the pie rule is not applied).
"""
from __future__ import annotations

from .rules import Variant

_BASE = {
    "domino": [(0, 0), (1, 0)],
    "i3": [(0, 0), (1, 0), (2, 0)],
    "l3": [(0, 0), (1, 0), (1, 1)],
}


def _rotations(cells):
    out = []
    cur = list(cells)
    for _ in range(4):
        mr = min(r for r, c in cur)
        mc = min(c for r, c in cur)
        norm = tuple(sorted((r - mr, c - mc) for r, c in cur))
        if norm not in out:
            out.append(norm)
        cur = [(c, -r) for r, c in cur]
    return out


def _kind(cells):
    h = max(r for r, c in cells) + 1
    w = max(c for r, c in cells) + 1
    return "v" if h > w else ("h" if w > h else "s")


def reference_first_wins(variant: Variant) -> bool:
    """True if the player moving first wins the base game of `variant`."""
    W, H = variant.width, variant.height
    shapes = list(variant.shapes)
    n = len(shapes)
    orients = [_rotations(_BASE[s]) for s in shapes]

    def allowed_kinds(player):
        if not variant.partisan:
            return {"v", "h", "s"}
        first = variant.first_orientation
        other = "h" if first == "v" else "v"
        return {first} if player == 0 else {other}

    def moves(occupied, player, mem):
        kinds = allowed_kinds(player)
        mem_on = variant.memory != "off"
        used = mem[0 if variant.memory == "shared" else player] if mem_on else frozenset()

        def gen(used_set):
            res = []
            for si in range(n):
                if mem_on and si in used_set:
                    continue
                for o in orients[si]:
                    if _kind(o) not in kinds:
                        continue
                    for r0 in range(H):
                        for c0 in range(W):
                            cells = [(r0 + r, c0 + c) for r, c in o]
                            if all(0 <= r < H and 0 <= c < W and (r, c) not in occupied for r, c in cells):
                                res.append((si, cells))
            return res

        found = gen(used)
        reset = False
        if not found and mem_on and variant.memory_stuck == "reset" and used:
            found = gen(frozenset())
            reset = True
        return found, (frozenset() if reset else used)

    def mover_wins(occupied, player, mem):
        found, used = moves(occupied, player, mem)
        for si, cells in found:
            new_occ = occupied | frozenset(cells)
            if variant.memory == "off":
                new_mem = mem
            else:
                new_used = used | {si}
                if len(new_used) == n:
                    new_used = frozenset()
                if variant.memory == "shared":
                    new_mem = (frozenset(new_used), mem[1])
                elif player == 0:
                    new_mem = (frozenset(new_used), mem[1])
                else:
                    new_mem = (mem[0], frozenset(new_used))
            if not mover_wins(new_occ, 1 - player, new_mem):
                return True
        return False

    return mover_wins(frozenset(), 0, (frozenset(), frozenset()))
