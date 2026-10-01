#!/usr/bin/env bash
set -u
X="$HOME/bench/.venv/lib/python3.12/site-packages/xqute"
echo "=== xqute/defaults.py lines 100-220 ==="
awk 'NR>=100 && NR<=220 {printf "%5d\t%s\n", NR, $0}' "$X/defaults.py"
echo
echo "=== keep_feeding in pipen? ==="
grep -rn "keep_feeding\|run_until_complete" "$HOME/github/pipen/pipen" --include='*.py' || echo "NO MATCH"
echo
echo "=== pipen defaults.py lines 30-60 (submission_batch config) ==="
awk 'NR>=30 && NR<=60 {printf "%5d\t%s\n", NR, $0}' "$HOME/github/pipen/pipen/defaults.py"
echo
echo "=== uvloop version ==="
"$HOME/bench/.venv/bin/python" -c 'import uvloop;print(uvloop.__version__)'
