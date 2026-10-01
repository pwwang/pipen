#!/usr/bin/env bash
# Step 4e + step 6: generated job script, ANSI-free help copies, third-party namespace attempt
set -u
SRC=/mnt/f/E/hermes-workspace/pipen/ai_demo
RAW=$SRC/raw
DEMO=$HOME/aidemo
VPY="$DEMO/.venv/bin/python"
PIPEN="$DEMO/.venv/bin/pipen"
export PATH="$DEMO/.venv/bin:$PATH"

echo "############ STEP 4e: the generated job script for the CLI-driven run"
echo "(workdir is relative to CWD; the CLI run was executed from \$HOME)"
find "$DEMO" -name 'job.script' -path '*FastqStats*' | sort
JS=$(find "$DEMO" -name 'job.script' -path '*FastqStats*' | sort | head -1)
echo "--- content of $JS ---"
cat "$JS" 2>&1

echo
echo "############ STEP 4e2: the rendered command / wrapper (cmd.sh) if present"
find "$HOME/.pipen" -maxdepth 4 -type f -name '*.sh' 2>/dev/null | head
for f in $(find "$HOME/.pipen" -maxdepth 4 -type f -name 'cmd.sh' 2>/dev/null | head -2); do
  echo "--- $f ---"; cat "$f"
done

echo
echo "############ ANSI-stripped copies of the CLI help (raw captures keep the codes)"
for sub in "--help" "run --help" "run demo_ns --help" "run demo_ns FastqStats --help" "run demo_ns CountReads --help" "mcp --help"; do
  echo "=========== pipen $sub ==========="
  # shellcheck disable=SC2086
  NO_COLOR=1 "$PIPEN" $sub 2>&1 | sed -e 's/\x1b\[[0-9;]*m//g'
  echo "RC=$?"
done

echo
echo "############ pipen plugins / version"
"$PIPEN" plugins 2>&1 | sed -e 's/\x1b\[[0-9;]*m//g'
echo "RC=$?"
"$PIPEN" version 2>&1 | sed -e 's/\x1b\[[0-9;]*m//g' | head -20
echo "RC=$?"

echo
echo "############ where does '[truncated]' in the tool result come from?"
grep -rn "truncated" "$DEMO/.venv/lib/python3.12/site-packages/mcp/server/mcpserver/" 2>/dev/null | head -10
grep -rln "max_output" "$DEMO/.venv/lib/python3.12/site-packages/mcp/" 2>/dev/null | head -5

echo
echo "############ STEP 6: third-party namespace - is biopipen available on PyPI?"
timeout 120 "$VPY" -m pip download --no-deps --dest /tmp/biopipen_dl biopipen 2>&1 | tail -5
echo "PIP_DOWNLOAD_RC=$?"
