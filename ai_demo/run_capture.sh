#!/usr/bin/env bash
# Run a target script and tee everything (stdout+stderr) to a capture file.
# Usage: bash run_capture.sh <script> <capture-file>
set -u
script="$1"
cap="$2"
mkdir -p "$(dirname "$cap")"
bash "$script" > "$cap" 2>&1
rc=$?
echo "CAPTURE=$cap"
echo "SCRIPT_RC=$rc"
wc -l "$cap"
exit 0
