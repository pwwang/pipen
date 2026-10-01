#!/usr/bin/env python3
"""Snakemake counterpart of driver_pipen.py: same DAGs, same metrics.

Every path and protocol size comes from ``bench.env`` (see ``bench_config.py``).

Usage::

    driver_smk.py [arms]        arms: any of "3", "4", "5", "345" (default)

Runs the Snakefiles in ``<ROOT>/smk_dag`` (scaling/concurrency, equivalent to
bench_pipen_dag.py) and ``<ROOT>/smk_cache`` (caching, equivalent to
bench_cache_dag.py) with the configured Snakemake executable and core count.
Job counts are taken from the marker log (measured) and cross-checked against
Snakemake's own "Finished jobid" lines.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_common import TreeRSSSampler, loadavg  # noqa: E402
from bench_config import load  # noqa: E402

CFG = load()
ROOT = CFG.root
SMK = CFG.smk
OUT = CFG.path("out_root")
WORK = CFG.path("work_root")
LOGS = OUT / "logs_smk"
#: marker logs are the job-count measurement: keep them on the same LOCAL
#: filesystem as the workdirs (concurrent appends lose lines on 9p/network
#: mounts) and archive the exact bytes under OUT_ROOT/markers afterwards.
MARKERS = WORK / "markers"
ARCHIVED_MARKERS = OUT / "markers"
NPROC = CFG.int("nproc")
REPS = CFG.int("reps")
SCALING_NS = CFG.list("scaling_ns")
CONC_N = CFG.int("conc_n")
CONC_FORKS = CFG.list("conc_forks")
CACHE_SCOPE_N = CFG.int("cache_scope_n")
SLEEP = CFG.raw("sleep")
SLEEP_F = float(SLEEP)
SNAKEFILE_DAG = ROOT / "smk_dag" / "Snakefile"
SNAKEFILE_CACHE = ROOT / "smk_cache" / "Snakefile"

for _d in (OUT, WORK, LOGS, MARKERS, ARCHIVED_MARKERS):
    _d.mkdir(parents=True, exist_ok=True)
ARTEFACTS = OUT / "artefacts"
ARTEFACTS.mkdir(parents=True, exist_ok=True)


def archive_agg(tool: str, label: str, src: Path | None, record: dict) -> None:
    """Archive a run's final agg.txt + its sha256 (cross-arm comparison artefact)."""
    if src is None or not Path(src).exists():
        record.update(agg_file=None, agg_sha256=None, agg_note=f"agg.txt not found ({src})")
        return
    dest = ARTEFACTS / f"agg_{tool}_{label}.txt"
    shutil.copy2(src, dest)
    record.update(agg_file=str(dest),
                  agg_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
                  agg_bytes=dest.stat().st_size,
                  agg_note=None)

records: list[dict] = []


def run_smk(tag, snakefile, workdir, cores, env_extra, marker, extra_args=None,
            truncate=True):
    if not SMK:
        raise RuntimeError(
            "no snakemake executable configured: set SMK= in bench.env to a "
            "snakemake binary, or put one on PATH (see setup_env.sh)")
    workdir.mkdir(parents=True, exist_ok=True)
    if truncate:
        marker.write_text("")
    env = dict(os.environ)
    env["BN_MARKER"] = str(marker)
    env.update(env_extra)
    log = LOGS / f"{tag}.log"
    cmd = [SMK, "--cores", str(cores), "-s", str(snakefile)]
    cmd += list(extra_args or [])
    la_before = loadavg()
    t0 = time.perf_counter()
    with open(log, "w") as fh:
        proc = subprocess.Popen(cmd, cwd=workdir, env=env,
                                stdout=fh, stderr=subprocess.STDOUT)
        sampler = TreeRSSSampler(proc.pid)
        sampler.start()
        rc = proc.wait()
        sampler.stop()
    wall = time.perf_counter() - t0
    la_after = loadavg()
    # archive the exact marker bytes under OUT_ROOT (see MARKERS note above)
    archived = ARCHIVED_MARKERS / marker.name
    shutil.copy2(marker, archived)
    lines = [l.split() for l in marker.read_text().splitlines() if l.strip()]
    log_text = log.read_text()
    # independent cross-check: Snakemake's own per-job "Finished jobid" lines.
    finished = re.findall(r"Finished jobid: (\d+) \(Rule: (\w+)\)", log_text)
    return {
        "tag": tag, "cmd": " ".join(cmd), "rc": rc,
        "wall_sec": round(wall, 3),
        "jobs_executed": len(lines),
        "jobs_by_proc": dict(Counter(l[0] for l in lines)),
        "jobs_from_log_all": len(finished),
        "jobs_from_log_excl_target_rule": len([f for f in finished if f[1] != "all"]),
        "executed_detail": [" ".join(l[:2]) for l in lines],
        "peak_tree_rss_mb": round(sampler.peak_kb / 1024, 1),
        "rss_samples": sampler.n_samples,
        "loadavg_before": la_before, "loadavg_after": la_after,
        "marker_log": str(archived), "log": str(log),
        "workdir": str(workdir),
    }


def step3(reps: int = None) -> None:
    for n in SCALING_NS:
        for rep in range(1, (reps or REPS) + 1):
            tag = f"smk_s3_n{n}_r{rep}"
            wd = WORK / f"smkw_{tag}"
            shutil.rmtree(wd, ignore_errors=True)
            rec = run_smk(tag, SNAKEFILE_DAG, wd, NPROC,
                          {"BN_N": str(n), "BN_SLEEP": SLEEP},
                          MARKERS / f"marker_{tag}.log")
            rec.update(step="3_scaling", n=n, forks=NPROC, sleep_per_job=SLEEP,
                       cache=False, rep=rep)
            rec["sleep_floor_sec"] = round(n * SLEEP_F / min(n, NPROC), 3)
            rec["overhead_vs_sleep_floor_sec"] = round(
                rec["wall_sec"] - rec["sleep_floor_sec"], 3)
            archive_agg("smk", tag, wd / "agg.txt", rec)
            records.append(rec)
            shutil.rmtree(wd, ignore_errors=True)
            print(f"[smk s3] {tag} wall={rec['wall_sec']} jobs={rec['jobs_executed']} "
                  f"rss={rec['peak_tree_rss_mb']}MB", flush=True)


def step4(n: int = None) -> None:
    n = n or CONC_N
    for cores in CONC_FORKS:
        tag = f"smk_s4_n{n}_c{cores}"
        wd = WORK / f"smkw_{tag}"
        shutil.rmtree(wd, ignore_errors=True)
        rec = run_smk(tag, SNAKEFILE_DAG, wd, cores,
                      {"BN_N": str(n), "BN_SLEEP": SLEEP},
                      MARKERS / f"marker_{tag}.log")
        rec.update(step="4_concurrency", n=n, forks=cores, sleep_per_job=SLEEP,
                   cache=False, rep=1)
        rec["sleep_floor_sec"] = round(n * SLEEP_F / min(n, cores), 3)
        rec["overhead_vs_sleep_floor_sec"] = round(
            rec["wall_sec"] - rec["sleep_floor_sec"], 3)
        archive_agg("smk", tag, wd / "agg.txt", rec)
        records.append(rec)
        shutil.rmtree(wd, ignore_errors=True)
        print(f"[smk s4] {tag} wall={rec['wall_sec']} jobs={rec['jobs_executed']}",
              flush=True)


def step5_scope(n: int = None) -> dict:
    """Symmetric caching / invalidation experiment on Snakemake."""
    n = n or CACHE_SCOPE_N
    wd = WORK / "smkw_s5_scope"
    indir = wd / "inputs"
    marker = MARKERS / "marker_smk_s5_scope.log"
    shutil.rmtree(wd, ignore_errors=True)
    indir.mkdir(parents=True)

    def write_inputs(version=1):
        for i in range(n):
            (indir / f"in{i}.txt").write_text(f"line{i}-v{version}\n")

    write_inputs()
    marker.write_text("")
    phases = []

    def one(label, extra=None, note="", args=None):
        off = len(marker.read_text().splitlines())
        rec = run_smk(f"smk_s5_{label}", SNAKEFILE_CACHE, wd,
                      NPROC, dict({"BN_N": str(n)}, **(extra or {})), marker,
                      extra_args=args, truncate=False)
        rec.update(step="5_caching_scope", n=n, forks=NPROC, cache=True,
                   rep=len(phases) + 1, note=note)
        after = [l.split() for l in marker.read_text().splitlines() if l.strip()]
        new = after[off:]
        rec["jobs_executed"] = len(new)
        rec["jobs_by_proc"] = dict(Counter(l[0] for l in new))
        rec["executed_detail"] = [" ".join(l[:2]) for l in new]
        archive_agg("smk", f"cache_{label}", wd / "agg.txt", rec)
        phases.append(rec)
        records.append(rec)
        print(f"[smk s5] {label} wall={rec['wall_sec']} jobs={rec['jobs_executed']} "
              f"{rec['jobs_by_proc']}", flush=True)
        return rec

    one("r1_cold", note="fresh workdir")
    one("r2_rerun", note="nothing changed")
    p = indir / f"in{max(0, n - 4)}.txt"
    p.write_text("line4-v2\n")
    one("r3_input4_changed", note=f"{p.name} content rewritten")
    one("r4_mid_script_changed", {"BN_MIDVARIANT": "B"},
        note="mid rule shell A -> B, default --rerun-triggers")
    one("r4b_mid_script_changed_mtime_trigger", {"BN_MIDVARIANT": "B"},
        note="same as r4 but --rerun-triggers mtime (traditional Snakemake)",
        args=["--rerun-triggers", "mtime"])
    one("r5_rerun", {"BN_MIDVARIANT": "B"},
        note="nothing changed (variant stays B)")
    return {"n": n, "phases": phases, "modified_input": str(p),
            "modified_input_content": p.read_text()}


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else "345"
    t_start = time.perf_counter()
    print(CFG.describe(), flush=True)
    print(f"# snakemake = {SMK}", flush=True)
    scope = None
    if "3" in only:
        step3()
    if "4" in only:
        step4()
    if "5" in only:
        scope = step5_scope()
    (OUT / "smk_records.json").write_text(json.dumps(records, indent=2))
    if "3" in only or "4" in only:
        steps34 = [r for r in records if r["step"] in ("3_scaling", "4_concurrency")]
        (OUT / "smk_records_steps34.json").write_text(json.dumps(steps34, indent=2))
    if "5" in only:
        step5 = [r for r in records if r["step"].startswith("5_")]
        (OUT / "smk_records_step5.json").write_text(json.dumps(step5, indent=2))
    if scope:
        (OUT / "smk_cache_scope.json").write_text(json.dumps(scope, indent=2))
    print(f"TOTAL_SMK_DRIVER_SEC={time.perf_counter() - t_start:.1f}", flush=True)
