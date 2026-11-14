# Mirror-strategy control experiment

## Question

What happens when the second player follows the known 180-degree rotational response strategy instead of using the same shallow search policy as the first player? This is a control for the earlier Cram experiments, not a general claim about other games or rule variants.

## Method

- Standard impartial Cram: dominoes only, empty 4×4 or 6×6 board, both orientations, no pie and no memory. The player with no legal move loses.
- First player: project's existing depth-limited alpha-beta `Player`, zero evaluation, search depth 1 or 2, randomized tie-breaking. Second player: after each first-player move, place a domino at the position obtained by rotating that move 180° about the board centre. The code asserts that the reply is a legal, unique successor. Other board types, partisan play, pie and memory are rejected.
- 1,000 matches per condition; 4,000 completed, zero timeouts/errors. Each match uses a seed derived from SHA-256 of `20261113:match_index`, following the earlier experiment's seed scheme. Each game has a 10-second wall-time limit and a fresh first-player search object. The mirror player does not use random search.
- Baseline values below are loaded from the earlier `fairness_experiment/summary.csv`, where both sides used the same depth-limited search and zero evaluation. Earlier 4×4 baseline n=200; 6×6 baseline n=1,000. Baseline and mirror runs use overlapping seeds, but decisions consume randomness differently; no paired significance test was performed. They differ in second-player policy, so the comparison measures policy dependence in these conditions, not an effect of board size alone.

| Board | First-player depth | Baseline: first wins / n | Baseline rate | Mirror control: first wins / n | Mirror rate | 95% Wilson interval for first win rate in mirror matches |
|---|---:|---:|---:|---:|---:|---|
| 4×4 | 1 | 108/200 | 54.0% | 0/1000 | 0% | [0%, 0.383%] |
| 4×4 | 2 | 102/200 | 51.0% | 0/1000 | 0% | [0%, 0.383%] |
| 6×6 | 1 | 491/1000 | 49.1% | 0/1000 | 0% | [0%, 0.383%] |
| 6×6 | 2 | 460/1000 | 46.0% | 0/1000 | 0% | [0%, 0.383%] |

All match-level results are in `matches.csv`; aggregates and baseline confidence intervals are in `summary.csv`. Wilson intervals are approximate under the random-seed sampling model. Zero observed losses does not on its own prove a zero loss probability.

## Mathematical context and limitations

On an empty even-by-even standard Cram board, 180-degree rotational pairing provides a second-player winning strategy. The symmetry argument is separate from the 4,000 simulations: paired cells lie in the same checkerboard colour class under rotation, so a single domino cannot be invariant under a 180-degree rotation about an even-by-even board's centre. After each pair of moves, occupancy is symmetric; consequently a rotated reply to the first player's next legal domino is unoccupied and legal. The finite board guarantees termination. This argument is specific to the stated rules and board parity; it does not establish the result for odd×odd boards, partisan games, memory or pie rules. See Uiterwijk, *Solving Cram using Combinatorial Game Theory* (2020), Theorem 1, https://doi.org/10.1007/978-3-030-65883-0_8.

The contrast illustrates why the previous 49.1% result is a property of the two limited-search policies, not proof that standard 6×6 Cram is theoretically fair. It does not prove that a limited-search player failed to discover a winning strategy: on this board the theoretical winner is the second player, and the second player's strategy is supplied explicitly in the control.

## Verification and reproduction

Original project source files were not modified; this experiment was added to the separate working copy. Automated checks: 112 existing tests plus 10 mirror-specific tests, 122 passed. The new tests check transformed placements, involution, no overlap, sample games and rejection of unsupported rules. Tests do not replace the general symmetry argument.

Run from the project working-copy root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m pytest -p no:cacheprovider tests mirror_experiment/test_mirror.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -u mirror_experiment/run_mirror.py --games 1000 --sizes 4,6 --depths 1,2 --out mirror_experiment/matches.csv
```

The second command overwrites the match CSV inside the copy. Wall-clock measurements vary. The test and runner depend on the existing project's `pfair` package. The baseline data and reporting code live in `fairness_experiment/` in the separate working copy.
