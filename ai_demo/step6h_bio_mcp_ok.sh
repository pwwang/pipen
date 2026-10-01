#!/usr/bin/env bash
# Third-party end-to-end over MCP, after the report frontend install.
set -u
SRC=/mnt/f/E/hermes-workspace/pipen/ai_demo
BIO=$HOME/aidemo_bio
WORK=$BIO/work
VPY="$BIO/.venv/bin/python"
cp -f "$SRC/mcp_bio_client2.py" "$BIO/"

export PIPEN_BIN="$BIO/.venv/bin/pipen"
export RAW_DIR="$SRC/raw"
export WORK="$WORK"

echo "############ the generated job script (cmd.sh) of the successful third-party CLI run"
cat "$WORK/out_cli/Shell/cmd.sh" 2>&1
echo "=== end cmd.sh ==="

echo
echo "############ produced output of the third-party CLI run"
ls -l "$WORK/out_cli/Shell/" 2>&1
echo "--- content ---"
cat "$WORK/out_cli/Shell/input.txt" 2>&1
echo "--- diff against the input the agent supplied ---"
diff "$WORK/input.txt" "$WORK/out_cli/Shell/input.txt" && echo "IDENTICAL"

echo
echo "############ third-party process discovered + EXECUTED over MCP"
rm -rf "$WORK/out"
cd "$WORK"
PATH="$BIO/.venv/bin:$PATH" "$VPY" "$BIO/mcp_bio_client2.py" 2>&1
echo "BIO_MCP_RC=$?"

echo
echo "############ files produced by the MCP-driven third-party run"
find "$WORK/out" -type f 2>/dev/null | sort | head -20
echo "--- content ---"
cat "$WORK/out/Shell/input.txt" 2>&1
