#!/usr/bin/env bash
# Diagnostic: where does the wall time go? N=100 at forks=32, with and without the sleep.
set -u
VP="$HOME/bench/.venv/bin"
OUT="$HOME/bench/out"
BENCH=/mnt/f/E/hermes-workspace/pipen/bench
mkdir -p "$OUT"
{
  echo "=== load before ==="; uptime
  echo "=== other python/bench processes ==="; ps -eo pid,pcpu,etime,cmd --sort=-pcpu | head -12
} > "$OUT/diag_load.txt" 2>&1

run_one () {
  local n="$1" forks="$2" slp="$3" tag="$4"
  rm -rf "$HOME/bench/wd_diag_$tag"
  : > "$OUT/marker_diag_$tag.log"
  local t0 t1
  t0=$(date +%s.%N)
  BENCH_N="$n" BENCH_FORKS="$forks" BENCH_SLEEP="$slp" BENCH_CACHE=0 \
    BENCH_WORKDIR="$HOME/bench/wd_diag_$tag" BENCH_MARKER="$OUT/marker_diag_$tag.log" \
    "$VP/python" "$BENCH/bench_pipen_dag.py" > "$OUT/diag_$tag.log" 2>&1
  local rc=$?
  t1=$(date +%s.%N)
  echo "$tag N=$n forks=$forks sleep=$slp rc=$rc wall=$(echo "$t1 - $t0" | bc -l) $(grep -o 'PIPELINE_RUN_SEC=[0-9.]*' "$OUT/diag_$tag.log" | tail -1) marker_lines=$(wc -l < "$OUT/marker_diag_$tag.log")"
}

run_one 100 32 0.05 sleep05
run_one 100 32 0 nosleep
run_one 100 1 0.05 forks1

echo "=== stage timing (sleep05) ==="
grep -nE "START|END|workdir:|Cached|>>>|<<<" "$OUT/diag_sleep05.log" | head -20
echo "=== first/last log lines ==="
head -3 "$OUT/diag_sleep05.log"
