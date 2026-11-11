# Rule decisions (write them down BEFORE running experiments)

Everything marked **DECIDE** needs a team decision. Change the code and this file together.

## Base game
- Players alternately place one tile on an empty board; the player who cannot place loses. No draws.
- Side 0 moves first. Partisan (Domineering-like): side 0 places vertical tiles, side 1 horizontal
  (`first_orientation="h"` swaps this). Impartial (Cram-like): both sides may place any orientation.
- Shapes: `domino`, `i3` (straight tromino), `l3` (L-tromino). `l3` is allowed only in impartial
  variants (it has no vertical/horizontal orientation).

## Memory rule
- A shape cannot be used again until every shape has been used once; then the cycle resets.
- `per_player`: each side has its own cycle. `shared`: one cycle for both sides.
- **DECIDE: what if the player has legal placements only with already used shapes?**
  - `lose` (default in code): the player cannot move and loses.
  - `reset`: the cycle resets and the move is allowed.
  The tests show the choice changes outcomes (e.g. 1x6 with domino + i3, per_player), so pick one
  for the main grid and state it in the report.
- With a single shape, the memory rule changes nothing (reduction test).

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
