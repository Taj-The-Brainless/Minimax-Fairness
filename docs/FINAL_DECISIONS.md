# Final decisions for the experiment and the report

These settle the DECIDE items in `rules.md` for the final run. Say them on a slide or in the report.

| Item | Decision | Why |
|---|---|---|
| Memory rule, stuck case | `lose` is the main setting; `reset` is run as a comparison (tier `rules`) | one clear rule; the alternative is checked |
| Pie rule | not run in the final grid; reported as theory only | under perfect play the second seat always wins, so exact solving adds nothing; its practical model (balanced first move) is still a modelling choice |
| Evaluation functions | `zero` and `mobility` only | `parity` was a placeholder; `mobility` carries no information in Cram-like variants (identical to `zero`) |
| Misère, no-repeat memory | exploratory results (tier `rules`) | implemented and tested against the reference solver |
| Extra tile shapes (i4, t4, l4, o4) | implemented and tested, but not in the default final run (tier `extra`) | keeps the main claims on the best-checked variants |
| Mirror / symmetry | `symmetry.py` proves pairing strategies and labels variants (`mirror_proved`); not removed from the data | those variants are where "balanced in practice" means "weak search", so they are reported separately |
| General mirror-strategy player | not implemented (future work) | the checker already tells us where the strategy exists |

## How fairness is judged
- Practical fairness = first player's win rate between equal-depth players (same evaluation, random tie-breaking), 95% Wilson interval.
- "balanced" = the interval contains 0.5. (A rule like "inside 45%-55%" cannot be met with 200 games: the interval is about +-7 points.)
- Always read it as "balanced against depth-limited players"; a variant with a proved pairing strategy can look balanced and still be decided by a simple strategy.
- Compare variants at the same depth (default depth 3, which exists for every tier) and stratify by board size and parity before comparing rules.

## Limits to state
- Boards up to 6x6; larger or harder variants hit the node limit (unsolved) or the per-variant timeout, and no exact winner exists for them (their practical fairness is still measured).
- Results depend on the evaluation function and on random tie-breaking.
- Solved variants are the smaller ones, which biases accuracy statements toward smaller boards.
