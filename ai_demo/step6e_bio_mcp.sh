#!/usr/bin/env bash
# Step 6 end-to-end: run a BioPipen process through the MCP server, in the biopipen venv
set -u
SRC=/mnt/f/E/hermes-workspace/pipen/ai_demo
BIO=$HOME/aidemo_bio
VPY="$BIO/.venv/bin/python"
cp -f "$SRC/mcp_bio_client.py" "$BIO/"

export PIPEN_BIN="$BIO/.venv/bin/pipen"
export RAW_DIR="$SRC/raw"
export WORK="$BIO/work"
mkdir -p "$WORK"
rm -rf "$WORK/out"

echo "### also capture the same third-party process over the plain CLI, for comparison"
"$BIO/.venv/bin/pipen" run misc Shell \
  --in.infile "$WORK/input.txt" \
  --envs.cmd 'cp $infile $outfile' \
  --out.outfile shell_out_cli.txt \
  --outdir "$WORK/out_cli" 2>&1 | tail -8
echo "CLI_RC=$?"
cat "$WORK/out_cli/Shell/shell_out_cli.txt" 2>&1

echo
echo "=================================================================="
echo "### third-party process discovered and executed via MCP"
echo "=================================================================="
cd "$WORK"
PATH="$BIO/.venv/bin:$PATH" "$VPY" "$BIO/mcp_bio_client.py" 2>&1
echo "BIO_MCP_RC=$?"

echo
echo "### the job script pipen generated for the third-party process"
find "$WORK" -name 'job.script' | head -3
for f in $(find "$WORK" -name 'job.script' | head -1); do cat "$f"; done

echo
echo "### produced file from the MCP-driven third-party run"
ls -l "$WORK/out/Shell/" 2>&1
cat "$WORK/out/Shell/shell_out.txt" 2>&1
