#!/usr/bin/env bash
# Copy plugin sources from the demo venv into src_ref for reading on the Windows side
set -u
DEST=/mnt/f/E/hermes-workspace/pipen/ai_demo/src_ref
V=$HOME/aidemo/.venv/lib/python3.12/site-packages
mkdir -p "$DEST"
cp -v "$V"/pipen_cli_run/*.py "$DEST"/
cp -v "$V"/pipen_mcp/*.py "$DEST"/
cp -v "$V"/pipen_annotate/*.py "$DEST"/
echo "=== listing ==="
ls -la "$DEST"
