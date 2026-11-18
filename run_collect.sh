#!/usr/bin/env bash
# Parallel data collection for the placement-fairness project.
# Put this file in the project root (next to collect_final.py) and run:
#
#   chmod +x run_collect.sh
#   caffeinate -i nohup ./run_collect.sh all > results/master.log 2>&1 &
#   while true; do clear; ./run_collect.sh status; sleep 30; done      # live progress (Ctrl-C to leave)
#
# Single steps:  ./run_collect.sh patch | p1 | p2 | p3 | p4 | retry | merge | status
# Every phase is resumable: if it stops (budget, Ctrl-C, sleep), run the same step again.
#
# Settings you may override:  N=4 (parallel shards)  NODE=12000000 (node limit of the re-solve)  PY=python3

set -u
cd "$(dirname "$0")"
PY=${PY:-python3}
N=${N:-4}
NODE=${NODE:-12000000}
mkdir -p results

ts() { date +%H:%M:%S; }

# --- one-time, idempotent patch of collect_final.py --------------------------------------------
# 1) big tier used to be capped at 60 games per row: use --games instead (200)
# 2) big tier used to stop at depth 3: allow depth 4 too
patch() {
  if grep -q 'min(games, 60)' collect_final.py; then
    cp collect_final.py collect_final.py.bak
    sed -i.sedbak 's/min(games, 60)/games/; s/"match_depths": (1, 2, 3)}/"match_depths": (1, 2, 3, 4)}/' collect_final.py
    rm -f collect_final.py.sedbak
    echo "[$(ts)] patched collect_final.py (backup: collect_final.py.bak)"
  else
    echo "[$(ts)] collect_final.py already patched"
  fi
}

# --- run one phase as N parallel shards, each with its own folder results/<name>_<k> ------------
run_phase() {   # usage: run_phase <name> <budget-minutes-per-shard> <collect_final args...>
  local name=$1 budget=$2
  shift 2
  echo "[$(ts)] phase $name: $N shards, budget $budget min each"
  local pids=()
  local k
  for k in $(seq 0 $((N - 1))); do
    $PY collect_final.py --shard "$k/$N" --out "results/${name}_$k" \
        --budget-minutes "$budget" "$@" > "results/${name}_$k.stdout" 2>&1 &
    pids+=($!)
  done
  wait "${pids[@]}"
  echo "[$(ts)] phase $name finished (if a shard hit its budget, run './run_collect.sh $name' again to continue)"
}

# P1: better ground truth. Re-solve core+rules variants with a higher node limit and redo d*.
#     (matches of these tiers are kept from the earlier run, so no matches here)
p1() { run_phase p1 70 --tiers core,rules --stages exact,depth --node-limit "$NODE"; }

# P2: big boards (up to 6x6): 200 games instead of 60, depths 1-4 instead of 1-3, higher node limit.
p2() { run_phase p2 100 --tiers big --games 200 --node-limit "$NODE"; }

# P3: pie rule, practical play only (exact result of pie is always "second", see FINAL_DECISIONS.md).
p3() { run_phase p3 30 --tiers pie --stages exact,matches --games 200; }

# P4: deeper players (depth 5 and 6) on boards up to 20 cells, 100 games.
p4() { run_phase p4 50 --tiers core,rules --max-cells 20 --match-depths 5,6 --games 100 --stages exact,matches; }

# --- RETRY: the 3 big variants that hit the 900 s timeout in p2 ----------------------------------
# Needs two new options in collect_final.py (--timeout, --only); this patches them in (idempotent).
RETRY_IDS="6x6_domino+i3_impartial,6x6_domino+l3_impartial,6x6_domino+l3_impartial_mem-per_player-lose"

patch_retry() {
  if grep -q '"--only"' collect_final.py; then
    echo "[$(ts)] collect_final.py already has --timeout/--only"
    return
  fi
  cp collect_final.py collect_final.py.bak2
  $PY - <<'PYEOF'
s = open("collect_final.py").read()
a = 'args = p.parse_args()\n'
b = ('p.add_argument("--timeout", type=int, default=0, help="per-variant wall seconds (0 = tier default)")\n'
     'p.add_argument("--only", default="", help="comma-separated variant ids; only these variants are run")\n'
     'args = p.parse_args()\n')
c = '[x for x in v if not args.max_cells or x.width * x.height <= args.max_cells][shard_k::shard_n], t, o)'
d = ('[x for x in v if (not args.max_cells or x.width * x.height <= args.max_cells)\n'
     '                 and (not ONLY or x.vid() in ONLY)][shard_k::shard_n], args.timeout or t, o)')
assert a in s and c in s and 'tiers = {name:' in s, "expected lines not found, patch NOT applied"
s = s.replace(a, b, 1).replace(c, d, 1)
s = s.replace('tiers = {name:', 'ONLY = {x.strip() for x in args.only.split(",") if x.strip()}\ntiers = {name:', 1)
open("collect_final.py", "w").write(s)
print("patched collect_final.py (backup: collect_final.py.bak2)")
PYEOF
}

# Step A: depths 1-3, 200 games, timeout 2 h (should take minutes: earlier these ran in ~80 s at 60 games)
# Step B: depth 4 only, timeout 4 h. If B never finishes you still keep depths 1-3 from step A.
# One process per variant (3 processes).
retry() {
  patch_retry
  local k pids=()
  echo "[$(ts)] retry step A: depths 1-3, timeout 7200 s"
  for k in 0 1 2; do
    $PY collect_final.py --tiers big --only "$RETRY_IDS" --shard "$k/3" --games 200 \
        --match-depths 1,2,3 --node-limit "$NODE" --timeout 7200 --budget-minutes 240 \
        --out "results/t1_$k" > "results/t1_$k.stdout" 2>&1 &
    pids+=($!)
  done
  wait "${pids[@]}"
  pids=()
  echo "[$(ts)] retry step B: depth 4 only, timeout 14400 s"
  for k in 0 1 2; do
    $PY collect_final.py --tiers big --only "$RETRY_IDS" --shard "$k/3" --games 200 \
        --match-depths 4 --stages exact,matches --node-limit "$NODE" --timeout 14400 --budget-minutes 300 \
        --out "results/t2_$k" > "results/t2_$k.stdout" 2>&1 &
    pids+=($!)
  done
  wait "${pids[@]}"
  echo "[$(ts)] retry finished; now run './run_collect.sh merge'"
}

# --- merge everything into results/final_all (+ separate folders for pie / deep / extra) -------
merge() {
  local k main=() pie=() deep=() extra=()
  for p in t2 t1 p2 p1; do for k in $(seq 0 $((N - 1))); do main+=("results/${p}_$k"); done; done
  # highest priority first: new runs win over the earlier results/merged
  $PY merge_results.py --out results/final_all "${main[@]}" results/merged

  for k in $(seq 0 $((N - 1))); do pie+=("results/p3_$k"); done
  $PY merge_results.py --out results/pie_all "${pie[@]}"

  for k in $(seq 0 $((N - 1))); do deep+=("results/p4_$k"); done
  deep+=(results/deep_0 results/deep_1 results/deep_2 results/deep_3)
  $PY merge_results.py --out results/deep_all "${deep[@]}"

  extra=(results/extra_0 results/extra_1 results/extra_2 results/extra_3)
  $PY merge_results.py --out results/extra_all "${extra[@]}"

  echo
  echo "next:  $PY final_analysis.py --dir results/final_all            (main report, depth 3, mobility)"
  echo "       $PY final_analysis.py --dir results/final_all --eval zero  (evaluation check)"
}

# --- progress -----------------------------------------------------------------------------------
status() {
  echo "=== $(date '+%H:%M:%S') ==="
  local d tier last found=0
  for d in results/[pt][1-4]_[0-9]*; do
    [ -d "$d" ] || continue
    [ -f "$d/run.log" ] || continue
    found=1
    tier=$(grep '== tier' "$d/run.log" | tail -1 | cut -c12-90)
    last=$(grep -E '\[[0-9]+/[0-9]+\]' "$d/run.log" | tail -1 | cut -c12-120)
    echo "$d | $tier"
    echo "      last: $last"
  done
  [ $found -eq 0 ] && echo "no run logs yet"
  echo
  echo "running collect_final processes: $(pgrep -f collect_final.py | wc -l | tr -d ' ')"
  echo "(memory: watch Activity Monitor; if it goes red, stop and rerun with NODE=6000000)"
}

all() {
  patch
  p1
  p2
  p3
  p4
  merge
  echo "[$(ts)] all done"
}

case "${1:-}" in
  patch) patch ;;
  p1) p1 ;;
  p2) patch; p2 ;;
  p3) p3 ;;
  p4) p4 ;;
  retry) retry ;;
  merge) merge ;;
  status) status ;;
  all) all ;;
  *) echo "usage: $0 patch|p1|p2|p3|p4|retry|merge|status|all"; exit 1 ;;
esac
