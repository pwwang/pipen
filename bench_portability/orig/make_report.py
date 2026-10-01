#!/usr/bin/env python3
"""Compute every ratio/total quoted in RESULTS.md, so no number is hand-computed."""
import json
from pathlib import Path

HOME = Path.home()
OUT = HOME / "bench" / "out"
DEST = Path("/mnt/f/E/hermes-workspace/pipen/bench")
RAW = DEST / "raw"

summary = json.loads((OUT / "summary.json").read_text())
evidence = json.loads((OUT / "evidence_caching.json").read_text())
env = json.loads((OUT / "environment.json").read_text())


def med3(vals):
    v = sorted(vals)
    return v[1]


d = {}
d["env"] = {
    "wsl_distro": env["wsl_distro"], "kernel": env["kernel_release"],
    "nproc": env["nproc"], "cpu": env["cpu_model_name"],
    "mem_total": env["mem_total"], "python": env["python_version"].split("|")[0].strip(),
    "pipen_version": env["pipen_version"], "pipen_git_commit": env["pipen_git_commit"],
    "pipen_git_describe": env["pipen_git_describe"],
    "deps": env["dependency_versions"], "java": env["java"].splitlines()[0],
    "disk": env["df"],
}

# ---- scaling table ----
def scaling(src, key_n="n"):
    out = []
    recs = summary[src]["records"]
    for n in sorted({r[key_n] for r in recs}):
        rs = [r for r in recs if r[key_n] == n]
        wall = [r["wall_sec"] for r in rs]
        floor = rs[0]["sleep_floor_sec"]
        oh = [round(w - floor, 3) for w in wall]
        out.append({
            "n": n, "reps": len(rs),
            "wall_median": round(med3(wall), 3), "wall_min": round(min(wall), 3),
            "wall_max": round(max(wall), 3),
            "wall_all": [round(w, 3) for w in wall],
            "sleep_floor": floor,
            "overhead_median": round(med3(oh), 3),
            "overhead_per_job_median": round(med3(oh) / n, 4),
            "overhead_per_job_min": round(min(oh) / n, 4),
            "overhead_per_job_max": round(max(oh) / n, 4),
            "rss_median_mb": round(med3([r["peak_tree_rss_mb"] for r in rs]), 1),
            "jobs": rs[0]["jobs"],
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
pc = summary["pipen_concurrency"]["records"]
sc = summary["smk_concurrency"]["records"]
d["pipen_concurrency"] = [
    {"forks": r["forks"], "wall_sec": r["wall_sec"], "pipeline_run_sec": r["pipeline_run_sec"],
     "sleep_floor": r["sleep_floor_sec"], "speedup_vs_forks1": r["speedup_vs_forks1"],
     "rss_mb": r["peak_tree_rss_mb"], "jobs": r["jobs"]} for r in pc]
d["smk_concurrency"] = [
    {"cores": r["forks"], "wall_sec": r["wall_sec"], "sleep_floor": r["sleep_floor_sec"],
     "speedup_vs_cores1": r["speedup_vs_cores1"], "rss_mb": r["peak_tree_rss_mb"],
     "jobs": r["jobs_executed"] // 2} for r in sc]
d["n100_diagnostic"] = summary["pipen_concurrency"]["n100_single_rep_diagnostic"]

# ---- observed parallelism (parsed text -> numbers) ----
par = {}
import re as _re
for k, lines in summary["observed_parallelism"].items():
    blob = " ".join(lines)
    kv = dict(_re.findall(r"(\w+)=([\d.eE+-]+)s?\b", blob))
    kv["jobs"] = (_re.search(r"jobs=(\d+)", blob) or [None, "0"])[1]
    kv["span"] = (_re.search(r"span=([\d.]+)s", blob) or [None, "0"])[1]
    kv["peak_concurrent_jobs"] = (_re.search(r"peak_concurrent_jobs=(\d+)", blob) or [None, "0"])[1]
    kv["mean_concurrent_jobs"] = (_re.search(r"mean_concurrent_jobs=([\d.]+)", blob) or [None, "0"])[1]
    kv["sum_job_durations"] = (_re.search(r"sum_job_durations=([\d.]+)s", blob) or [None, "0"])[1]
    kv["job_duration_s"] = "min=0 median=" + ((_re.search(r"job_duration_s: min=[\d.]+ median=([\d.]+)", blob) or [None, "0"])[1])
    par[k] = {
        "jobs": int(kv.get("jobs", "0").split()[0]),
        "span_sec": float(kv.get("span", "0 s").rstrip("s").split()[-1]),
        "peak_concurrent_jobs": int(kv.get("peak_concurrent_jobs", "0").split()[0]),
        "mean_concurrent_jobs": float(kv.get("mean_concurrent_jobs", "0").split()[0]),
        "sum_job_durations_sec": float(kv.get("sum_job_durations", "0s").rstrip("s").split()[-1]),
        "median_job_duration_sec": float(kv.get("job_duration_s", "min=0 median=0").split("median=")[1].split()[0]),
    }
    par[k]["job_start_rate_per_sec"] = round(par[k]["jobs"] / par[k]["span_sec"], 1) if par[k]["span_sec"] else None
    par[k]["mean_job_start_gap_ms"] = round(1000 * par[k]["span_sec"] / par[k]["jobs"], 2) if par[k]["span_sec"] else None
d["observed_parallelism"] = par

# ---- caching ----
pipen_time = {r["tag"]: r for r in summary["caching"]["pipen_timing"]}
cold = [r for r in summary["caching"]["pipen_timing"] if r["tag"].endswith("cold_r1")][0]
warm1 = [r for r in summary["caching"]["pipen_timing"] if r["tag"].endswith("warm1_r1")][0]
warm2 = [r for r in summary["caching"]["pipen_timing"] if r["tag"].endswith("warm2_r1")][0]
d["pipen_caching_timing"] = {
    "n": cold["n"], "total_jobs": cold["jobs_executed"] + warm1["jobs_executed"],
    "cold_run_jobs": cold["jobs_executed"], "cold_wall_sec": cold["wall_sec"],
    "warm1_jobs": warm1["jobs_executed"], "warm1_wall_sec": warm1["wall_sec"],
    "warm2_jobs": warm2["jobs_executed"], "warm2_wall_sec": warm2["wall_sec"],
    "speedup_cold_over_warm1": round(cold["wall_sec"] / warm1["wall_sec"], 2),
    "speedup_cold_over_warm2": round(cold["wall_sec"] / warm2["wall_sec"], 2),
    "job_executions_saved": cold["jobs_executed"] - warm1["jobs_executed"],
}
d["pipen_caching_scope"] = [
    {"phase": r["tag"].replace("s5_", ""), "note": r["note"], "wall_sec": r["wall_sec"],
     "jobs_executed": r["jobs_executed"], "jobs_by_proc": r["jobs_by_proc"],
     "cached_jobs_log_lines": [c.split("core", 1)[-1].strip() for c in r["cached_jobs_log_lines"]]}
    for r in summary["caching"]["pipen_scope_phases"]]
d["smk_caching_scope"] = [
    {"phase": r["tag"].replace("smk_s5_", ""), "note": r["note"], "wall_sec": r["wall_sec"],
     "jobs_executed": r["jobs_executed"], "jobs_by_proc": r["jobs_by_proc"],
     "jobs_from_log_excl_target_rule": r.get("jobs_from_log_excl_target_rule")}
    for r in summary["caching"]["smk_scope_phases"]]
d["cache_freshness"] = evidence["cache_freshness_proof"]
d["per_job_table_pipen"] = evidence["per_job_table_pipen"]
d["phase_executed_jobs_pipen"] = evidence["phase_executed_jobs"]

(RAW / "derived_numbers.json").write_text(json.dumps(d, indent=2))
(OUT / "derived_numbers.json").write_text(json.dumps(d, indent=2))

print(json.dumps({k: v for k, v in d.items() if k not in
                  ("cache_freshness", "per_job_table_pipen", "phase_executed_jobs_pipen",
                   "pipen_caching_scope", "smk_caching_scope")}, indent=2))
