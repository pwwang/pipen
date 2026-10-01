#!/usr/bin/env bash
set -u
cd "$HOME/bench"
"$HOME/bench/.venv/bin/python" /mnt/f/E/hermes-workspace/pipen/bench/make_report.py > out/derived.log 2>&1
echo "DERIVED_RC=$?"
cat out/derived.log
