#!/usr/bin/env bash
# Step 5: drive the pipen MCP server with (a) the official mcp SDK client and
# (b) a raw JSON-RPC stdio probe. Also capture the CAVEAT that `run_process`
# depends on the `pipen` console script being on PATH.
set -u
SRC=/mnt/f/E/hermes-workspace/pipen/ai_demo
RAW=$SRC/raw
DEMO=$HOME/aidemo
VPY="$DEMO/.venv/bin/python"
mkdir -p "$RAW"

cp -f "$SRC/mcp_client_sdk.py" "$SRC/mcp_client_raw.py" "$DEMO/"

export PIPEN_BIN="$DEMO/.venv/bin/pipen"
export RAW_DIR="$RAW"
export TESTDATA="$DEMO/testdata"
export OUTDIR="$DEMO/out_mcp"

echo "=================================================================="
echo " STEP 5a: official mcp SDK client over stdio"
echo "=================================================================="
rm -rf "$OUTDIR"
PATH="$DEMO/.venv/bin:$PATH" "$VPY" "$DEMO/mcp_client_sdk.py" 2>&1
echo "SDK_CLIENT_RC=$?"

echo
echo "=================================================================="
echo " STEP 5b: raw JSON-RPC over stdio (wire-level trace)"
echo "=================================================================="
rm -rf "$OUTDIR"
PATH="$DEMO/.venv/bin:$PATH" "$VPY" "$DEMO/mcp_client_raw.py" 2>&1
echo "RAW_CLIENT_RC=$?"

echo
echo "=================================================================="
echo " STEP 5c: produced output file from the MCP-driven run"
echo "=================================================================="
ls -l "$OUTDIR/FastqStats/" 2>&1
cat "$OUTDIR/FastqStats/read_stats.tsv" 2>&1

echo
echo "=================================================================="
echo " STEP 5d: CAVEAT - run_process shells out to the 'pipen' console script."
echo "          Here we launch the client WITHOUT the venv on PATH."
echo "=================================================================="
OUTDIR="$DEMO/out_mcp_nopath" "$VPY" "$DEMO/mcp_client_raw.py" 2>&1 | tail -25
echo "(see the run_process error above)"
