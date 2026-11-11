# Fairness of rule variants of placement games

Exact alpha-beta solving of many rule variants (Cram/Domineering-like, extra tile shapes, memory
rule, pie rule), plus depth-limited alpha-beta players that measure how deep the search must be
(settling depth d*) to find the winner.

## Quick start

```bash
pip install -r requirements.txt
pip install -e .                      # or prefix commands with PYTHONPATH=src
python -m pytest                      # all tests must pass before you trust any result
python -m pfair.cli run --grid pilot --out results/pilot --games 50 --match-depths 1,2,3
python collect_all.py                 # everything: full MAIN grid, resumable, then plots
python -m pfair.analysis results/pilot   # writes results/pilot/plots/*.png
```

## Layout

```
src/pfair/
  rules.py        Variant (parameters) and Rules (placements, successors, state key)
  solver.py       exact solver (alpha-beta on win/lose + transposition table), node limit
  reference.py    deliberately simple, independent solver used only to validate the fast one
  players.py      depth-limited alpha-beta, evaluations, d* (depth_table, settling_depth), matches
  experiments.py  variant grids (PILOT, MAIN), Config, run_variant, run_grid, CSV output
  cli.py          command line
  analysis.py     the four plots of the proposal
tests/            rules, solver (theory, reference, symmetry, reduction, pie), players
docs/rules.md     rule decisions (fill in the DECIDE items first)
results/          CSV output per run (exact, depth, dstar, matches)
```

## How it maps to the proposal

| Proposal part | Code / file |
|---|---|
| Question 1 (winner, cost) | `exact.csv`: winner, nodes, tt_entries, nodes_no_tt; plots 1 and 3 |
| Question 2 (depth, practical balance) | `dstar.csv` (d*, d*/L, nodes to d*), `matches.csv`; plots 2 and 4 |
| Correctness check 1-4 | `tests/test_solver.py` (reduction, symmetry, two implementations, hand checks) |
| Unsolved variants / node limit | `Config.node_limit`, `winner == "unsolved"` |

## Suggested order of work

1. **Day 1:** fill in `docs/rules.md` (the DECIDE items). Run the tests and the pilot grid.
2. **Week 1:** add published results to `tests/test_solver.py` (see the TODO there, with the source and the
   player convention), so the solver is checked against the literature.
3. **Week 2:** choose the main grid (`experiments.MAIN`) from a pilot of board sizes: find the largest size
   that mostly solves within the node limit. Run it in chunks (`--limit`, several output folders).
4. **Week 3:** pick evaluations, run `depth` and `matches`, check that results do not hinge on one evaluation.
5. **Week 4:** plots, report. Add the mirror-strategy player and symmetry handling only if time remains.

Splitting the work: one person owns `rules.py`/`solver.py`/`reference.py` and the tests (ground truth);
the other owns `players.py`/`experiments.py`/`analysis.py` (experiments). Review each other's tests.

## Performance notes (measured on the machine used to build this, yours may be 2-5x slower)

- About 1 million nodes per second. Plain Cram 5x5 took about 2 million nodes (2 s); Domineering 6x6
  exceeded a 5 million node limit. Memory-rule variants multiply the state space.
- `PyPy` runs this code unchanged and is often much faster (try it). If Python is still too slow, the hot loop
  (`ExactSolver.wins` and `Rules.successors`) is small and can be rewritten in C/C++ and called from Python.
- Results are written after every variant, so a long run can be stopped and resumed on a smaller grid.

## Known limits (TODO)

- No published-results tests yet (needs the tables from the papers).
- `eval_parity` is a placeholder. The mirror-strategy player and symmetry handling are not implemented.
- Matches use a full-window search for every root move to detect ties; this is simple but slower than needed.
- `MAIN` grid values are guesses until the pilot is done.
