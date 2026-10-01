#!/usr/bin/env bash
# Targeted probe of plugin metadata (skipping nested .venv dirs)
set -u
raw=/mnt/f/E/hermes-workspace/pipen/ai_demo
mkdir -p "$raw"
for d in pipen-cli-run pipen-mcp pipen-annotate pipen-args; do
  echo "########## $d ##########"
  echo "--- pyproject.toml ---"
  cat "$HOME/github/$d/pyproject.toml" 2>&1
  echo "--- version.py ---"
  cat "$HOME/github/$d"/*/version.py 2>/dev/null || echo "(no version.py)"
  echo "--- module files ---"
  find "$HOME/github/$d" -maxdepth 2 -name '*.py' -not -path '*/.git/*' -not -path '*/.venv/*' -not -path '*__pycache__*'
  echo
done
