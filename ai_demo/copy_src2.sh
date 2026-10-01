#!/usr/bin/env bash
# Stage plugin sources with unambiguous names
set -u
DEST=/mnt/f/E/hermes-workspace/pipen/ai_demo/src_ref
V=$HOME/aidemo/.venv/lib/python3.12/site-packages
mkdir -p "$DEST"
cp -v "$V"/pipen_cli_run/entry.py "$DEST"/cli_run_entry.py
cp -v "$V"/pipen_cli_run/__init__.py "$DEST"/cli_run___init__.py
cp -v "$V"/pipen_mcp/entry.py "$DEST"/mcp_entry.py
cp -v "$V"/pipen_mcp/server.py "$DEST"/mcp_server.py
cp -v "$V"/pipen_mcp/introspect.py "$DEST"/mcp_introspect.py
echo "=== pipen.entry_points / CLI hooks ==="
cat "$V"/pipen/cli/_hooks.py
