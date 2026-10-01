#!/usr/bin/env bash
# Inventory of the demo: integration-surface size + raw capture inventory
set -u
SRC=/mnt/f/E/hermes-workspace/pipen/ai_demo
echo "############ size of the integration surface (the demo package)"
wc -l "$SRC/demo_ns/demo_ns/__init__.py" "$SRC/demo_ns/pyproject.toml" \
      "$SRC/demo_extra_ns/demo_extra_ns/__init__.py" "$SRC/demo_extra_ns/pyproject.toml"
echo
echo "############ the single entry-point table that makes a package a namespace"
grep -n -A2 "entry-points" "$SRC/demo_ns/pyproject.toml"
echo
echo "############ raw capture inventory"
ls -l "$SRC/raw"
echo
echo "############ workspace inventory"
ls -l "$SRC"
