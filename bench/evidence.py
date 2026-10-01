#!/usr/bin/env python3
"""Build the per-job invalidation evidence table + cache-freshness proof.

Paths come from ``bench.env`` (see ``bench_config.py``).  Every section degrades
gracefully: if the corresponding run is absent (reduced-size run), the field is
present but null and the reason is recorded under ``"unavailable"``, so
``make_report.py`` can still produce derived_numbers.json.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_config import load  # noqa: E402

CFG = load()
OUT = CFG.path("out_root")
WORK = CFG.path("work_root")
ARCHIVE = CFG.path("archive") if CFG.raw("archive") else None
N_SCOPE = CFG.int("cache_scope_n")

unavailable: dict[str, str] = {}


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        unavailable.setdefault(str(path), str(exc))
        return default


summary = read_json(OUT / "summary.json", {})

# ---- 1. attach Snakemake-log job counts (independent cross-check) ----
def log_job_counts(path):
    lg = Path(path)
    if not lg.exists():
        return None
    txt = lg.read_text(errors="replace")
    fin = re.findall(r"Finished jobid: \d+ \(Rule: (\w+)\)", txt)
    if not fin:
        return None
    c = Counter(fin)
    c.pop("all", None)
    return {"total_excl_target_rule": sum(c.values()), "by_rule": dict(c)}


for group in ("pipen_scaling", "pipen_concurrency", "smk_scaling", "smk_concurrency"):
    for rec in summary.get(group, {}).get("records", []):
        lc = log_job_counts(rec["log"])
        if lc:
            rec["jobs_from_tool_log"] = lc

# ---- 2. per-phase executed jobs (from the scope-run records) ----
# Each phase appends one marker line per *job execution*, so the re-run set is
# counted directly.  Primary source: the phase records written by the driver.
SCOPE = WORK / "wd_s5_scope" / "CachePipeline"
records5 = read_json(OUT / "pipen_records_step5.json", []) or []
phase_exec: dict[str, list] = {}
for rec in records5:
    if rec.get("step") == "5_caching_scope":
        phase_exec[rec["tag"].replace("s5_", "")] = rec.get("executed_detail", [])
# fallback: per-phase marker logs (only if the records carried no detail)
if not any(phase_exec.values()):
    for label, tag in [("r1_cold", "s5_r1_cold"), ("r2_rerun", "s5_r2_rerun"),
                       ("r3_input3_changed", "s5_r3_input3_changed"),
                       ("r4_mid_script_changed", "s5_r4_mid_script_changed"),
                       ("r5_rerun", "s5_r5_rerun")]:
        f = OUT / "markers" / f"marker_{tag}.log"
        if f.exists() and f.read_text().strip():
            phase_exec[label] = [" ".join(l.split()[:2]) for l in f.read_text().splitlines() if l.strip()]

# ---- 3. per-job table (pipen, caching scope run) ----
table = []
procs = [("Read", N_SCOPE), ("Mid", N_SCOPE), ("Side", N_SCOPE), ("Agg", 1)]
for proc, cnt in procs:
    for idx in range(cnt):
        jobdir = SCOPE / proc / str(idx)
        outdir = jobdir / "output"
        files = sorted(p for p in outdir.rglob("*") if p.is_file()) if outdir.exists() else []
        key_candidates = []
        for f in files:
            try:
                text = f.read_text()
            except Exception:
                text = ""
            key_candidates.append(f"{f.name}={text.strip()}")
        reran = {}
        for label, detail in phase_exec.items():
            hit = False
            for d in detail:
                parts = d.split()
                if len(parts) < 2 or parts[0] != proc:
                    continue
                digits = re.findall(r"\d+", parts[1])
                if proc == "Agg":
                    # the aggregation job has no per-input index
                    hit = True
                elif digits and int(digits[0]) == idx:
                    hit = True
            reran[label] = hit
        table.append({
            "job_dir": str(jobdir.relative_to(SCOPE)),
            "output_files": [f.name for f in files],
            "output_content": key_candidates,
            "output_mtime": datetime.fromtimestamp(
                max((f.stat().st_mtime for f in files), default=0)).isoformat(timespec="microseconds"),
            "reran_in_phase": {k: v for k, v in reran.items()},
        })
if not SCOPE.exists():
    unavailable["per_job_table_pipen"] = f"{SCOPE} not found (caching-scope run absent)"

# ---- 4. cache-freshness proof (per-branch, from the non-shared job outputs) ----
small = WORK / "cache_inputs_small"
mod_idx = max(0, N_SCOPE - 4)
freshness = {
    "modified_input_file": str(small / f"in{mod_idx}.txt"),
    "modified_input_content": (small / f"in{mod_idx}.txt").read_text()
    if (small / f"in{mod_idx}.txt").exists() else None,
    "untouched_input_example": {
        "file": str(small / "in0.txt"),
        "content": (small / "in0.txt").read_text() if (small / "in0.txt").exists() else None,
    },
    "note_on_modified_content": (
        "the driver overwrites the modified input with the literal string "
        "'line3-v2' (the same literal the archived run used); the original file "
        "held 'line<N>-v1'.  Only the fact that the content changed matters for "
        "the invalidation test."
    ),
    "mid_branch_output_after_all_phases": {},
    "agg_exported_output": {},
    "shared_export_caveat": (
        "the Agg job's output dir is a symlink to <cwd>/CachePipeline-output/Agg, i.e. a "
        "single path shared by every run of a same-named pipeline in the same cwd; a later "
        "run overwrites this file, so the per-branch per-job outputs in the workdir are "
        "used as the freshness proof instead."
    ),
}
for i in range(N_SCOPE):
    p = sorted((SCOPE / "Mid" / str(i)).rglob("m-r-in*.txt")) if (SCOPE / "Mid").exists() else []
    freshness["mid_branch_output_after_all_phases"][f"in{i}.txt"] = {
        "produced_by": "Mid job %d" % i,
        "output_file": str(p[0]) if p else None,
        "content": p[0].read_text().strip() if p else None,
        "branch_was_invalidated": i == mod_idx,
    }
for cand in sorted(set(list(Path.cwd().glob("CachePipeline-output/**/agg.txt"))
                       + list(OUT.glob("CachePipeline-output/**/agg.txt"))
                       + list(WORK.rglob("agg.txt")))):
    real = cand.resolve()
    freshness["agg_exported_output"][str(cand)] = {
        "resolved": str(real),
        "mtime": datetime.fromtimestamp(real.stat().st_mtime).isoformat(timespec="microseconds"),
        "n_lines": len(real.read_text().splitlines()),
    }
entry = freshness["mid_branch_output_after_all_phases"][f"in{mod_idx}.txt"]
freshness["modified_value_propagated_to_mid_branch"] = bool(
    entry["content"] and entry["content"].endswith("line3-v2"))

evidence = {
    "config": CFG.as_dict(),
    "per_job_table_pipen": table,
    "phase_executed_jobs": phase_exec,
    "cache_freshness_proof": freshness,
    "unavailable": unavailable,
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "evidence_caching.json").write_text(json.dumps(evidence, indent=2))
if ARCHIVE:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    (ARCHIVE / "evidence_caching.json").write_text(json.dumps(evidence, indent=2))
    (ARCHIVE / "summary.json").write_text(json.dumps(summary, indent=2))

print("=== freshness proof ===")
print(json.dumps(freshness, indent=2))
print("=== per-job table (pipen, first 4 rows) ===")
print(json.dumps(table[:4], indent=2))
print("=== phase executed jobs (pipen) ===")
print(json.dumps(phase_exec, indent=1))
if unavailable:
    print("=== unavailable ===")
    print(json.dumps(unavailable, indent=2))
