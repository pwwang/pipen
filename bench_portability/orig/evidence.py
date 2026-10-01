#!/usr/bin/env python3
"""Build the per-job invalidation evidence table + cache-freshness proof."""
import json
import re
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

HOME = Path.home()
OUT = HOME / "bench" / "out"
DEST = Path("/mnt/f/E/hermes-workspace/pipen/bench")
RAW = DEST / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# ---- 1. attach Snakemake-log job counts (independent cross-check) ----
summary = json.loads((OUT / "summary.json").read_text())


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

# ---- 2. per-job invalidation evidence table (pipen) ----
SCOPE = HOME / "bench" / "wd_s5_scope" / "CachePipeline"
PHASE_FILES = {
    "r1_cold": OUT / "marker_s5_r1_cold.log",
    "r3_input4_changed": OUT / "marker_s5_r3_input3_changed.log",
    "r4_mid_script_changed": OUT / "marker_s5_r4_mid_script_changed.log",
}
# per-phase executed job ids, read directly from the phase logs of the driver run
records5 = json.loads((OUT / "pipen_records_step5.json").read_text())
phase_exec = {}
for rec in records5:
    if rec["step"] == "5_caching_scope":
        name = rec["tag"].replace("s5_", "")
        # the tags in the log files use the phase label; map back
        phase_exec[name] = rec["executed_detail"]

# driver writes per-phase marker files named marker_s5_<label>.log
phase_exec = {}
for label, tag in [("r1_cold", "s5_r1_cold"), ("r2_rerun", "s5_r2_rerun"),
                   ("r3_input4_changed", "s5_r3_input3_changed"),
                   ("r4_mid_script_changed", "s5_r4_mid_script_changed"),
                   ("r5_rerun", "s5_r5_rerun")]:
    f = OUT / f"marker_{tag}.log"
    if f.exists():
        phase_exec[label] = [" ".join(l.split()[:2]) for l in f.read_text().splitlines() if l.strip()]

table = []
procs = [("Read", 8), ("Mid", 8), ("Side", 8), ("Agg", 1)]
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
            hit = [d for d in detail if d.split()[0] == proc and
                   (d.split()[1] == str(idx) or d.split()[1].replace("in", "").replace(".txt", "") == str(idx))]
            # match by job dir content is ambiguous; match by index for Agg and by
            # the file naming convention for the branches
            reran[label] = bool(hit)
        table.append({
            "job_dir": str(jobdir.relative_to(SCOPE)),
            "output_files": [f.name for f in files],
            "output_content": key_candidates,
            "output_mtime": datetime.fromtimestamp(
                max((f.stat().st_mtime for f in files), default=0)).isoformat(timespec="microseconds"),
            "reran_in_phase": {k: v for k, v in reran.items()},
        })

# ---- 3. cache-freshness proof (per-branch, from the non-shared job outputs) ----
freshness = {
    "modified_input_file": str(HOME / "bench" / "cache_inputs_small" / "in4.txt"),
    "modified_input_content": (HOME / "bench" / "cache_inputs_small" / "in4.txt").read_text(),
    "untouched_input_example": {
        "file": str(HOME / "bench" / "cache_inputs_small" / "in3.txt"),
        "content": (HOME / "bench" / "cache_inputs_small" / "in3.txt").read_text(),
    },
    "note_on_modified_content": (
        "the driver overwrote in4.txt with the literal string 'line3-v2' (hardcoded "
        "new-content string); in4.txt originally held 'line4-v1'. Only the fact that "
        "the content changed matters for the invalidation test."
    ),
    "mid_branch_output_after_all_phases": {},
    "agg_exported_output": {},
    "shared_export_caveat": (
        "the Agg job's output dir is a symlink to <cwd>/CachePipeline-output/Agg, i.e. a "
        "single path shared by every run of a same-named pipeline in the same cwd; the "
        "later N=100 timing run overwrote this file, so the per-branch per-job outputs in "
        "the workdir are used as the freshness proof instead."
    ),
}
for i in range(8):
    p = sorted((SCOPE / "Mid" / str(i)).rglob("m-r-in*.txt"))
    freshness["mid_branch_output_after_all_phases"][f"in{i}.txt"] = {
        "produced_by": "Mid job %d" % i,
        "output_file": str(p[0]) if p else None,
        "content": p[0].read_text().strip() if p else None,
        "branch_4_was_invalidated": i == 4,
    }
for cand in sorted(set(list(Path(HOME / "bench").glob("CachePipeline-output/**/agg.txt"))
                       + list((HOME / "bench" / "wd_s5_scope").rglob("agg.txt")))):
    real = cand.resolve()
    freshness["agg_exported_output"][str(cand)] = {
        "resolved": str(real),
        "mtime": datetime.fromtimestamp(real.stat().st_mtime).isoformat(timespec="microseconds"),
        "n_lines": len(real.read_text().splitlines()),
        "contains_line3_v2": "line3-v2" in real.read_text(),
    }
freshness["modified_value_propagated_to_mid_branch4"] = (
    freshness["mid_branch_output_after_all_phases"]["in4.txt"]["content"] or ""
).endswith("line3-v2")

evidence = {
    "per_job_table_pipen": table,
    "phase_executed_jobs": phase_exec,
    "cache_freshness_proof": freshness,
}
(RAW / "evidence_caching.json").write_text(json.dumps(evidence, indent=2))
(OUT / "evidence_caching.json").write_text(json.dumps(evidence, indent=2))
(DEST / "raw" / "summary.json").write_text(json.dumps(summary, indent=2))

print("=== freshness proof ===")
print(json.dumps(freshness, indent=2))
print("=== per-job table (pipen, first 6 rows) ===")
print(json.dumps(table[:6], indent=2))
print("=== phase executed jobs (pipen) ===")
print(json.dumps(phase_exec, indent=1))
