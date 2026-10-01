#!/usr/bin/env bash
set -u
cd "$HOME/bench"
"$HOME/bench/.venv/bin/python" /mnt/f/E/hermes-workspace/pipen/bench/evidence.py > out/evidence.log 2>&1
echo "EVIDENCE_RC=$?"
head -70 out/evidence.log
