#!/usr/bin/env bash
set -u
P="$HOME/github/pipen/pipen"
echo "=== pipen: Scheduler / LocalScheduler / submission_batch / keep_feeding refs ==="
grep -rn "LocalScheduler\|submission_batch\|keep_feeding\|Scheduler\b\|xqute" "$P" --include='*.py' | head -80
echo
echo "=== pipen defaults: SLEEP/BATCH/FORKS config keys ==="
grep -rn "sleep\|SLEEP\|submission\|batch" "$P/defaults.py" | head -40
echo
echo "=== pipen version + git commit ==="
cd "$HOME/github/pipen" && git log --oneline -1 && git describe --tags 2>/dev/null; "$HOME/bench/.venv/bin/python" -c 'import pipen;print("pipen",pipen.__version__)'
echo
echo "=== JOBCMD_WRAPPER_TEMPLATE + wrapper init (defaults.py lines 1-100) ==="
awk 'NR>=1 && NR<=100 {printf "%5d\t%s\n", NR, $0}' "$HOME/bench/.venv/lib/python3.12/site-packages/xqute/defaults.py"
