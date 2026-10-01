#!/usr/bin/env bash
set -u
SP="$HOME/bench/.venv/lib/python3.12/site-packages/xqute"
echo "=== xqute/scheduler.py (numbered) ==="
cat -n "$SP/scheduler.py"
