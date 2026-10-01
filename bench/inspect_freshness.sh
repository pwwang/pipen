#!/usr/bin/env bash
set -u
echo "=== exported agg (last writer wins; shared path across runs) ==="
ls -la "$HOME/bench/CachePipeline-output/Agg/agg.txt"
wc -l "$HOME/bench/CachePipeline-output/Agg/agg.txt"
echo "=== small-run Agg job output ==="
find "$HOME/bench/wd_s5_scope" -name "agg.txt" -exec ls -la {} \;
echo "--- content (head 12) ---"
find "$HOME/bench/wd_s5_scope" -name "agg.txt" -exec head -12 {} \;
echo "--- does it contain line3-v2 ? ---"
find "$HOME/bench/wd_s5_scope" -name "agg.txt" -exec grep -c "line3-v2" {} \;
echo "--- grep line4 / line3 lines ---"
find "$HOME/bench/wd_s5_scope" -name "agg.txt" -exec grep -n "line3\|line4" {} \;
echo "=== inputs ==="
for f in "$HOME/bench/cache_inputs_small"/in3.txt "$HOME/bench/cache_inputs_small"/in4.txt; do echo "$f: $(cat $f)"; done
echo "=== Mid branch outputs (small run) ==="
for d in "$HOME/bench/wd_s5_scope/CachePipeline/Mid"/*/; do i=$(basename $d); echo "$i: $(cat $d/output/m-*.txt 2>/dev/null | tr '\n' ' ')"; done
echo "=== Agg job signature/output mtimes ==="
ls -la --time-style=full-iso "$HOME/bench/wd_s5_scope/CachePipeline/Agg/0/"
