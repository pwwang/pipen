#!/usr/bin/env bash
set -u
V="$HOME/bench/.venv/lib/python3.12/site-packages"
sed -n '160,230p' "$V/xqute/xqute.py" | cat -n
echo "..........."
sed -n '280,335p' "$V/xqute/xqute.py" | cat -n
echo "=== scheduler.py check_all_done ==="
sed -n '546,585p' "$V/xqute/scheduler.py" | cat -n
