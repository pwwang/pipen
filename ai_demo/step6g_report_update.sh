#!/usr/bin/env bash
# Install pipen-report's frontend deps in the biopipen venv, then retry the third-party run.
set -u
BIO=$HOME/aidemo_bio
WORK=$BIO/work
PIPEN="$BIO/.venv/bin/pipen"
export PATH="$BIO/.venv/bin:$PATH"

echo "### pipen report update"
timeout 900 "$PIPEN" report update 2>&1 | tail -20
echo "REPORT_UPDATE_RC=$?"

echo
echo "### retry: CLI run of the third-party process"
rm -rf "$WORK/out_cli"
"$PIPEN" run misc Shell \
  --in.infile "$WORK/input.txt" \
  --envs.cmd 'cp $infile $outfile' \
  --out.outfile shell_out_cli.txt \
  --outdir "$WORK/out_cli" 2>&1 | tail -12
echo "CLI_RC=$?"
find "$WORK/out_cli" -type f 2>/dev/null | sort
echo "--- produced file ---"
cat "$WORK/out_cli/Shell/shell_out_cli.txt" 2>&1

echo
echo "### job script of the third-party run"
for f in $(find "$WORK/out_cli" -name 'job.script' 2>/dev/null | head -1); do cat "$f"; done
