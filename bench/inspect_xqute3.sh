#!/usr/bin/env bash
set -u
V="$HOME/bench/.venv/lib/python3.12/site-packages"
echo "=== defaults.py ==="
cat -n "$V/xqute/defaults.py"
echo "=== xqute.py lines 150-230 ==="
sed -n '150,230p' "$V/xqute/xqute.py" | cat -n
echo "=== xqute.py lines 290,340 ==="
sed -n '290,340p' "$V/xqute/xqute.py" | cat -n
