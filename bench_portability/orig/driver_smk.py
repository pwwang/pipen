#!/usr/bin/env python3
"""Snakemake counterpart of driver_pipen.py: same DAGs, same metrics."""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/mnt/f/E/hermes-workspace/pipen/bench")
from bench_common import TreeRSSSampler, loadavg  # noqa: E402

HOME = Path.home()
BENCH = HOME / "bench"
OUT = BENCH / "out"
LOGS = OUT / "logs_smk"
SMK = BENCH / "smk" / "bin" / "snakemake"
SMKDIR = Path("/mnt/f/E/hermes-workspace/pipen/bench")
NPROC = os.cpu_count()
SLEEP = "0.05"
LOGS.mkdir(parents=True, exist_ok=True)
records = []


def run_smk(tag, snakefile, workdir, cores, env_extra, marker, extra_args=None,
            truncate=True):
    workdir.mkdir(parents=True, exist_ok=True)
    if truncate:
        marker.write_text("")
    env = dict(os.environ)
    env["BN_MARKER"] = str(marker)
    env.update(env_extra)
    log = LOGS / f"{tag}.log"
    cmd = [str(SMK), "--cores", str(cores), "-s", str(snakefile)]
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
        "marker_log": str(marker), "log": str(log),
        "workdir": str(workdir),
    }


def step3(reps=3):
    for n in (1, 10, 100, 500):
        for rep in range(1, reps + 1):
            tag = f"smk_s3_n{n}_r{rep}"
            wd = BENCH / f"smkw_{tag}"
            shutil.rmtree(wd, ignore_errors=True)
            rec = run_smk(tag, SMKDIR / "smk_dag" / "Snakefile", wd, NPROC,
                          {"BN_N": str(n), "BN_SLEEP": SLEEP},
                          OUT / f"marker_{tag}.log")
            rec.update(step="3_scaling", n=n, forks=NPROC, sleep_per_job=SLEEP,
                       cache=False, rep=rep)
            rec["sleep_floor_sec"] = round(n * 0.05 / min(n, NPROC), 3)
            rec["overhead_vs_sleep_floor_sec"] = round(
                rec["wall_sec"] - rec["sleep_floor_sec"], 3)
            records.append(rec)
            shutil.rmtree(wd, ignore_errors=True)
            print(f"[smk s3] {tag} wall={rec['wall_sec']} jobs={rec['jobs_executed']} "
                  f"rss={rec['peak_tree_rss_mb']}MB", flush=True)


def step4(n=20):
    for cores in (1, 2, 4, NPROC):
        tag = f"smk_s4_n{n}_c{cores}"
        wd = BENCH / f"smkw_{tag}"
        shutil.rmtree(wd, ignore_errors=True)
        rec = run_smk(tag, SMKDIR / "smk_dag" / "Snakefile", wd, cores,
                      {"BN_N": str(n), "BN_SLEEP": SLEEP},
                      OUT / f"marker_{tag}.log")
        rec.update(step="4_concurrency", n=n, forks=cores, sleep_per_job=SLEEP,
                   cache=False, rep=1)
        rec["sleep_floor_sec"] = round(n * 0.05 / min(n, cores), 3)
        rec["overhead_vs_sleep_floor_sec"] = round(
            rec["wall_sec"] - rec["sleep_floor_sec"], 3)
        records.append(rec)
        shutil.rmtree(wd, ignore_errors=True)
        print(f"[smk s4] {tag} wall={rec['wall_sec']} jobs={rec['jobs_executed']}",
              flush=True)


def step5_scope(n=8):
    """Symmetric caching / invalidation experiment on Snakemake."""
    global records
    wd = BENCH / "smkw_s5_scope"
    indir = wd / "inputs"
    marker = OUT / "marker_smk_s5_scope.log"
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
        rec = run_smk(f"smk_s5_{label}", SMKDIR / "smk_cache" / "Snakefile", wd,
                      NPROC, dict({"BN_N": str(n)}, **(extra or {})), marker,
                      extra_args=args, truncate=False)
        rec.update(step="5_caching_scope", n=n, forks=NPROC, cache=True,
                   rep=len(phases) + 1, note=note)
        after = [l.split() for l in marker.read_text().splitlines() if l.strip()]
        new = after[off:]
        rec["jobs_executed"] = len(new)
        rec["jobs_by_proc"] = dict(Counter(l[0] for l in new))
        rec["executed_detail"] = [" ".join(l[:2]) for l in new]
        phases.append(rec)
        records.append(rec)
        print(f"[smk s5] {label} wall={rec['wall_sec']} jobs={rec['jobs_executed']} "
              f"{rec['jobs_by_proc']}", flush=True)
        return rec

    one("r1_cold", note="fresh workdir")
    one("r2_rerun", note="nothing changed")
    p = indir / f"in{n - 4}.txt"
    p.write_text("line4-v2\n")
    one("r3_input4_changed", note=f"{p.name} content rewritten")
    one("r4_mid_script_changed", {"BN_MIDVARIANT": "B"},
        note="mid rule shell A -> B, default --rerun-triggers")
    one("r4b_mid_script_changed_mtime_trigger", {"BN_MIDVARIANT": "B"},
        note="same as r4 but --rerun-triggers mtime (traditional Snakemake)",
        args=["--rerun-triggers", "mtime"])
    one("r5_rerun", {"BN_MIDVARIANT": "B"},
        note="nothing changed (variant stays B)")
    return {"phases": phases, "modified_input": str(p),
            "modified_input_content": p.read_text()}


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else "345"
    t_start = time.perf_counter()
    scope = None
    if "3" in only:
        step3()
    if "4" in only:
        step4()
    if "5" in only:
        scope = step5_scope()
    (OUT / "smk_records.json").write_text(json.dumps(records, indent=2))
    if scope:
        (OUT / "smk_cache_scope.json").write_text(json.dumps(scope, indent=2))
    print(f"TOTAL_SMK_DRIVER_SEC={time.perf_counter() - t_start:.1f}", flush=True)
