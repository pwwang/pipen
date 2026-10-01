#!/usr/bin/env bash
set -u
echo "=== how input_data callables are invoked ==="
grep -n "input_data\|callable" "$HOME/github/pipen/pipen/proc.py" | head -40
echo
echo "=== context around the call ==="
grep -n "input_data(.*)" -B 8 -A 8 "$HOME/github/pipen/pipen/proc.py" | head -60
echo "=== tail of r1_cold log ==="
tail -25 "$HOME/bench/out/logs/s5_r1_cold.log"
echo "=== tail of r4 log ==="
tail -15 "$HOME/bench/out/logs/s5_r4_mid_script_changed.log"
