#!/usr/bin/env bash
# Can the third-party (biopipen) process be executed with the report plugin disabled?
set -u
BIO=$HOME/aidemo_bio
WORK=$BIO/work
PIPEN="$BIO/.venv/bin/pipen"
export PATH="$BIO/.venv/bin:$PATH"
mkdir -p "$WORK"
printf 'agent-provided input\nsecond line\n' > "$WORK/input.txt"

echo "############ is node/npm available?"
command -v node; command -v npm; echo "(rc=$?)"

echo
echo "############ full help (-h+) of a biopipen process: any report switch?"
"$PIPEN" run misc Shell --help+ 2>&1 | sed -e 's/\x1b\[[0-9;]*m//g' | grep -i -n "report" | head -20

echo
echo "############ attempt: run with --report false"
rm -rf "$WORK/out_cli"
"$PIPEN" run misc Shell \
  --in.infile "$WORK/input.txt" \
  --envs.cmd 'cp $infile $outfile' \
  --out.outfile shell_out_cli.txt \
  --outdir "$WORK/out_cli" \
  --report false 2>&1 | tail -15
echo "RC=$?"
echo "--- produced? ---"
find "$WORK/out_cli" -type f 2>/dev/null | sort
cat "$WORK/out_cli/Shell/shell_out_cli.txt" 2>&1

echo
echo "############ version of the report plugin in this venv"
"$BIO/.venv/bin/python" -m pip show pipen-report 2>/dev/null | grep -E '^(Name|Version):'
