#!/usr/bin/env bash
set -u
V="$HOME/bench/.venv/lib/python3.12/site-packages"
echo "=== xqute files ==="
find "$V/xqute" -name '*.py' | head -20
echo "=== local scheduler ==="
find "$V/xqute" -name '*.py' -path '*sched*' -exec grep -n "sleep(\|forks\|submission_batch\|async def\|def " {} + | head -50
echo "=== search sleep intervals in xqute ==="
grep -rn "sleep(" "$V/xqute" | head -30
