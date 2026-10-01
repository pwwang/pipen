#!/usr/bin/env bash
# Locate the generated job script; find the source of '[truncated]'; inspect biopipen entry points
set -u
SRC=/mnt/f/E/hermes-workspace/pipen/ai_demo
RAW=$SRC/raw
DEMO=$HOME/aidemo
VPY="$DEMO/.venv/bin/python"
export PATH="$DEMO/.venv/bin:$PATH"

echo "############ where did the workdir go?"
find "$HOME" -maxdepth 3 -name '.pipen' -type d 2>/dev/null
echo "--- full tree of \$HOME/.pipen (maxdepth 4) ---"
find "$HOME/.pipen" -maxdepth 4 2>/dev/null | sort | head -40

echo
echo "############ the generated job script(s)"
for f in $(find "$HOME/.pipen" -name 'job.script' 2>/dev/null | sort); do
  echo "===== $f ====="
  cat "$f"
  echo "===== end $f ====="
done

echo
echo "############ source of '[truncated]' in the captured tool result"
grep -c 'truncated' "$RAW"/05h_call_run_process.json || echo "(no 'truncated' in 05h file)"
"$VPY" - <<'PY'
import json, pathlib
p = pathlib.Path("/mnt/f/E/hermes-workspace/pipen/ai_demo/raw/05h_call_run_process.json")
d = json.loads(p.read_text())
t = d["structured_content"]["result"]
print("tool result text length:", len(t))
print("contains 'truncated':", "truncated" in t)
print("tail:", repr(t[-200:]))
PY
echo "--- grep the mcp SDK for a truncation constant ---"
grep -rn "truncat" "$DEMO/.venv/lib/python3.12/site-packages/mcp/" --include=*.py 2>/dev/null | grep -iv "traceback" | head -20

echo
echo "############ biopipen 1.5.1: does it register a pipen_cli_run namespace?"
"$VPY" - <<'PY'
import zipfile, pathlib
whl = next(pathlib.Path("/tmp/biopipen_dl").glob("biopipen-*.whl"))
with zipfile.ZipFile(whl) as z:
    for name in z.namelist():
        if name.endswith("entry_points.txt"):
            print("===", name, "===")
            print(z.read(name).decode())
PY
