#!/usr/bin/env bash
set -u
OUT="$HOME/bench/out"
RAW=/mnt/f/E/hermes-workspace/pipen/bench/raw
mkdir -p "$RAW"
cp -f "$OUT"/pipen_install.log "$RAW/pipen_install.log" 2>/dev/null || true
cp -f "$OUT"/snakemake_install.log "$RAW/snakemake_install.log" 2>/dev/null || true
cp -f "$OUT"/pip_upgrade.log "$RAW/pip_pip_upgrade.log" 2>/dev/null || true
cp -f "$HOME/bench/out/hello_stdout.log" "$RAW/hello_world_pipen.log" 2>/dev/null || true
echo "=== raw contents ==="
ls "$RAW"
echo "=== size / count ==="
du -sh "$RAW"; find "$RAW" -type f | wc -l
echo "=== subdirs ==="
ls "$RAW/logs_pipen" | head -30
echo "---"
ls "$RAW/logs_smk"
echo "--- markers (count) ---"
ls "$RAW/markers" | wc -l
echo "=== verify key claims are present in the raw JSONs ==="
"$HOME/bench/.venv/bin/python" - <<'PY'
import json
r = json.load(open("/mnt/f/E/hermes-workspace/pipen/bench/raw/derived_numbers.json"))
print("pipen N=500 wall median :", r["pipen_scaling"][-1]["wall_median"])
print("pipen oh/job N=500      :", r["pipen_scaling"][-1]["overhead_per_job_median"])
print("smk   N=500 wall median :", r["smk_scaling"][-1]["wall_median"])
print("smk   oh/job N=500      :", r["smk_scaling"][-1]["overhead_per_job_median"])
print("ratio N=500             :", r["head_to_head"][-1]["ratio_pipen_over_smk"])
print("caching timing          :", r["pipen_caching_timing"])
t = json.load(open("/mnt/f/E/hermes-workspace/pipen/bench/raw/touch_test.json"))
for x in t["results"]:
    print("  touch:", x["label"], "jobs=", x["jobs_executed"], x["jobs_by_proc"])
PY
