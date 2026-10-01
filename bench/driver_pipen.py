#!/usr/bin/env python3
"""pipen benchmark driver: step 3 (overhead/scaling), 4 (concurrency), 5 (caching).

Every path and protocol size comes from ``bench.env`` (see ``bench_config.py``);
nothing in this file is machine specific.  No number is invented: each value in
the records JSON is either measured here or copied verbatim from a raw log.

Usage::

    driver_pipen.py [arms]      arms: any of "3", "4", "5", "all" (default)
    driver_pipen.py 5           caching arm only (cold/warm + invalidation scope)
    driver_pipen.py 34          scaling + concurrency arms

Outputs (all under ``OUT_ROOT``, see ``bench_config.py``):
    pipen_records.json            every record from this invocation
    pipen_records_steps34.json    step 3 + 4 records (written when those arms run)
    pipen_records_step5.json      step 5 records (written when arm 5 runs)
    pipen_cache_scope.json        per-phase caching detail + agg.txt content
    pipen_run_meta.json           resolved configuration of this invocation
    logs/<tag>.log                full stdout of every pipeline invocation
    markers/marker_<tag>.log      per-job start/end epochs (the job count is
                                  measured from here, never from the framework)
"""
from __future__ import annotations

import hashlib
import json
import os
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
PY = CFG.py
OUT = CFG.path("out_root")
WORK = CFG.path("work_root")
LOGS = OUT / "logs"
#: Marker logs ARE the job-count measurement (one line per job execution), so
#: they must live on the same LOCAL filesystem as the workdirs: concurrent
#: appends from many job processes lose lines on a 9p/network mount (measured on
#: this box: 29 of 42 lines on /mnt/f, 42 of 42 on ext4).  A copy is archived
#: under OUT_ROOT/markers after every run so the record stays complete.
MARKERS = WORK / "markers"
ARCHIVED_MARKERS = OUT / "markers"
NPROC = CFG.int("nproc")
REPS = CFG.int("reps")
SCALING_NS = CFG.list("scaling_ns")
CONC_N = CFG.int("conc_n")
CONC_FORKS = CFG.list("conc_forks")
CACHE_SCOPE_N = CFG.int("cache_scope_n")
CACHE_TIMING_N = CFG.int("cache_timing_n")
CACHE_TIMING_REPS = CFG.int("cache_timing_reps")
SLEEP = CFG.raw("sleep")
SLEEP_F = float(SLEEP)
RUNINFO = CFG.bool("runinfo")
#: literal written over the modified input in the invalidation phase.  The
#: archived run used this same literal; only "the content changed" matters.
MOD_NEW_CONTENT = "line3-v2"

for _d in (OUT, WORK, LOGS, MARKERS, ARCHIVED_MARKERS):
    _d.mkdir(parents=True, exist_ok=True)
ARTEFACTS = OUT / "artefacts"
ARTEFACTS.mkdir(parents=True, exist_ok=True)


def find_pipeline_export(pipeline: str) -> Path | None:
    """pipen exports an end process to <cwd>/<Pipeline>-output/<Proc>/agg.txt."""
    cands = sorted(WORK.glob(f"{pipeline}-output/**/agg.txt"))
    return cands[-1] if cands else None


def archive_agg(tool: str, label: str, src: Path | None, record: dict) -> None:
    """Archive a run's final agg.txt + its sha256.

    This is the cross-arm comparison artefact: the same DAG under pipen and
    under Snakemake must produce byte-identical agg.txt.
    """
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
#: version of pipen-runinfo visible to PY (the interpreter that runs the
#: pipelines), or None.  Recorded in every record so the JSON is self-describing.
RUNINFO_VERSION = CFG.module_version("pipen_runinfo", "pipen-runinfo") if RUNINFO else None
if RUNINFO and RUNINFO_VERSION is None:
    print("WARNING: RUNINFO=1 but pipen-runinfo is not importable by "
          f"{PY}; job.runinfo.* files will NOT be produced.  Install it with "
          f"`{PY} -m pip install pipen-runinfo` (run_all.sh does this).", flush=True)

#: RUNINFO=0 must really switch the plugin off (it would otherwise activate by
#: itself just because it is installed in PY), so the archived plugin-free
#: timing protocol stays reproducible.
PIPELINE_ENV = {} if RUNINFO else {"BENCH_PLUGINS": "-runinfo"}


def run_pipen(tag: str, env_extra: dict, record: dict) -> dict:
    """Run one pipeline invocation; return the record updated with timings."""
    marker = MARKERS / f"marker_{tag}.log"
    marker.write_text("")
    env = dict(os.environ)
    env["BENCH_MARKER"] = str(marker)
    env.update(env_extra)
    env.update(PIPELINE_ENV)
    log = LOGS / f"{tag}.log"
    la_before = loadavg()
    t0 = time.perf_counter()
    with open(log, "w") as fh:
        proc = subprocess.Popen(
            [str(PY), str(ROOT / record["_script"])],
            env=env, stdout=fh, stderr=subprocess.STDOUT,
            # cwd = WORK_ROOT so pipen's exported <Pipeline>-output/ lands there
            # instead of in whatever directory the driver happened to be started from
            cwd=str(WORK),
        )
        sampler = TreeRSSSampler(proc.pid)
        sampler.start()
        rc = proc.wait()
        sampler.stop()
    wall = time.perf_counter() - t0
    la_after = loadavg()

    # count on the local copy, then archive the exact bytes under OUT_ROOT
    archived = ARCHIVED_MARKERS / marker.name
    shutil.copy2(marker, archived)
    run_sec = None
    for line in log.read_text().splitlines():
        if line.startswith("PIPELINE_RUN_SEC="):
            run_sec = float(line.split("=", 1)[1])
    lines = [l.split() for l in marker.read_text().splitlines() if l.strip()]
    by_proc = Counter(l[0] for l in lines)
    log_text = log.read_text()
    cached_lines = [l for l in log_text.splitlines() if "Cached jobs" in l]
    record.update(
        wall_sec=round(wall, 3),
        pipeline_run_sec=None if run_sec is None else round(run_sec, 3),
        rc=rc,
        rc_ok=(rc == 0),
        # pipeline_ok keeps its archived meaning: rc==0 AND the script printed
        # PIPELINE_RUN_SEC (bench_cache_dag.py does not print it, so cache-DAG
        # runs are rc_ok=true / pipeline_ok=false - use rc_ok, not pipeline_ok).
        pipeline_ok=(rc == 0 and run_sec is not None),
        cached_jobs_log_lines=cached_lines,
        jobs_executed=len(lines),
        jobs_by_proc=dict(by_proc),
        peak_tree_rss_mb=round(sampler.peak_kb / 1024, 1),
        rss_samples=sampler.n_samples,
        loadavg_before=la_before,
        loadavg_after=la_after,
        runinfo_version=RUNINFO_VERSION,
        runinfo_enabled=bool(RUNINFO and RUNINFO_VERSION),
        marker_log=str(archived),
        marker_log_local=str(marker),
        log=str(log),
    )
    return record


# --------------------------------------------------------------------------- #
# STEP 3: overhead / scaling, cache disabled, fresh workdir per rep
# --------------------------------------------------------------------------- #
def step3(reps: int = None) -> None:
    for n in SCALING_NS:
        for rep in range(1, (reps or REPS) + 1):
            tag = f"s3_n{n}_r{rep}"
            wd = WORK / f"wd_{tag}"
            shutil.rmtree(wd, ignore_errors=True)
            rec = {
                "step": "3_scaling", "tag": tag, "n": n, "forks": NPROC,
                "sleep_per_job": SLEEP, "cache": False, "rep": rep,
                "_script": "bench_pipen_dag.py",
            }
            run_pipen(tag, {
                "BENCH_N": str(n), "BENCH_FORKS": str(NPROC),
                "BENCH_SLEEP": SLEEP, "BENCH_CACHE": "0",
                "BENCH_WORKDIR": str(wd),
            }, rec)
            rec["sleep_floor_sec"] = round(n * SLEEP_F / min(n, NPROC), 3)
            rec["overhead_vs_sleep_floor_sec"] = round(
                (rec["pipeline_run_sec"] or 0) - rec["sleep_floor_sec"], 3)
            rec["overhead_per_job_sec"] = round(
                rec["overhead_vs_sleep_floor_sec"] / n, 4)
            archive_agg("pipen", tag, find_pipeline_export("DagPipeline"), rec)
            shutil.rmtree(wd, ignore_errors=True)
            records.append(rec)
            print(f"[s3] {tag} wall={rec['wall_sec']} run={rec['pipeline_run_sec']} "
                  f"jobs={rec['jobs_executed']} rss={rec['peak_tree_rss_mb']}MB", flush=True)


# --------------------------------------------------------------------------- #
# STEP 4: concurrency scaling
# --------------------------------------------------------------------------- #
def step4(n: int = None, reps: int = 1) -> None:
    n = n or CONC_N
    for forks in CONC_FORKS:
        for rep in range(1, reps + 1):
            tag = f"s4_n{n}_f{forks}_r{rep}"
            wd = WORK / f"wd_{tag}"
            shutil.rmtree(wd, ignore_errors=True)
            rec = {
                "step": "4_concurrency", "tag": tag, "n": n, "forks": forks,
                "sleep_per_job": SLEEP, "cache": False, "rep": rep,
                "_script": "bench_pipen_dag.py",
            }
            run_pipen(tag, {
                "BENCH_N": str(n), "BENCH_FORKS": str(forks),
                "BENCH_SLEEP": SLEEP, "BENCH_CACHE": "0",
                "BENCH_WORKDIR": str(wd),
            }, rec)
            rec["sleep_floor_sec"] = round(n * SLEEP_F / min(n, forks), 3)
            rec["overhead_vs_sleep_floor_sec"] = round(
                (rec["pipeline_run_sec"] or 0) - rec["sleep_floor_sec"], 3)
            archive_agg("pipen", tag, find_pipeline_export("DagPipeline"), rec)
            shutil.rmtree(wd, ignore_errors=True)
            records.append(rec)
            print(f"[s4] {tag} wall={rec['wall_sec']} run={rec['pipeline_run_sec']} "
                  f"jobs={rec['jobs_executed']}", flush=True)


# --------------------------------------------------------------------------- #
# STEP 5: caching evidence
# --------------------------------------------------------------------------- #
def make_inputs(indir: Path, n: int, version: int = 1) -> None:
    shutil.rmtree(indir, ignore_errors=True)
    indir.mkdir(parents=True)
    for i in range(n):
        (indir / f"in{i}.txt").write_text(f"line{i}-v{version}\n")


def find_agg_outputs(wd: Path) -> list[Path]:
    """All agg.txt candidates: the exported copy plus the per-job workdir copy.

    pipen exports an end-process output to ``<cwd>/<PipelineName>-output/<Proc>/``,
    so a later run of a same-named pipeline in the same cwd overwrites it; the
    per-job workdir copy is the durable one.
    """
    cands = set(wd.rglob("agg.txt"))
    for base in (Path.cwd(), OUT, WORK):
        cands.update(base.glob("CachePipeline-output/**/agg.txt"))
    return sorted(cands)


def step5_scope(n: int = None) -> dict:
    """Caching + invalidation-scope experiment on a fresh workdir."""
    n = n or CACHE_SCOPE_N
    indir = WORK / "cache_inputs_small"
    wd = WORK / "wd_s5_scope"
    marker = MARKERS / "marker_s5_scope.log"
    make_inputs(indir, n)
    shutil.rmtree(wd, ignore_errors=True)
    marker.write_text("")
    phases = []

    def one(label: str, extra: dict | None = None, note: str = "") -> dict:
        env = {
            "BN_N": str(n), "BN_INDIR": str(indir), "BN_WORKDIR": str(wd),
            "BN_MARKER": str(marker), "BN_MIDVARIANT": "A", "BN_SIDEVARIANT": "A",
            "BN_FORKS": str(NPROC),
        }
        env.update(extra or {})
        off = len(marker.read_text().splitlines())
        rec = {"step": "5_caching_scope", "tag": f"s5_{label}", "n": n,
               "forks": NPROC, "cache": True, "rep": len(phases) + 1,
               "_script": "bench_cache_dag.py", "note": note}
        run_pipen(f"s5_{label}", env, rec)
        # adjust the per-run counts to only this phase
        after = [l.split() for l in marker.read_text().splitlines() if l.strip()]
        new = after[off:]
        rec["jobs_executed"] = len(new)
        rec["jobs_by_proc"] = dict(Counter(l[0] for l in new))
        rec["executed_detail"] = [" ".join(l[:2]) for l in new]
        phases.append(rec)
        records.append(rec)
        print(f"[s5] {label} wall={rec['wall_sec']} jobs={rec['jobs_executed']} "
              f"{rec['jobs_by_proc']}", flush=True)
        return rec

    one("r1_cold", note="fresh workdir, cache on: everything must execute")
    one("r2_rerun", note="immediate re-run, nothing changed")
    # (c) modify one input file: index n-4 in the archived run (in4.txt for n=8)
    p = indir / f"in{max(0, n - 4)}.txt"
    p.write_text(MOD_NEW_CONTENT + "\n")
    one("r3_input3_changed", note=f"content of {p.name} rewritten")
    # (d) change the script of the Mid process only
    one("r4_mid_script_changed", extra={"BN_MIDVARIANT": "B"},
        note="Mid process script variant A -> B")
    one("r5_rerun", extra={"BN_MIDVARIANT": "B"},
        note="re-run immediately after r4, nothing else changed (variant stays B)")

    cands = find_agg_outputs(wd)
    if not cands:
        raise FileNotFoundError(
            f"agg.txt not found under {wd}, {OUT}/CachePipeline-output or "
            f"{Path.cwd()}/CachePipeline-output")
    agg_out = cands[0]
    agg_meta: dict = {}
    archive_agg("pipen", f"cache_n{n}", agg_out, agg_meta)
    return {
        "n": n,
        "phases": phases,
        "agg_output_file": str(agg_out),
        "agg_output_content": agg_out.read_text(),
        "agg_archive": agg_meta,
        "agg_output_candidates": [str(c) for c in cands],
        "modified_input": str(p),
        "modified_input_content": p.read_text(),
        "modified_new_content": MOD_NEW_CONTENT,
    }


def step5_timing(n: int = None, reps: int = None) -> None:
    """Cold vs warm timings at a size where job execution actually costs time."""
    n = n or CACHE_TIMING_N
    indir = WORK / "cache_inputs_big"
    make_inputs(indir, n)
    for rep in range(1, (reps or CACHE_TIMING_REPS) + 1):
        wd = WORK / f"wd_s5_time_r{rep}"
        shutil.rmtree(wd, ignore_errors=True)
        marker = MARKERS / f"marker_s5_time_r{rep}.log"
        marker.write_text("")
        for label in ("cold", "warm1", "warm2"):
            off = len(marker.read_text().splitlines())
            rec = {"step": "5_caching_timing", "tag": f"s5_time_n{n}_{label}_r{rep}",
                   "n": n, "forks": NPROC, "cache": True, "rep": rep,
                   "_script": "bench_cache_dag.py", "note": label}
            run_pipen(f"s5_time_n{n}_{label}_r{rep}", {
                "BN_N": str(n), "BN_INDIR": str(indir), "BN_WORKDIR": str(wd),
                "BN_MARKER": str(marker), "BN_MIDVARIANT": "A", "BN_SIDEVARIANT": "A",
                "BN_FORKS": str(NPROC),
            }, rec)
            after = [l.split() for l in marker.read_text().splitlines() if l.strip()]
            new = after[off:]
            rec["jobs_executed"] = len(new)
            rec["jobs_by_proc"] = dict(Counter(l[0] for l in new))
            if label == "cold":
                archive_agg("pipen", f"s5time_cold_n{n}_r{rep}",
                            find_pipeline_export("CachePipeline"), rec)
            records.append(rec)
            print(f"[s5t] {label} wall={rec['wall_sec']} run={rec['pipeline_run_sec']} "
                  f"jobs={rec['jobs_executed']}", flush=True)
        shutil.rmtree(wd, ignore_errors=True)


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    t_start = time.perf_counter()
    print(CFG.describe(), flush=True)
    scope = None
    if "3" in only:
        step3()
    if "4" in only:
        step4()
    if "5" in only:
        scope = step5_scope()
        step5_timing()
    (OUT / "pipen_records.json").write_text(json.dumps(records, indent=2))
    if "3" in only or "4" in only:
        steps34 = [r for r in records if r["step"] in ("3_scaling", "4_concurrency")]
        (OUT / "pipen_records_steps34.json").write_text(json.dumps(steps34, indent=2))
    if "5" in only:
        step5 = [r for r in records if r["step"].startswith("5_")]
        (OUT / "pipen_records_step5.json").write_text(json.dumps(step5, indent=2))
    if scope:
        (OUT / "pipen_cache_scope.json").write_text(json.dumps(scope, indent=2))
    (OUT / "pipen_run_meta.json").write_text(json.dumps({
        "config": CFG.as_dict(),
        "runinfo_requested": RUNINFO,
        "pipen_runinfo_version": RUNINFO_VERSION,
        "arms": only,
        "py": str(PY),
        "pipen_version": CFG.module_version("pipen"),
        "interpreter_version": sys.version,
    }, indent=2))
    print(f"TOTAL_DRIVER_SEC={time.perf_counter() - t_start:.1f}", flush=True)
