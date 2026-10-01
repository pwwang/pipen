#!/usr/bin/env bash
set -u
SP="$HOME/bench/.venv/lib/python3.12/site-packages/xqute"
echo "=== xqute/xqute.py (numbered, lines 150-360) ==="
sed -n '1,150p' "$SP/xqute.py" | cat -n | sed 's/^/    /' > /dev/null
awk 'NR>=1 && NR<=150 {printf "%5d\t%s\n", NR, $0}' "$SP/xqute.py"
echo "-----"
awk 'NR>=150 && NR<=360 {printf "%5d\t%s\n", NR, $0}' "$SP/xqute.py"
