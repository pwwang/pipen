#!/usr/bin/env bash
set -u
SRC=/mnt/f/E/hermes-workspace/pipen/ai_demo
RAW=$SRC/raw
DEMO=$HOME/aidemo
VPY="$DEMO/.venv/bin/python"

echo "############ biopipen wheel metadata: Requires-Dist"
"$VPY" - <<'PY'
import zipfile, pathlib
whl = next(pathlib.Path("/tmp/biopipen_dl").glob("biopipen-*.whl"))
with zipfile.ZipFile(whl) as z:
    meta = [n for n in z.namelist() if n.endswith("METADATA")][0]
    for line in z.read(meta).decode().splitlines():
        if line.startswith(("Requires-Dist", "Requires-Python", "Name:", "Version:")):
            print(line)
PY

echo
echo "############ where did the demo workdir land? search the workspace"
find /mnt/f/E/hermes-workspace -maxdepth 5 -type d -name '.pipen' 2>/dev/null
for d in $(find /mnt/f/E/hermes-workspace -maxdepth 5 -type d -name '.pipen' 2>/dev/null); do
  echo "--- tree: $d ---"
  find "$d" -maxdepth 3 | sort | head -20
done

echo
echo "############ job.script for the demo runs, anywhere on F: or in \$HOME"
find /mnt/f/E/hermes-workspace "$HOME" -name 'job.script' -newermt '2026-09-30 21:30' 2>/dev/null | head -10

echo
echo "############ is '[truncated]' really in the capture file, or an artefact of the reader?"
grep -c 'truncated' "$RAW/05_mcp_run.txt"
grep -o 'truncated' "$RAW/05_mcp_run.txt" | head -3
echo "line lengths of the run_process JSON lines:"
awk '{ print NR": "length($0) }' "$RAW/05h_call_run_process.json" | sort -t: -k2 -n | tail -5
