#!/usr/bin/env bash
# Is there a third-party (biopipen) process with a bash-only script we can actually RUN?
set -u
BIO=$HOME/aidemo_bio
export PATH="$BIO/.venv/bin:$PATH"
for p in Shell File2Proc Str2File Glob2Dir Config2File; do
  echo "############ pipen run misc $p --help"
  "$BIO/.venv/bin/pipen" run misc "$p" --help 2>&1 | sed -e 's/\x1b\[[0-9;]*m//g' | sed -n '1,12p;/Namespace <envs>/,/^Options:/p'
  echo "RC=$?"
  echo
done
