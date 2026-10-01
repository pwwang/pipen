#!/usr/bin/env bash
set -u
OUT="$HOME/bench/out"
DEST=/mnt/f/E/hermes-workspace/pipen/bench
RAW="$DEST/raw"
mkdir -p "$RAW" "$RAW/logs_pipen" "$RAW/logs_smk" "$RAW/markers"

# JSON artifacts (small)
cp -f "$OUT"/pipen_records.json             "$RAW/pipen_records_steps34.json"
cp -f "$OUT"/pipen_records_step5.json       "$RAW/pipen_records_step5.json"
cp -f "$OUT"/pipen_cache_scope_step5.json   "$RAW/pipen_cache_scope.json"
cp -f "$OUT"/smk_records_step34.json        "$RAW/smk_records_steps34.json"
cp -f "$OUT"/smk_records_step5.json         "$RAW/smk_records_step5.json"
cp -f "$OUT"/smk_cache_scope.json           "$RAW/smk_cache_scope.json"
cp -f "$OUT"/summary.json                   "$RAW/summary.json"
cp -f "$OUT"/evidence_caching.json          "$RAW/evidence_caching.json"
cp -f "$OUT"/environment.json               "$RAW/environment.json"
cp -f "$OUT"/env_raw.txt                    "$RAW/env_raw.txt"
cp -f "$OUT"/probe3_stdout.log              "$RAW/probe_pipen_aggregation.txt"
cp -f "$OUT"/hello_stdout.log               "$RAW/hello_world_pipen.log"

# raw per-run tool logs (these are the primary traceability source)
cp -f "$OUT"/logs/*.log          "$RAW/logs_pipen/" 2>/dev/null || true
cp -f "$OUT"/logs_smk/*.log      "$RAW/logs_smk/" 2>/dev/null || true
cp -f "$OUT"/diag_*.log          "$RAW/logs_pipen/" 2>/dev/null || true
cp -f "$OUT"/cal_*.log           "$RAW/logs_pipen/" 2>/dev/null || true

# marker logs = per-job execution evidence
cp -f "$OUT"/marker_*.log        "$RAW/markers/" 2>/dev/null || true

echo "=== raw tree ==="
du -sh "$RAW"
find "$RAW" -type f | wc -l
echo "=== largest files ==="
find "$RAW" -type f -printf '%s %p\n' | sort -rn | head -8
echo "=== totals by dir ==="
du -sh "$RAW"/* 2>/dev/null
echo "=== jobs per run (pipen steps3/4, from summary) ==="
"$HOME/bench/.venv/bin/python" - <<'PY'
import json
s = json.load(open("/home/pwwang/bench/out/summary.json"))
for g in ("pipen_scaling", "pipen_concurrency", "smk_scaling", "smk_concurrency"):
    for r in s[g]["records"]:
        print(g, r["tag"], "jobs=", r.get("jobs"), "logjobs=", r.get("jobs_from_tool_log"))
PY
