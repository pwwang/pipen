#!/usr/bin/env bash
set -u
O="$HOME/bench/out"
echo "=== Agg-related lines in r1_cold log ==="
grep -n -iE "agg|error|traceback|Trace|Exception|cached" "$O/logs/s5_r1_cold.log" | tail -40
echo
echo "=== Agg workdir ==="
find "$HOME/bench/wd_s5_scope/CachePipeline/Agg" -maxdepth 2 2>/dev/null | head -20
echo "=== Agg job script ==="
cat "$HOME/bench/wd_s5_scope/CachePipeline/Agg/0/job.script" 2>/dev/null
echo
echo "=== Agg stdout/stderr ==="
cat "$HOME/bench/wd_s5_scope/CachePipeline/Agg/0/job.stdout" 2>/dev/null | head -20
cat "$HOME/bench/wd_s5_scope/CachePipeline/Agg/0/job.stderr" 2>/dev/null | head -30
echo "=== Agg rc ==="
cat "$HOME/bench/wd_s5_scope/CachePipeline/Agg/0/job.rc" 2>/dev/null
echo
echo "=== marker file ==="
cat "$O/marker_s5_scope.log"
echo "=== exported output dir ==="
find "$HOME/bench/wd_s5_scope" -name "agg.txt" 2>/dev/null
ls "$HOME/bench/bench-out" 2>/dev/null
