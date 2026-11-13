import csv,platform,sys
from pathlib import Path
p=Path('fairness_experiment'); rows=list(csv.DictReader((p/'summary.csv').open())); pilots=list(csv.DictReader((p/'pilot_summary.csv').open()))
table='\n'.join(f"| {r['game']} | {r['size']}×{r['size']} | {r['depth']} | {r['evaluation']} | {r['wins']}/{r['n']} | {float(r['rate']):.3f} | [{float(r['ci_low']):.3f}, {float(r['ci_high']):.3f}] | {r['classification']} | {float(r['mean_seconds']):.4f} | {float(r['mean_plies']):.2f} | {r['exact_winner']} | {r['exact_nodes'] or '—'} | {r['dstar'] or '—'} |" for r in rows)
pilottable='\n'.join(f"| {r['game']} | {r['size']}×{r['size']} | {r['depth']} | {r['n']} | {float(r['wins'])/int(r['n']):.3f} | {float(r['mean_seconds']):.4f} | {float(r['mean_plies']):.2f} | {r['failures']} |" for r in pilots)
text='''# Practical fairness experiments on larger boards

## Research question and hypotheses

Can a theoretically unfair placement game appear approximately balanced when identical players use limited search? The predefined operational target is a true first-seat win probability p between 0.45 and 0.55, under each specified policy and rule set. A 95% Wilson interval entirely inside this region is treated as evidence supporting the target for that individual condition; an interval entirely outside is evidence against it, otherwise inconclusive. This is a confidence-interval equivalence criterion, not a claim of universal game fairness. The prediction that increasing size necessarily moves p towards 0.5 is exploratory; no monotonic trend or causal inference is assumed.

## Design

- Board sizes: 4×4, 5×5 baseline, 6×6 main extension, 7×7 and 8×8 extensions. All empty, rectangular squares, standard normal play.
- Two rule configurations: Cram (domino, both orientations, impartial, eval zero); Domineering (domino, vertical side moves first, horizontal second, eval mobility). Memory off and pie off in every new match, no random opening. This choice isolates standard games and avoids unresolved pie-policy decisions. Memory and pie were not investigated here.
- Both player objects use the project's `Player`, `DepthLimited` alpha-beta, TT, and one depth per condition: 1 or 2. Best moves selected by depth-limited search; tied best moves are uniformly sampled using Python's pseudo-random generator. Cram mobility is identically zero; zero is used. Comparing games changes both rules and evaluation; do not attribute observed differences to rules alone. Each size comparison within a given game/depth keeps policy fixed.
- Each game constructs fresh player objects and fresh tables. Seeds are `int.from_bytes(SHA256(f"{base_seed}:{match_index}")[:8], "big")`, base seed 20261113. The same seed indices are used across conditions; the trajectories are not identical and observations across conditions can be correlated. Within a condition, distinct pseudo-random seeds model independently randomized matches, subject to PRNG assumptions. Two identically configured agent objects alternate the A/B label assigned to the starting seat; they share the same RNG as in the existing implementation. Agent labels are operationally exchangeable, not a comparison of different agent strengths.
- Main analysis uses n=200 per condition except 6×6, where n=1000. The first 200 6×6 games were rerun as part of the 1000 using the same seeds; only the 1000-run rows are included in the combined dataset. 7,200 distinct condition/seed observations in the combined main file; actual main executions total 8,000 including the 800 repeated matches. Pilot 400 games and reproducibility checks 24 additional executions are not included in main estimates.
- Each game has a 10-second SIGALRM timeout; failures are logged and omitted from the estimate with counts reported. All 7,200 main games completed. This Unix timeout is platform-dependent. Runtime is wall time per game; concurrent workloads affect it. Python '''+platform.python_version()+''' on macOS; base seed and policy configuration are recorded per row.
- Wilson 95% intervals use `pfair.players.wilson` (z=1.96). Intervals are approximate, individual-condition, and unadjusted for 20 comparisons; the near-fair classification is exploratory and selection/multiple comparisons can inflate false-positive risk. They are not causal tests. Distances from 50%, per-game seeds, swap flag, plies, statuses and mean timings are in CSVs.

## Pilot feasibility: 20 games per condition

| Game | Board | Depth | Completed | First-seat rate | Mean sec/game | Mean plies | Failures |
|---|---|---:|---:|---:|---:|---:|---:|
'''+pilottable+'''

Pilot results were used for runtime feasibility only, not merged into main results. Main and pilot use overlapping seeds. The slowest pilot configuration was 8×8 Cram at depth 2, approximately 0.60 s/game, implying roughly two minutes for 200 games on this machine. Choice of 6×6 n=1000 was made after initial pilot and some main observations; resulting evidence is exploratory, not a prespecified confirmatory analysis.

## Main results

`not_available` means not present in prior exact dataset; `unsolved` means the earlier exact solver reached its 2,000,000-node limit. Exact winner is the *base-game first/second role* with no pie. d* is from the earlier dataset for the same evaluation; it is the settling depth when the full search finished, not necessarily a match depth. The prior exact results were not recomputed here. The prior 5×5 Cram base row is unsolved; other results from an earlier experimental symmetry prototype are deliberately not merged.

| Game | Board | Depth | Eval | Wins/n | Rate | 95% Wilson CI | Equivalence assessment | Sec/game | Plies | Exact | Exact nodes | d* |
|---|---|---:|---|---:|---:|---|---|---:|---:|---|---:|---:|
'''+table+'''

## Interpretation

- The first-seat win rate does not decrease consistently with board size across these settings. For example, Domineering at depth 1 is 0/200 on 4×4 but 1000/1000 on 6×6; at depth 2 it is 44/200 versus 997/1000. Cram rates fluctuate around 0.5 without a demonstrated monotone relationship. These are descriptive comparisons; no formal trend or difference test was carried out.
- Only 6×6 Cram at depth 1 has its 95% Wilson interval wholly within [0.45, 0.55]: 491/1000, CI approximately [0.460, 0.522]. This is individual-condition, exploratory evidence, not proof or a multiple-testing-adjusted claim. The depth-2 condition is 460/1000 with an interval crossing 0.45, so its near-fair assessment is inconclusive. All 200-game intervals intersecting the equivalence region are too wide to establish it by the specified criterion.
- Domineering often differs sharply from Cram, and depth can matter: on 7×7, Domineering rates are 107/200 at depth 1 and 193/200 at depth 2. Because the two game types use different evaluation functions and have different roles, this is not an isolated causal estimate of the rule change. Same-seed comparisons have not been subjected to paired significance tests.
- For 4×4 Cram, prior exact search says second wins, yet first seat wins 102/200 at depth 2: an example consistent with theoretical unfairness coexisting with approximately balanced play under these policies, though its confidence interval is too wide to establish the 45–55% range. 4×4 Domineering has an exact first-player win but first wins only 44/200 at depth 2, showing a reversal can also occur. Ground truth for earlier 5×5 Cram run was unsolved. Larger-game exact outcomes are not assumed or computed here.
- Three unique solved standard 4×4/5×5 cases do not support any general conclusion about the association between exact nodes/d* and practical fairness. The exact-node figure is descriptive; it is not a regression. Raw exact-node measures depend on move order, TT implementation, and stopping behavior.

## Previous reported findings

The supplied previous `exact.csv` has 256 records: 250 solved base-game results and 6 node-limit records, with pie/non-pie entries sharing underlying exact solves. It does not represent 250 independent exact searches. From all rows in the previous `matches.csv`, the unweighted mean of `side0_rate` across 2×2 rows is 0.543125 (128 rows) and across available 5×5 rows is 0.424125 (80 rows). These averages combine different rules, depths, and pie settings, exclude rows without exact results, and use side-0 role rather than necessarily the original first seat, so they are not suitable as fairness estimates. The previously stated 0.92 and 0.51 cannot be verified without its original selection and aggregation methodology. Search complexity is not demonstrated to grow exponentially by these observations.

## Figures

![Win rate versus size](fairness_experiment/plots/win_rate_by_size.png)
![Runtime versus size](fairness_experiment/plots/runtime_by_size.png)
![Rule comparison](fairness_experiment/plots/rule_comparison.png)
![Exact search nodes versus distance from 50 percent](fairness_experiment/plots/exact_nodes_vs_fairness.png)

The gray band shows 45%–55%, and error bars are 95% Wilson intervals. Error bars overlapping 0.5 are not proof of fairness. In pie experiments the starting seat and side-0 role may differ; this study excludes pie.

## Validation and limitations

- Relevant automated suite: 112 passed, including 15 published outcome regression tests copied from the user's current project. The prior validation supports tested standard small games, not correctness on every board or every policy.
- Seed reproducibility: two separate 12-game runs produced identical rows excluding runtime. In addition, all 800 6×6 rows repeated in the 200-game and 1000-game runs matched in every non-timing field. Timings need not match.
- These are finite Monte Carlo experiments for specified code/policies, not human play, perfect play, or all algorithms. Samples for n=200 often cannot meet the equivalence criterion; sequential choice of n and multiple comparisons are not controlled. No automatic false-discovery or family-wise correction is applied.
- New experiments do not test pie, memory, random openings or different evaluations for the same game. Depths 1 and 2 are shallow. Run-time measurements may be noisy, particularly because 6×6 and 8×8 runs overlapped.
- Exact winner and d* values come from a previous run and have not been recalculated under the new sampling protocol. Unsolved/not computed is not a claim of theoretical unfairness. Variant rows including pie can duplicate base-game exact work.

## Reproduction commands

Run from the working-copy root on macOS or another Unix-like system, with pytest and matplotlib installed:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -u fairness_experiment/run.py --games 20 --out fairness_experiment/pilot.csv
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -u fairness_experiment/run.py --games 200 --out fairness_experiment/main_200.csv
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -u fairness_experiment/run.py --games 1000 --sizes 6 --out fairness_experiment/main_6x6_1000.csv
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python fairness_experiment/combine.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src MPLCONFIGDIR=/tmp/pfair-fairness-mpl XDG_CACHE_HOME=/tmp/pfair-fairness-cache python fairness_experiment/analyze.py
PYTHONDONTWRITEBYTECODE=1 python fairness_experiment/report.py
```

These commands overwrite outputs in this copy. `previous_main` is the saved earlier run used as an input. Source code for players, solver and rules was not changed. Exact node and wall-time budget for the main experiment are not comparable: a per-game 10-second wall-clock timeout is used here, not the exact solver's node limit. Per-game failures would be recorded.

## Next steps

Essential: agree which outcomes and visualizations answer the research questions; verify the 6×6 result with a fresh, prespecified independent seed set and suitable sample size; confirm main exact and d* data provenance; state policy/selection/timeout and multiple-comparison limitations; present the results without claiming universal fairness. Optional: additional depths, matched same-evaluation comparisons, seed-paired inference, predeclared memory/pie studies and larger boards, if time permits.
'''
Path('FAIRNESS_EXPERIMENT_REPORT.md').write_text(text)
