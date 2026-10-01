#!/usr/bin/env bash
# Calibration: one run each at N=1 and N=500 to size the full matrix.
set -u
VP="$HOME/bench/.venv/bin"
OUT="$HOME/bench/out"
BENCH=/mnt/f/E/hermes-workspace/pipen/bench
mkdir -p "$OUT"

run_one () {
  local n="$1" forks="$2" tag="$3"
  rm -rf "$HOME/bench/wd_cal_$tag"
  : > "$OUT/marker_cal_$tag.log"
  local t0 t1
  t0=$(date +%s.%N)
  BENCH_N="$n" BENCH_FORKS="$forks" BENCH_SLEEP=0.05 BENCH_CACHE=0 \
    BENCH_WORKDIR="$HOME/bench/wd_cal_$tag" BENCH_MARKER="$OUT/marker_cal_$tag.log" \
    "$VP/python" "$BENCH/bench_pipen_dag.py" > "$OUT/cal_$tag.log" 2>&1
  local rc=$?
  t1=$(date +%s.%N)
  echo "$tag N=$n forks=$forks rc=$rc wall=$(echo "$t1 - $t0" | bc -l) $(grep -o 'PIPELINE_RUN_SEC=[0-9.]*' "$OUT/cal_$tag.log" | tail -1) jobs_executed=$(wc -l < "$OUT/marker_cal_$tag.log")"
}

run_one 1 32 n1
run_one 100 32 n100
run_one 500 32 n500
