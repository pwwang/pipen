#!/usr/bin/env bash
set -u
cd "$HOME/bench"
"$HOME/bench/.venv/bin/python" /mnt/f/E/hermes-workspace/pipen/bench/analyse_all.py > out/analysis.log 2>&1
echo "ANALYSE_RC=$?"
sed -n '1,90p' out/analysis.log
