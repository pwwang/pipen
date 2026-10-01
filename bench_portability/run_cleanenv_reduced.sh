#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Reduced-size portability verification of the bench harness.
#
# This is NOT the published protocol: it runs the same driver code paths at
# small N (N=20 scaling, N=20 concurrency at 2 fork levels, N=8 caching scope,
# N=20 cold/warm caching) against a clean virtualenv created by setup_env.sh at
# ~/ws_bench/.venv (pipen) and ~/ws_bench/smk-venv (snakemake) - deliberately
# different paths from the archived ~/bench/.venv and ~/bench/smk.
#
# Outputs: bench_portability/out_clean_run/ (artefacts) and
#          bench_portability/run_logs/01_run_all_reduced.log (verbatim console)
# ---------------------------------------------------------------------------
set -uo pipefail

BENCH=/mnt/f/E/hermes-workspace/pipen/bench
PORT=/mnt/f/E/hermes-workspace/pipen/bench_portability
OUT="$PORT/out_clean_run"
LOGS="$PORT/run_logs"
mkdir -p "$LOGS"
rm -rf "$OUT"

cd "$BENCH"
export BENCH_NPROC=8
export BENCH_REPS=1
export BENCH_SCALING_NS=20
export BENCH_CONC_FORKS=1,2
export BENCH_CACHE_SCOPE_N=8
export BENCH_CACHE_TIMING_N=20
export BENCH_CACHE_TIMING_REPS=1
export BENCH_WORK_ROOT=/home/pwwang/ws_bench/work

echo "### verification: reduced-size run, clean venvs at ~/ws_bench/{.venv,smk-venv}"
bash run_all.sh "$OUT" 2>&1 | tee "$LOGS/01_run_all_reduced.log"
rc=${PIPESTATUS[0]}
echo "RUN_ALL_RC=$rc" | tee -a "$LOGS/01_run_all_reduced.log"
exit "$rc"
