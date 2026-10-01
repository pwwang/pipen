#!/usr/bin/env bash
# Capture --help+ (full option set) and count options, for an evidence-backed statement
set -u
DEMO=$HOME/aidemo
PIPEN="$DEMO/.venv/bin/pipen"
export PATH="$DEMO/.venv/bin:$PATH"
cd "$DEMO"
echo "### pipen run demo_ns FastqStats --help+  (full option set)"
"$PIPEN" run demo_ns FastqStats --help+ 2>&1 | sed -e 's/\x1b\[[0-9;]*m//g' > /tmp/helpplus.txt
head -60 /tmp/helpplus.txt
echo "..."
echo "### option count in --help+  vs  --help"
echo -n "--help+ option lines: "
grep -c '^  --' /tmp/helpplus.txt
"$PIPEN" run demo_ns FastqStats --help 2>&1 | sed -e 's/\x1b\[[0-9;]*m//g' > /tmp/help.txt
echo -n "--help  option lines: "
grep -c '^  --' /tmp/help.txt
echo
echo "### a couple of options that only appear in --help+"
comm -13 <(grep '^  --' /tmp/help.txt | sed 's/^ *//' | cut -d' ' -f1 | sort) \
         <(grep '^  --' /tmp/helpplus.txt | sed 's/^ *//' | cut -d' ' -f1 | sort) | head -12
echo
echo "### error_strategy present in --help+ ?"
grep -c 'error_strategy' /tmp/helpplus.txt
