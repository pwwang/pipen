#!/usr/bin/env python3
"""Compute every ratio/total quoted in RESULTS.md, so no number is hand-computed.

Paths come from ``bench.env`` (see ``bench_config.py``).  Sections whose inputs
are absent (reduced-size run) are reported as ``null`` and listed under
``"missing"`` rather than aborting the report.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_config import load  # noqa: E402

CFG = load()
OUT = CFG.path("out_root")
ARCHIVE = CFG.path("archive") if CFG.raw("archive") else None
missing: list[str] = []


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        missing.append(f"{path.name}: {exc}")
        return default


summary = read_json(OUT / "summary.json", {})
evidence = read_json(OUT / "evidence_caching.json", {})
env = read_json(OUT / "environment.json", {})
missing.extend(summary.get("missing_inputs", []))


def med(vals):
    """Median of the recorded reps (the archived tables quote medians)."""
    v = sorted(vals)
    if not v:
        return None
    if len(v) % 2:
        return v[len(v) // 2]
    return (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2


d: dict = {}
d["config"] = CFG.as_dict()
d["env"] = {
    "wsl_distro": env.get("wsl_distro"), "kernel": env.get("kernel_release"),
    "nproc": env.get("nproc"), "cpu": env.get("cpu_model_name"),
    "mem_total": env.get("mem_total"),
    "python": (env.get("python_version") or "").split("|")[0].strip(),
    "pipen_version": env.get("pipen_version"),
    "pipen_git_commit": env.get("pipen_git_commit"),
    "pipen_git_describe": env.get("pipen_git_describe"),
    "deps": env.get("dependency_versions"), "java": (env.get("java") or "").splitlines()[0]
    if env.get("java") else None,
    "disk": env.get("df"),
    "pipen_runinfo_version": env.get("pipen_runinfo_version"),
}


# ---- scaling table ----
def scaling(src, key_n="n"):
    out = []
    recs = summary.get(src, {}).get("records", [])
    if not recs:
        if src not in missing:
            missing.append(src)
        return out
    for n in sorted({r[key_n] for r in recs}):
        rs = [r for r in recs if r[key_n] == n]
        wall = [r["wall_sec"] for r in rs]
        floor = rs[0]["sleep_floor_sec"]
        oh = [round(w - floor, 3) for w in wall]
        out.append({
            "n": n, "reps": len(rs),
            "wall_median": round(med(wall), 3), "wall_min": round(min(wall), 3),
            "wall_max": round(max(wall), 3),
            "wall_all": [round(w, 3) for w in wall],
            "sleep_floor": floor,
            "overhead_median": round(med(oh), 3),
            "overhead_per_job_median": round(med(oh) / n, 4),
            "overhead_per_job_min": round(min(oh) / n, 4),
            "overhead_per_job_max": round(max(oh) / n, 4),
            "rss_median_mb": round(med([r["peak_tree_rss_mb"] for r in rs]), 1),
            "jobs": rs[0].get("jobs"),
        })
    return out


d["pipen_scaling"] = scaling("pipen_scaling")
d["smk_scaling"] = scaling("smk_scaling")

# ---- head to head ----
p, s = d["pipen_scaling"], d["smk_scaling"]
d["head_to_head"] = [
    {"n": a["n"], "pipen_wall_median": a["wall_median"], "smk_wall_median": b["wall_median"],
     "ratio_pipen_over_smk": round(a["wall_median"] / b["wall_median"], 2),
     "pipen_overhead_per_job": a["overhead_per_job_median"],
     "smk_overhead_per_job": b["overhead_per_job_median"],
     "smk_jobs_from_log": b.get("jobs")}
    for a, b in zip(p, s)
]

# ---- concurrency ----
pc = summary.get("pipen_concurrency", {}).get("records", [])
sc = summary.get("smk_concurrency", {}).get("records", [])
d["pipen_concurrency"] = [
    {"forks": r["forks"], "wall_sec": r["wall_sec"], "pipeline_run_sec": r.get("pipeline_run_sec"),
     "sleep_floor": r["sleep_floor_sec"], "speedup_vs_forks1": r.get("speedup_vs_forks1"),
     "rss_mb": r["peak_tree_rss_mb"], "jobs": r.get("jobs")} for r in pc]
d["smk_concurrency"] = [
    {"cores": r["forks"], "wall_sec": r["wall_sec"], "sleep_floor": r["sleep_floor_sec"],
     "speedup_vs_cores1": r.get("speedup_vs_cores1"), "rss_mb": r["peak_tree_rss_mb"],
     "jobs": (r["jobs_executed"] // 2) if r.get("jobs_executed") is not None else None}
    for r in sc]
d["n100_diagnostic"] = summary.get("pipen_concurrency", {}).get("n100_single_rep_diagnostic", [])

# ---- observed parallelism (parsed text -> numbers) ----
par = {}
for k, lines in (summary.get("observed_parallelism") or {}).items():
    blob = " ".join(lines)
    def grab(pattern, default="0"):
        m = re.search(pattern, blob)
        return m.group(1) if m else default
    try:
        par[k] = {
            "jobs": int(grab(r"jobs=(\d+)")),
            "span_sec": float(grab(r"span=([\d.]+)s")),
            "peak_concurrent_jobs": int(grab(r"peak_concurrent_jobs=(\d+)")),
            "mean_concurrent_jobs": float(grab(r"mean_concurrent_jobs=([\d.]+)")),
            "sum_job_durations_sec": float(grab(r"sum_job_durations=([\d.]+)s")),
            "median_job_duration_sec": float(grab(r"job_duration_s: min=[\d.]+ median=([\d.]+)")),
        }
    except ValueError:
        missing.append(f"observed_parallelism[{k}]")
        continue
    par[k]["job_start_rate_per_sec"] = round(par[k]["jobs"] / par[k]["span_sec"], 1) if par[k]["span_sec"] else None
    par[k]["mean_job_start_gap_ms"] = round(1000 * par[k]["span_sec"] / par[k]["jobs"], 2) if par[k]["span_sec"] else None
d["observed_parallelism"] = par

# ---- caching ----
caching = summary.get("caching", {})
pipen_timing = caching.get("pipen_timing", [])


def pick(suffix):
    return next((r for r in pipen_timing if r["tag"].endswith(suffix)), None)


cold, warm1, warm2 = pick("cold_r1"), pick("warm1_r1"), pick("warm2_r1")
if cold and warm1:
    d["pipen_caching_timing"] = {
        "n": cold["n"], "total_jobs": cold["jobs_executed"] + warm1["jobs_executed"],
        "cold_run_jobs": cold["jobs_executed"], "cold_wall_sec": cold["wall_sec"],
        "warm1_jobs": warm1["jobs_executed"], "warm1_wall_sec": warm1["wall_sec"],
        "warm2_jobs": warm2["jobs_executed"] if warm2 else None,
        "warm2_wall_sec": warm2["wall_sec"] if warm2 else None,
        "speedup_cold_over_warm1": round(cold["wall_sec"] / warm1["wall_sec"], 2),
        "speedup_cold_over_warm2": round(cold["wall_sec"] / warm2["wall_sec"], 2) if warm2 else None,
        "cold_run_pipeline_sec": cold.get("pipeline_run_sec"),
        "warm1_run_pipeline_sec": warm1.get("pipeline_run_sec"),
        "runinfo_version": cold.get("runinfo_version"),
        "job_executions_saved": cold["jobs_executed"] - warm1["jobs_executed"],
    }
else:
    d["pipen_caching_timing"] = None
    missing.append("pipen_caching_timing (cold/warm timing runs absent)")

d["pipen_caching_scope"] = [
    {"phase": r["tag"].replace("s5_", ""), "note": r.get("note"), "wall_sec": r["wall_sec"],
     "jobs_executed": r["jobs_executed"], "jobs_by_proc": r["jobs_by_proc"],
     "cached_jobs_log_lines": [c.split("core", 1)[-1].strip() for c in r.get("cached_jobs_log_lines", [])]}
    for r in caching.get("pipen_scope_phases", [])]
d["smk_caching_scope"] = [
    {"phase": r["tag"].replace("smk_s5_", ""), "note": r.get("note"), "wall_sec": r["wall_sec"],
     "jobs_executed": r["jobs_executed"], "jobs_by_proc": r["jobs_by_proc"],
     "jobs_from_log_excl_target_rule": r.get("jobs_from_log_excl_target_rule")}
    for r in caching.get("smk_scope_phases", [])]
d["pipen_scope_agg_output"] = caching.get("pipen_scope_agg_output")
d["pipen_scope_agg_file"] = caching.get("pipen_scope_agg_file")
d["cache_freshness"] = evidence.get("cache_freshness_proof")
d["per_job_table_pipen"] = evidence.get("per_job_table_pipen")
d["phase_executed_jobs_pipen"] = evidence.get("phase_executed_jobs")
d["evidence_unavailable"] = evidence.get("unavailable")
d["missing"] = sorted(set(missing))

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "derived_numbers.json").write_text(json.dumps(d, indent=2))
if ARCHIVE:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    (ARCHIVE / "derived_numbers.json").write_text(json.dumps(d, indent=2))

print(json.dumps({k: v for k, v in d.items() if k not in
                  ("cache_freshness", "per_job_table_pipen", "phase_executed_jobs_pipen",
                   "pipen_caching_scope", "smk_caching_scope", "config")}, indent=2))
if d["missing"]:
    print("\n=== MISSING INPUTS ===")
    print(json.dumps(d["missing"], indent=2))
