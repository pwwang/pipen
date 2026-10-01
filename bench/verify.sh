#!/usr/bin/env bash
# Step 2: verify pipen runs; plus probe the files-aggregation template pattern.
set -u
VP="$HOME/bench/.venv/bin"
OUT="$HOME/bench/out"
mkdir -p "$OUT"
BENCH=/mnt/f/E/hermes-workspace/pipen/bench

# --- hello world ---
rm -rf "$HOME/bench/wd_hello" "$HOME/bench/out_hello"
HELLO_WORKDIR="$HOME/bench/wd_hello" HELLO_OUTDIR="$HOME/bench/out_hello" \
  "$VP/python" "$BENCH/hello_pipen.py" > "$OUT/hello_stdout.log" 2>&1
echo "HELLO_RC=$?" > "$OUT/hello_rc.txt"
echo "--- hello output file content ---" 
echo "result.txt:"; cat "$HOME/bench/out_hello/NumberLines/result.txt" 2>/dev/null
echo "intermediate.txt:"; cat "$HOME/bench/out_hello/SortFile/intermediate.txt" 2>/dev/null
echo "--- find exported outputs ---"
find "$HOME/bench/out_hello" -type f -o -type l 2>/dev/null | head -20

# --- files aggregation probe ---
rm -rf "$HOME/bench/wd_probe"
: > "$HOME/bench/out/probe_rerun.log"
PROBE_WORKDIR="$HOME/bench/wd_probe" PROBE_N=4 PROBE_LOG="$HOME/bench/out/probe_rerun.log" \
  "$VP/python" "$BENCH/probe_files.py" > "$OUT/probe_stdout.log" 2>&1
echo "PROBE_RC=$?"
tail -30 "$OUT/probe_stdout.log"
