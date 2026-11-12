# Validation of the exact solver against published results

## 1. Objective

Compare the project's independently implemented solver with externally published outcomes for standard Cram and Domineering. Passing tests supports correctness on these instances; it does not prove correctness for all games, states, or rules.

## 2. Methodology

All boards are empty rectangles. Dimensions below are **rows × columns**. Both games use non-overlapping dominoes and normal play: the player with no legal move loses. Cram allows either orientation to both players; standard Domineering assigns vertical dominoes to the first player and horizontal dominoes to the second. No memory or pie rule is enabled. In `Variant`, width is columns and height is rows; `partisan=True, first_orientation="v"` models these Domineering conventions. No rotations are assumed to preserve winner without also transforming player orientations.

The script `validation/run_benchmarks.py` runs each exact solver in a separate process, using the existing transposition table and a node cap of 2,000,000, with a 10-second wall-clock cap per process. It additionally runs `reference_first_wins` on boards of at most 12 cells with a separate 10-second cap. A non-completing exact solve is INCONCLUSIVE; an exact match and a reference match when available is PASS. A disagreement is FAIL. Reference not run on larger cases for cost, not because it failed. Times below are exact solver `perf_counter` durations and vary between runs. The node count increments on every call, including table hits; a node-limit abort would report 2,000,001. No solver optimization was added.

Implementation inspection (paths relative to this copied project):

- `src/pfair/rules.py`: `Variant` defines configuration; `Rules.initial_state` returns `(occupied_mask, side_to_move, mem0, mem1)`. `_gen` makes non-overlapping legal placements from precomputed shape masks; `successors` returns an empty list for a terminal position. `key` keeps only state relevant to the variant.
- `src/pfair/solver.py`: `ExactSolver.wins` checks whether any successor loses for the opponent; with no legal move it returns false. It stores exact Boolean outcomes under `Rules.key` in `self.tt`. `solve` catches `NodeLimitExceeded` and marks the result unsolved. There is no built-in wall-clock timeout; the validation runner supplies the process timeout. `solve_variant(v,node_limit=...,use_tt=True)` runs one configuration.
- `src/pfair/reference.py`: `reference_first_wins` independently generates moves with occupied-cell sets and runs plain recursive search without the exact solver's move generator or transposition table. It shares the `Variant` configuration type, so it is not independent of the problem specification.
- `tests/test_solver.py` already has parity and hand checks and comparison against the reference solver, but had a TODO for cited published benchmarks. `src/pfair/cli.py` and `src/pfair/experiments.py` run preset grids; the validation runner directly calls the single-variant API.

## 3. Published benchmarks

- **U2020-T1/T2:** Jos W. H. M. Uiterwijk, “Solving Cram using Combinatorial Game Theory,” *Advances in Computer Games*, pp. 91–105, 2020, Theorems 1–2. Theorem 1 gives second-player wins for even × even empty Cram boards; Theorem 2 gives first-player wins for even × odd boards (including transposes). [DOI](https://doi.org/10.1007/978-3-030-65883-0_8); [author-institution record](https://cris.maastrichtuniversity.nl/en/publications/solving-cram-using-combinatorial-game-theory/); [accessible theorem text](https://www.researchgate.net/publication/347759227_Solving_Cram_Using_Combinatorial_Game_Theory).
- **L2002:** Michael Lachmann, Cristopher Moore and Ivan Rapaport, “Who Wins Domineering on Rectangular Boards?”, *More Games of No Chance*, MSRI Publications 42, 2002, pp. 307–316, especially Figure 1, p. 312, and rules on p. 307. [Full paper](https://library.slmath.org/books/Book42/files/lachmann.pdf). Figure 1 labels 1 = player moving first, 2 = player moving second, V = vertical, H = horizontal. Since vertical goes first here, 1/V map to first and 2/H map to second. Figure 1 gives rows × columns; e.g. 2×4 is H while 4×3 is V. The paper draws on some prior computer results; it is independent of this implementation, not necessarily an independent derivation of every published entry.

## 4. Experimental results

| Game | Board rows×columns | Source | Published | Exact | Reference | Exact nodes | Exact seconds | Result |
|---|---:|---|---|---|---|---:|---:|---|
| Cram | 2×2 | U2020-T1 | second | second | second | 9 | 0.000011 | PASS |
| Cram | 2×4 | U2020-T1 | second | second | second | 70 | 0.000038 | PASS |
| Cram | 4×4 | U2020-T1 | second | second | not_run_size | 7832 | 0.004167 | PASS |
| Cram | 2×3 | U2020-T2 | first | first | first | 18 | 0.000017 | PASS |
| Cram | 3×2 | U2020-T2 | first | first | first | 10 | 0.000017 | PASS |
| Cram | 3×4 | U2020-T2 | first | first | first | 217 | 0.000131 | PASS |
| Domineering | 2×2 | L2002 | first | first | first | 2 | 0.000008 | PASS |
| Domineering | 2×3 | L2002 | first | first | first | 4 | 0.000010 | PASS |
| Domineering | 2×4 | L2002 | second | second | second | 16 | 0.000018 | PASS |
| Domineering | 2×5 | L2002 | first | first | first | 34 | 0.000030 | PASS |
| Domineering | 3×3 | L2002 | first | first | first | 10 | 0.000017 | PASS |
| Domineering | 3×4 | L2002 | second | second | second | 150 | 0.000090 | PASS |
| Domineering | 4×3 | L2002 | first | first | first | 36 | 0.000033 | PASS |
| Domineering | 4×4 | L2002 | first | first | not_run_size | 710 | 0.000550 | PASS |
| Domineering | 5×5 | L2002 | second | second | not_run_size | 234578 | 0.139935 | PASS |

Results are also stored in `validation/benchmark_results.csv`, including reference runtimes and completion status. Results reflect one run on Python 3.13.9 on macOS; timings are not universal.

## 5. Correctness assessment

15 PASS, 0 FAIL, 0 INCONCLUSIVE. All 15 exact results agree with the published results. The independent reference implementation also agrees on all 12 selected boards with at most 12 cells; it was not run for the three larger cases. The 15 cited cases were added as parametrized regression tests. Original suite: 97 passed in 0.44 s; expanded suite: 112 passed in 0.57 s.

## 6. Limitations

These cases cover standard empty-board games, not extra tile shapes, memory, pie, arbitrary partial positions, every orientation or large boards. Some even/odd Cram benchmarks instantiate the same general theorem, so 15 are not 15 independent theorems. The published results sometimes rely on theoretical symmetry or prior computer searches. Reference search is bounded and not run on larger boards. Published agreement is external evidence, not a mathematical proof of implementation correctness. Execution time and nodes are implementation-dependent. The project's node cap and runner's wall timeout are different: reaching either leaves a case inconclusive, not failed. No conclusion is drawn about the six prior unsolved Cram rows or their theoretical outcomes.

## 7. Conclusion

The tested solver agrees with the selected published Cram and Domineering results, including rectangular orientation-sensitive cases, and with the independent implementation on small cases. This supports using its answers for the tested standard configurations but does not validate every variant or constitute proof.

## Reproduction

From this copied project's root (Python 3.10+, pytest installed):

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -u validation/run_benchmarks.py
```

The latter overwrites only `validation/benchmark_results.csv` within this copy. To run one variant directly:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -c 'from pfair.rules import Variant; from pfair.solver import solve_variant; print(solve_variant(Variant(width=4,height=2,partisan=True),node_limit=2000000))'
```
