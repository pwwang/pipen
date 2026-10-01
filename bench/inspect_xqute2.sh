#!/usr/bin/env bash
set -u
V="$HOME/bench/.venv/lib/python3.12/site-packages"
echo "=== local_scheduler.py ==="
cat -n "$V/xqute/schedulers/local_scheduler.py"
echo "=== SLEEP constants ==="
grep -n "SLEEP_INTERVAL\|SUBMIT_JOB_SLEEP\|POLLING" "$V/xqute/defaults.py" "$V/xqute/scheduler.py" "$V/xqute/xqute.py" | head -30
echo "=== xqute.py keep-feeding / polling loop ==="
sed -n '280,340p' "$V/xqute/xqute.py"
