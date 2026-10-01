#!/usr/bin/env bash
set -u
VP="$HOME/bench/.venv/bin"
OUT="$HOME/bench/out"
BENCH=/mnt/f/E/hermes-workspace/pipen/bench
rm -rf "$HOME/bench/wd_probe3"
: > "$OUT/probe3.log"
PROBE_WORKDIR="$HOME/bench/wd_probe3" PROBE_N=4 PROBE_LOG="$OUT/probe3.log" \
  "$VP/python" "$BENCH/probe_agg.py" > "$OUT/probe3_stdout.log" 2>&1
echo "PROBE_AGG_RC=$?" > "$OUT/probe3_rc.txt"
grep -E "SHARD_JOBS|AGG_JOBS|OUT |Traceback|Error" "$OUT/probe3_stdout.log" | head -20
echo "=== rendered agg script ==="
cat "$HOME/bench/wd_probe3/ProbeAggPipeline/AggFiles/0/job.script" 2>/dev/null
echo ""
echo "=== agg signature ==="
cat "$HOME/bench/wd_probe3/ProbeAggPipeline/AggFiles/0/job.signature.toml" 2>/dev/null
echo "=== exec log ==="
cat "$OUT/probe3.log"
echo "=== tail stdout ==="
tail -20 "$OUT/probe3_stdout.log"
