#!/usr/bin/env bash
set -u
OUT="$HOME/bench/out"
cd "$HOME/bench"
: > "$OUT/marker_dbg.log"
BENCH_LOGLEVEL=debug \
BN_N=8 BN_INDIR="$HOME/bench/cache_inputs_small" BN_WORKDIR="$HOME/bench/wd_s5_scope" \
BN_MARKER="$OUT/marker_dbg.log" BN_MIDVARIANT=B BN_SIDEVARIANT=A \
  "$HOME/bench/.venv/bin/python" /mnt/f/E/hermes-workspace/pipen/bench/bench_cache_dag.py \
  > "$OUT/dbg_cache.log" 2>&1
echo "DBG_RC=$?"
echo "### why not cached (unique reasons) ###"
grep -o "Not cached ([^)]*)" "$OUT/dbg_cache.log" | sort | uniq -c | sort -rn | head -20
echo "### sample reason lines ###"
grep -n "Not cached" "$OUT/dbg_cache.log" | head -12
echo "### cached jobs lines ###"
grep -n "Cached jobs" "$OUT/dbg_cache.log" | head
echo "### jobs that executed ###"
wc -l "$OUT/marker_dbg.log"
head -6 "$OUT/marker_dbg.log"
echo "### signature file of Read/0 ###"
cat "$HOME/bench/wd_s5_scope/CachePipeline/Read/0/job.signature.toml" 2>/dev/null
echo "### stat of a Read input and its signature ###"
ls -la --time-style=full-iso "$HOME/bench/cache_inputs_small/in0.txt" \
   "$HOME/bench/wd_s5_scope/CachePipeline/Read/0/job.signature.toml" \
   "$HOME/bench/wd_s5_scope/CachePipeline/Read/0/job.script" \
   "$HOME/bench/wd_s5_scope/CachePipeline/Read/0/output/" 2>/dev/null
