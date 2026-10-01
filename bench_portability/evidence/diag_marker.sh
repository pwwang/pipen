#!/usr/bin/env bash
# Diagnose marker-line accounting in the reduced run + A/B for the 9p mount.
set -uo pipefail

OUT=/mnt/f/E/hermes-workspace/pipen/bench_portability/out_clean_run
PY=/home/pwwang/ws_bench/.venv/bin/python
BENCH=/mnt/f/E/hermes-workspace/pipen/bench
W=/home/pwwang/ws_bench/work

echo "=== marker files under OUT_ROOT/markers (OUT_ROOT is on the 9p mount /mnt/f) ==="
for f in "$OUT"/markers/*.log; do
  printf "%6d lines  %s\n" "$(wc -l < "$f")" "$f"
done

echo
echo "=== ground truth: job dirs actually created in the caching-scope workdir ==="
find "$W/wd_s5_scope" -name job.script | wc -l
echo "(scaling/concurrency workdirs are deleted after every rep, as designed)"

echo
echo "=== pipen's own job accounting for the scope cold phase ==="
grep -nE "Cached jobs|Cached|jobs:" "$OUT/logs/s5_r1_cold.log" | head -20

echo
echo "=== agg.txt exported by the scope run (must contain N lines per branch) ==="
cat "$OUT/CachePipeline-output/Agg/agg.txt" 2>/dev/null | head -30

echo
echo "=== A/B: identical DAG, marker log on ext4 vs on the 9p mount ==="
cd "$BENCH"
for where in ext4 9p; do
  if [ "$where" = ext4 ]; then M="$W/marker_ab_ext4.log"; else M="$OUT/marker_ab_9p.log"; fi
  : > "$M"
  BENCH_N=20 BENCH_FORKS=8 BENCH_SLEEP=0.05 BENCH_CACHE=0 BENCH_WORKDIR="$W/ab_$where" \
    BENCH_MARKER="$M" "$PY" bench_pipen_dag.py > "$W/ab_$where.log" 2>&1
  echo "marker on $where: $(wc -l < "$M") lines   [expect 42 = 21 jobs x (start+end)]"
done
echo
echo "=== mounts involved ==="
mount | grep -E "on /mnt/f |on / "
