#!/usr/bin/env python3
"""Summarise all raw records into reproducible summary JSON files."""
import json
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
OUT = HOME / "bench" / "out"
DEST = Path("/mnt/f/E/hermes-workspace/pipen/bench")


def load(p):
    return json.loads(Path(p).read_text()) if Path(p).exists() else []


def med(vals):
    v = sorted(vals)
    n = len(v)
    return round(v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2, 3)


def summ(records, key, n_key):
    """group -> {median,min,max,all}"""
    groups = {}
    for r in records:
        groups.setdefault(r[n_key], []).append(r[key])
    return {k: {"median": med(v), "min": round(min(v), 3), "max": round(max(v), 3),
                "n_reps": len(v), "all": [round(x, 3) for x in v]}
            for k, v in sorted(groups.items())}


pipen34 = load(OUT / "pipen_records.json")           # steps 3+4 (current contents)
pipen5 = load(OUT / "pipen_records_step5.json")
pipen_scope = load(OUT / "pipen_cache_scope_step5.json")
smk34 = load(OUT / "smk_records_step34.json")
smk5 = load(OUT / "smk_records_step5.json")
smk_scope = load(OUT / "smk_cache_scope.json")


def job_count_from_marker(rec):
    """Jobs = number of '<proc>_start' marker lines (DAG pipeline) or all lines."""
    p = Path(rec["marker_log"])
    if not p.exists():
        return None
    kinds = [l.split()[0] for l in p.read_text().splitlines() if l.strip()]
    starts = [k for k in kinds if k.endswith("_start")]
    return len(starts) if starts else len(kinds)


summary = {"pipen_scaling": {}, "pipen_concurrency": {}, "smk_scaling": {},
           "smk_concurrency": {}, "caching": {}, "observed_parallelism": {}}

# ---- scaling (step 3) ----
p3 = [r for r in pipen34 if r["step"] == "3_scaling"]
for r in p3:
    r["jobs"] = job_count_from_marker(r)
summary["pipen_scaling"] = {
    "wall_sec_by_n": summ(p3, "wall_sec", "n"),
    "pipeline_run_sec_by_n": summ(p3, "pipeline_run_sec", "n"),
    "sleep_floor_by_n": {r["n"]: r["sleep_floor_sec"] for r in p3},
    "overhead_by_n": summ(p3, "overhead_vs_sleep_floor_sec", "n"),
    "overhead_per_job_by_n": summ(p3, "overhead_per_job_sec", "n"),
    "peak_tree_rss_mb_by_n": summ(p3, "peak_tree_rss_mb", "n"),
    "records": p3,
}
s3 = [r for r in smk34 if r["step"] == "3_scaling"]
for r in s3:
    r["jobs"] = job_count_from_marker(r)
summary["smk_scaling"] = {
    "wall_sec_by_n": summ(s3, "wall_sec", "n"),
    "sleep_floor_by_n": {r["n"]: r["sleep_floor_sec"] for r in s3},
    "overhead_by_n": summ(s3, "overhead_vs_sleep_floor_sec", "n"),
    "peak_tree_rss_mb_by_n": summ(s3, "peak_tree_rss_mb", "n"),
    "records": s3,
}

# ---- concurrency (step 4) ----
p4 = [r for r in pipen34 if r["step"] == "4_concurrency"]
for r in p4:
    r["jobs"] = job_count_from_marker(r)
base = next(r["wall_sec"] for r in p4 if r["forks"] == 1)
for r in p4:
    r["speedup_vs_forks1"] = round(base / r["wall_sec"], 2)
summary["pipen_concurrency"] = {"records": p4}
s4 = [r for r in smk34 if r["step"] == "4_concurrency"]
base = next(r["wall_sec"] for r in s4 if r["forks"] == 1)
for r in s4:
    r["speedup_vs_cores1"] = round(base / r["wall_sec"], 2)
summary["smk_concurrency"] = {"records": s4}

# N=100 single-rep data points measured during the diagnostic phase
summary["pipen_concurrency"]["n100_single_rep_diagnostic"] = [
    {"n": 100, "forks": 32, "wall_sec": 16.437, "pipeline_run_sec": 15.923,
     "source": "~/bench/out/diag_sleep05.log + marker_diag_sleep05.log", "reps": 1},
    {"n": 100, "forks": 1, "wall_sec": 330.685, "pipeline_run_sec": 303.730,
     "source": "~/bench/out/diag_forks1.log + marker_diag_forks1.log", "reps": 1},
]

# ---- caching ----
summary["caching"] = {
    "pipen_scope_phases": pipen_scope.get("phases", []),
    "pipen_scope_agg_output": pipen_scope.get("agg_output_content"),
    "pipen_scope_modified_input": pipen_scope.get("modified_input"),
    "pipen_timing": [r for r in pipen5 if r["step"] == "5_caching_timing"],
    "smk_scope_phases": smk_scope.get("phases", []),
    "smk_scope_modified_input": smk_scope.get("modified_input"),
}

# ---- observed parallelism from marker timestamps ----
for label, markers in [
    ("pipen_s4_n20_f1", "marker_s4_n20_f1_r1"),
    ("pipen_s4_n20_f2", "marker_s4_n20_f2_r1"),
    ("pipen_s4_n20_f4", "marker_s4_n20_f4_r1"),
    ("pipen_s4_n20_f32", "marker_s4_n20_f32_r1"),
    ("pipen_s3_n100_r1", "marker_s3_n100_r1"),
    ("pipen_s3_n500_r1", "marker_s3_n500_r1"),
    ("smk_s4_n20_c1", "marker_smk_s4_n20_c1"),
    ("smk_s4_n20_c2", "marker_smk_s4_n20_c2"),
    ("smk_s4_n20_c4", "marker_smk_s4_n20_c4"),
    ("smk_s4_n20_c32", "marker_smk_s4_n20_c32"),
    ("smk_s3_n500_r1", "marker_smk_s3_n500_r1"),
]:
    mpath = OUT / f"{markers}.log"
    if not mpath.exists():
        continue
    out = subprocess.run([str(HOME / "bench/.venv/bin/python"),
                          str(DEST / "analyse_marker.py"), str(mpath)],
                         capture_output=True, text=True)
    summary["observed_parallelism"][label] = out.stdout.strip().splitlines()

(DEST / "raw").mkdir(parents=True, exist_ok=True)
(DEST / "raw" / "summary.json").write_text(json.dumps(summary, indent=2))
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps({k: v for k, v in summary.items() if k != "caching"}, indent=2)[:6000])
print("\n=== CACHING ===")
print(json.dumps(summary["caching"], indent=2)[:4000])
