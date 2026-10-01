#!/usr/bin/env python3
"""Summarise the raw per-run records into ``summary.json``.

Paths come from ``bench.env`` (see ``bench_config.py``).  Missing arms are
tolerated: a reduced-size run simply produces a smaller summary and records what
was absent in ``summary["missing_inputs"]`` instead of crashing.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_config import load  # noqa: E402

CFG = load()
ROOT = CFG.root
OUT = CFG.path("out_root")
ARCHIVE = CFG.raw("archive")
ARCHIVE = CFG.path("archive") if ARCHIVE else None
missing: list[str] = []


def load(p: Path):
    return json.loads(Path(p).read_text()) if Path(p).exists() else ([] if p.suffix == ".json" else {})


def load_records(primary: str, step_prefixes: tuple[str, ...]) -> list:
    """Preferred arm file, else the legacy combined records filtered by step."""
    p = OUT / primary
    if p.exists():
        data = json.loads(p.read_text())
        if data:
            return data
    legacy = OUT / "pipen_records.json" if step_prefixes[0].startswith(("3", "4", "5")) else OUT / "smk_records.json"
    if legacy.exists():
        data = json.loads(legacy.read_text())
        sel = [r for r in data if r.get("step", "").startswith(step_prefixes)]
        if sel:
            return sel
    missing.append(primary)
    return []


def load_scope(name: str) -> dict:
    p = OUT / name
    if p.exists():
        data = json.loads(p.read_text())
        if data:
            return data
    missing.append(name)
    return {}


def med(vals):
    v = sorted(vals)
    n = len(v)
    if n == 0:
        return None
    return round(v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2, 3)


def summ(records, key, n_key):
    """group -> {median,min,max,all}"""
    groups = {}
    for r in records:
        groups.setdefault(r[n_key], []).append(r[key])
    return {k: {"median": med(v), "min": round(min(v), 3), "max": round(max(v), 3),
                "n_reps": len(v), "all": [round(x, 3) for x in v]}
            for k, v in sorted(groups.items())}


pipen34 = load_records("pipen_records_steps34.json", ("3_", "4_"))
pipen5 = load_records("pipen_records_step5.json", ("5_",))
pipen_scope = load_scope("pipen_cache_scope.json")
smk34 = load_records("smk_records_steps34.json", ("3_", "4_"))
smk5 = load_records("smk_records_step5.json", ("5_",))
smk_scope = load_scope("smk_cache_scope.json")


def resolve(path_str: str) -> Path:
    """Marker/log paths recorded by the drivers are absolute; be forgiving."""
    p = Path(path_str)
    if p.exists():
        return p
    for cand in (OUT / p.name, OUT / "markers" / p.name,
                 CFG.path("work_root") / "markers" / p.name, ROOT / p.name):
        if cand.exists():
            return cand
    return p


def job_count_from_marker(rec):
    """Jobs = number of '<proc>_start' marker lines (DAG pipeline) or all lines."""
    p = resolve(rec["marker_log"])
    if not p.exists():
        return None
    kinds = [l.split()[0] for l in p.read_text().splitlines() if l.strip()]
    starts = [k for k in kinds if k.endswith("_start")]
    return len(starts) if starts else len(kinds)


summary = {"config": CFG.as_dict(), "pipen_scaling": {}, "pipen_concurrency": {},
           "smk_scaling": {}, "smk_concurrency": {}, "caching": {},
           "observed_parallelism": {}}

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
base = next((r["wall_sec"] for r in p4 if r["forks"] == 1), None)
for r in p4:
    r["speedup_vs_forks1"] = round(base / r["wall_sec"], 2) if base else None
summary["pipen_concurrency"] = {"records": p4}
s4 = [r for r in smk34 if r["step"] == "4_concurrency"]
base = next((r["wall_sec"] for r in s4 if r["forks"] == 1), None)
for r in s4:
    r["speedup_vs_cores1"] = round(base / r["wall_sec"], 2) if base else None
summary["smk_concurrency"] = {"records": s4}

# N=100 single-rep data points measured during the diagnostic phase of the
# ARCHIVED full-size run.  They are quoted from bench/raw/logs_pipen/*.log and
# are NOT re-measured here; the provenance is recorded with them.
summary["pipen_concurrency"]["n100_single_rep_diagnostic"] = [
    {"n": 100, "forks": 32, "wall_sec": 16.437, "pipeline_run_sec": 15.923,
     "source": "archived run: bench/raw/logs_pipen/diag_sleep05.log + marker_diag_sleep05.log",
     "measured_in": "archived full-size run (RESULTS.md section 4)", "reps": 1},
    {"n": 100, "forks": 1, "wall_sec": 330.685, "pipeline_run_sec": 303.730,
     "source": "archived run: bench/raw/logs_pipen/diag_forks1.log + marker_diag_forks1.log",
     "measured_in": "archived full-size run (RESULTS.md section 4)", "reps": 1},
]

# ---- caching ----
summary["caching"] = {
    "pipen_scope_phases": pipen_scope.get("phases", []),
    "pipen_scope_agg_output": pipen_scope.get("agg_output_content"),
    "pipen_scope_agg_file": pipen_scope.get("agg_output_file"),
    "pipen_scope_modified_input": pipen_scope.get("modified_input"),
    "pipen_timing": [r for r in pipen5 if r.get("step") == "5_caching_timing"],
    "smk_scope_phases": smk_scope.get("phases", []),
    "smk_scope_modified_input": smk_scope.get("modified_input"),
}

# ---- observed parallelism from marker timestamps ----
# Names follow the harness tag scheme; whatever the run produced is picked up.
def marker_names(records):
    seen, out = set(), []
    for r in records:
        tag = r.get("tag")
        if tag and tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


for label_rec in (p4 + p3 + s4 + s3):
    tag = label_rec.get("tag")
    if not tag:
        continue
    label = tag if tag.startswith("smk_") else f"pipen_{tag}"
    if label in summary["observed_parallelism"]:
        continue
    mpath = None
    for cand in (OUT / "markers" / f"marker_{tag}.log", OUT / f"marker_{tag}.log",
                 CFG.path("work_root") / "markers" / f"marker_{tag}.log"):
        if cand.exists():
            mpath = cand
            break
    if mpath is None:
        continue
    out = subprocess.run([sys.executable, str(ROOT / "analyse_marker.py"), str(mpath)],
                         capture_output=True, text=True)
    summary["observed_parallelism"][label] = out.stdout.strip().splitlines()

summary["missing_inputs"] = missing
summary["artefact_dir"] = str(OUT)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
if ARCHIVE:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    (ARCHIVE / "summary.json").write_text(json.dumps(summary, indent=2))

print(json.dumps({k: v for k, v in summary.items() if k != "caching"}, indent=2)[:6000])
print("\n=== CACHING ===")
print(json.dumps(summary["caching"], indent=2)[:4000])
if missing:
    print("\n=== MISSING INPUTS (reduced run or incomplete arms) ===")
    print(json.dumps(missing, indent=2))
