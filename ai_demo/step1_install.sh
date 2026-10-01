#!/usr/bin/env bash
# Step 1: fresh venv on PyPI releases; record versions. Console-only captures go to $OUT.
set -u
OUT=/mnt/f/E/hermes-workspace/pipen/ai_demo/raw
mkdir -p "$OUT"
DEMO=$HOME/aidemo
mkdir -p "$DEMO"
cd "$DEMO"

echo "### python3 version"
python3 -V 2>&1

echo
echo "### creating fresh venv at \$HOME/aidemo/.venv"
rm -rf "$DEMO/.venv"
python3 -m venv "$DEMO/.venv" 2>&1
VPY="$DEMO/.venv/bin/python"
"$VPY" -V 2>&1
"$VPY" -m pip --version 2>&1

echo
echo "### pip install (PyPI released versions)"
"$VPY" -m pip install --quiet --upgrade pip 2>&1 | tail -3
"$VPY" -m pip install "pipen==1.2.3" "pipen-cli-run" "pipen-annotate" "pipen-mcp" "mcp[cli]" 2>&1
echo "PIP_INSTALL_RC=$?"

echo
echo "### pip freeze | grep -i pipen"
"$VPY" -m pip freeze 2>&1 | grep -i -E 'pipen|xqute|simplug|argx|^mcp|annotate' | sort

echo
echo "### pip show (versions)"
for p in pipen pipen-cli-run pipen-annotate pipen-mcp mcp pipen-args xqute simplug argx; do
  "$VPY" -m pip show "$p" 2>/dev/null | grep -E '^(Name|Version|Location|Requires):'
done

echo
echo "### does released pipen 1.2.3 ship the pipen.cli package?"
"$VPY" - <<'PY'
import importlib.util, pipen, os
print("pipen.__version__ =", pipen.__version__)
print("pipen file        =", pipen.__file__)
spec = importlib.util.find_spec("pipen.cli")
print("pipen.cli spec    =", spec)
print("cli dir listing   =", os.listdir(os.path.dirname(spec.origin)) if spec else None)
PY

echo
echo "### installed pipen console script"
ls -l "$DEMO/.venv/bin/" | grep -iE 'pipen|mcp' || echo "(no pipen/mcp scripts)"
