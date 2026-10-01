#!/usr/bin/env bash
# Probe xqute source for the constants under test. Read-only.
set -u
VENV="$HOME/bench/.venv"
SP=$("$VENV/bin/python" -c 'import xqute.defaults as d, os; print(os.path.dirname(d.__file__))')
echo "XQUTE_DIR=$SP"
"$VENV/bin/python" -c 'import xqute, pipen; print("xqute", xqute.__version__ if hasattr(xqute,"__version__") else "?", "from", xqute.__file__)'
echo "=== defaults.py : sleep/batch lines ==="
grep -n 'SLEEP\|BATCH' "$SP/defaults.py"
echo
echo "=== local_scheduler.py (full, numbered) ==="
cat -n "$SP/schedulers/local_scheduler.py"
echo
echo "=== all references to the five constants under test ==="
grep -rn 'SUBMIT_JOB_SLEEP\|SLEEP_INTERVAL_PRODUCER_MAX_FORKS\|SLEEP_INTERVAL_POLLING_JOBS\|SLEEP_INTERVAL_KEEP_FEEDING\|DEFAULT_SUBMISSION_BATCH' "$SP" --include='*.py'
echo
echo "=== xqute package dir listing ==="
find "$SP" -name '*.py' | sort
