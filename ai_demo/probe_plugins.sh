#!/usr/bin/env bash
# Probe the plugin checkouts: structure + entry points
set -u
for d in pipen-cli-run pipen-mcp pipen-annotate pipen-args; do
  echo "=========== $d ==========="
  find "$HOME/github/$d" -name '*.py' -not -path '*/.git/*' -not -path '*__pycache__*' | head -30
  echo "--- pyproject.toml ---"
  if [ -f "$HOME/github/$d/pyproject.toml" ]; then
    cat "$HOME/github/$d/pyproject.toml"
  else
    echo "(no pyproject.toml)"
  fi
  echo "--- _version.py / __init__ version ---"
  find "$HOME/github/$d" -name '_version.py' -not -path '*/.git/*' -exec sh -c 'echo "FILE: $1"; cat "$1"' _ {} \; 2>/dev/null
  echo
done
