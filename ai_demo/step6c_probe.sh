#!/usr/bin/env bash
set -u
SRC=/mnt/f/E/hermes-workspace/pipen/ai_demo
RAW=$SRC/raw
VPY="$HOME/aidemo/.venv/bin/python"

echo "############ direct candidate paths for the demo workdir"
for p in /mnt/f/E/hermes-workspace/pipen/.pipen /mnt/f/E/hermes-workspace/pipen/ai_demo/.pipen "$HOME/.pipen/FastqStats"; do
  if [ -d "$p" ]; then echo "FOUND: $p"; else echo "absent: $p"; fi
done

echo
echo "############ tree of the first one that exists"
for p in /mnt/f/E/hermes-workspace/pipen/.pipen /mnt/f/E/hermes-workspace/pipen/ai_demo/.pipen; do
  if [ -d "$p" ]; then
    echo "--- $p ---"
    find "$p" -maxdepth 4 | sort
    break
  fi
done

echo
echo "############ the generated job script"
for f in $(find /mnt/f/E/hermes-workspace/pipen/.pipen /mnt/f/E/hermes-workspace/pipen/ai_demo/.pipen -name 'job.script' 2>/dev/null); do
  echo "===== $f ====="
  cat "$f"
  echo "===== end ====="
  break
done

echo
echo "############ '[truncated]' presence check on the capture file"
grep -c 'truncated' "$RAW/05_mcp_run.txt"
echo "--- longest lines in 05h json ---"
awk '{ print NR": "length($0) }' "$RAW/05h_call_run_process.json" | sort -t: -k2 -n | tail -3

echo
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
