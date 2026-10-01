#!/usr/bin/env bash
# How does pipen expose `envs` to the job script?
set -u
V=$HOME/aidemo/.venv/lib/python3.12/site-packages
echo "=== grep 'envs' in pipen/template.py ==="
grep -n "envs" "$V"/pipen/template.py | head -30
echo
echo "=== grep 'envs' in pipen/proc.py ==="
grep -n "envs" "$V"/pipen/proc.py | head -40
echo
echo "=== PIPEN_ prefixes / env var rendering ==="
grep -rn "envs" "$V"/pipen/defaults.py | head -20
