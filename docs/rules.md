# Rule decisions (write them down BEFORE running experiments)

Everything marked **DECIDE** needs a team decision. Change the code and this file together.

## Base game
- Players alternately place one tile on an empty board; the player who cannot place loses. No draws.
- Side 0 moves first. Partisan (Domineering-like): side 0 places vertical tiles, side 1 horizontal
  (`first_orientation="h"` swaps this). Impartial (Cram-like): both sides may place any orientation.
- Shapes: `mono` (1 cell), `domino`, `i3` (straight tromino), `l3` (L-tromino), `i4`, `o4` (square),
  `t4`, `l4`, `s4` (tetrominoes; `l4` and `s4` use rotations only, no mirror image).
  Shapes with a square bounding box (`mono`, `l3`, `o4`) are allowed only in impartial variants,
  because they have no vertical/horizontal orientation.
- **Misère play** (`misere=True`): the player who cannot place WINS (the last player to place
  loses). Default is normal play (the player who cannot place loses). The exact solver, the
  depth-limited players and the matches all follow this flag; the evaluation functions do not.
  **DECIDE:** `mobility` assumes "more moves is better", which is questionable in misère; either
  accept that or use only `zero` for misère variants.

## Memory rule
- A shape cannot be used again until every shape has been used once; then the cycle resets.
- `per_player`: each side has its own cycle. `shared`: one cycle for both sides.
- **DECIDE: what if the player has legal placements only with already used shapes?**
  - `lose` (default in code): the player cannot move and loses.
  - `reset`: the cycle resets and the move is allowed.
  The tests show the choice changes outcomes (e.g. 1x6 with domino + i3, per_player), so pick one
  for the main grid and state it in the report.
- With a single shape, the memory rule changes nothing (reduction test).
- **No-repeat rules** (`memory="no_repeat"` / `"no_repeat_shared"`): a player may not place the same
  shape as their own previous move (`no_repeat`) or as the previous move of either player
  (`no_repeat_shared`). They use the same `memory_stuck` setting: `lose` (cannot move, loses) or
  `reset` (the restriction is lifted for that move). Needs 2+ shapes to be meaningful (with one
  shape each player could place only once).

## Pie rule
- After side 0's first move, the second *seat* may swap sides.
- Under perfect play the second seat always wins (it picks whichever side wins the position after
  the first move; no draws). `pie_second_player_always_wins` checks this by brute force and
  `exact.csv` stores `pie_exact_winner = second` for pie variants. The exact solver itself solves the
  base game only.
- In matches (`players.play_game`): seat A picks the first move whose position looks most balanced
  (smallest absolute value) to A's own search, then seat B keeps or swaps by B's own search. Ties in
  B's decision are broken at random.
- **DECIDE:** is this "most balanced first move" rule what we want to call the practical pie rule?

## Evaluation functions (depth-limited players)
- `zero`: no knowledge, only real wins and losses are seen.
- `mobility`: own placements minus opponent placements (ignores the memory rule). Informative for
  Domineering-like variants, always 0 for Cram-like ones (both sides have the same placements).
- `parity`: PLACEHOLDER for impartial variants (+1 if the number of legal moves is odd, else -1).
  **DECIDE:** replace it with something justified, or keep it and say it is a crude baseline.

## Prediction and settling depth d*
- A depth-d search of the initial position gives a root value (side 0's point of view). Predicted
  winner = sign of the value; value 0 = undecided (counted as wrong).
- d* = smallest depth d such that the prediction is correct at depth d and at every deeper depth.
  The search stops once a depth is exhaustive (no depth cut-off), because then it is exact.
- Game length L = `max_plies_bound` = cells // smallest tile area. This is an upper bound, so
  `d_star_rel = d*/L` is a conservative scale; say so in the report.
- `nodes_to_d_star` adds up the nodes of the searches at depths 1..d* (each done from scratch).

## Matches
- Both seats search the same depth d per move. Ties between equally valued moves are broken at random
  (seeded). `random_opening` adds that many random plies for variety.
- `side0_rate` = share of games won by the side that moves first in the base game.
  `theory_winner_rate` = share won by the side that wins under perfect play.

## Exact search limits
- A variant that exceeds `node_limit` is `unsolved`: it is kept in `exact.csv` but excluded from
  depth and match experiments. Report the share of unsolved variants.

## Symmetry (pairing) strategies: `pfair/symmetry.py`
- `analyze_mirror(variant)` looks for a PROVED simple strategy in the base game: answer every
  move with its mirror image (180-degree rotation, a mirror, or a diagonal mirror on square boards).
  Two proofs: (1) second player pairs every first-player tile; (2) first player opens with a
  symmetric tile, then pairs every reply. The result says the winner under perfect play.
- `applicable = False` only means "no proof found". It does NOT mean the variant is fair or that
  no simple strategy exists. The checker refuses misère play and memory rules that can stop the
  reply from using the same shape (shared cycle with 2+ shapes, no-repeat, `reset` with a
  per-player cycle). The pie rule is ignored (like the exact solver, the base game is analysed).
- **Default handling: label, do not delete.** Every row in exact/depth/dstar/matches carries
  `mirror_proved`, `mirror_winner`, `mirror_symmetry`. Variants with a proved pairing strategy are
  exactly where a ~50% depth-limited win rate says "search is weak" and not "the variant is
  fair", so report them as a separate group (or exclude them only from the fairness claim).
  `collect_all.py --drop-mirror --out <other folder>` runs the grid without them, if you want the
  filtered set as well.
- Safety nets: `tests/test_symmetry.py` and `run_variant` both check that a claimed winner equals
  the exact solver's result; a mismatch means a bug in the checker.
