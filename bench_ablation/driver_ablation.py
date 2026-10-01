#!/usr/bin/env python3
"""Ablation driver for the pipen/xqute local-scheduler overhead claim.

Runs INSIDE WSL (Ubuntu-24.04) with ~/bench/.venv/bin/python.  All heavy I/O
(workdirs, marker logs) happens on the ext4 WSL home; only the finished JSON
and stdout logs are copied to /mnt/f at the end.

Sub-commands
  verify   one short run per arm (N=8) with the sleep census enabled: proves
           which await sites fire and with what argument, plus the effective
           constant values and a source-tree integrity check.
  calib    one rep per (arm, N) to size the timed matrix.
  time     the timed matrix, `--reps` reps each (default 3).
  copy     copy out/ to the F: workspace raw/ directory.

Every number written to JSON comes from a parsed raw log / marker file.
"""
import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HOME = Path.home()
BENCH = HOME / "bench_abl"
OUT = BENCH / "out"
LOGS = OUT / "logs"
WD = BENCH / "wd"
VPY = HOME / "bench" / ".venv" / "bin" / "python"
DAG = Path("/mnt/f/E/hermes-workspace/pipen/bench_ablation/abl_dag.py")
DEST = Path("/mnt/f/E/hermes-workspace/pipen/bench_ablation/raw")

NPROC = os.cpu_count()
SHARD_SLEEP = 0.05
FORKS = 32

# arm -> N values that arm is timed at
ARM_N = {
    "A": [100, 500],
    "B": [100, 500],
    "C_pf": [100],
    "C_poll": [100],
    "C_kf": [100],
    "C_batch": [100],
    "C_pf_poll": [100],
    "F": [100],
    "E_all": [100],
}
ARM_LABEL = {
    "A": "baseline (all xqute constants at shipped defaults)",
    "B": "SUBMIT_JOB_SLEEP 0.1 -> 0.001",
    "C_pf": "SLEEP_INTERVAL_PRODUCER_MAX_FORKS 1.0 -> 0.001 (alone)",
    "C_poll": "SLEEP_INTERVAL_POLLING_JOBS 1.0 -> 0.001 (alone)",
    "C_kf": "SLEEP_INTERVAL_KEEP_FEEDING 0.1 -> 0.001 (alone)",
    "C_batch": "DEFAULT_SUBMISSION_BATCH 8 -> 64 (alone)",
    "C_pf_poll": "SLEEP_INTERVAL_PRODUCER_MAX_FORKS + SLEEP_INTERVAL_POLLING_JOBS -> 0.001 (alone, no other change)",
    "F": "the 2x `sleep 1` in the local job wrapper removed (alone)",
    "E_all": "all of the above relaxed together",
}

LOGS.mkdir(parents=True, exist_ok=True)


def loadavg():
    return open("/proc/loadavg").read().split()[:3]


def tree_sha256(root: Path) -> dict:
    """sha256 of every .py under root -> integrity evidence (nothing modified)."""
    out = {}
    for p in sorted(root.rglob("*.py")):
        if p.is_file():
            out[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def sha_of_tree(root: Path) -> str:
    h = hashlib.sha256()
    for k, v in sorted(tree_sha256(root).items()):
        h.update((k + v).encode())
    return h.hexdigest()


def run_one(arm, n, rep, census=False, tag=None):
    tag = tag or f"{arm}_n{n}_r{rep}"
    wd = WD / tag
    shutil.rmtree(wd, ignore_errors=True)
    wd.mkdir(parents=True)
    marker = OUT / "markers" / f"marker_{tag}.log"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("")
    log = LOGS / f"{tag}.log"
    env = dict(os.environ)
    env.update({
        "ABL_ARM": arm, "ABL_N": str(n), "ABL_FORKS": str(FORKS),
        "ABL_SLEEP": str(SHARD_SLEEP), "ABL_WORKDIR": str(wd),
        "ABL_MARKER": str(marker),
        "ABL_CENSUS": "1" if census else "0",
    })
    la_before = loadavg()
    t0 = time.perf_counter()
    with open(log, "w") as fh:
        proc = subprocess.Popen([str(VPY), str(DAG)], env=env, stdout=fh,
                                stderr=subprocess.STDOUT, cwd=str(wd))
        rc = proc.wait()
    wall = time.perf_counter() - t0
    la_after = loadavg()
    text = log.read_text()

    def grab(prefix):
        for line in text.splitlines():
            if line.startswith(prefix):
                return line[len(prefix):]
        return None

    eff = json.loads(grab("ABL_EFFECTIVE=")) if grab("ABL_EFFECTIVE=") else None
    rsec = grab("PIPELINE_RUN_SEC=")
    agg = json.loads(grab("ABL_AGG=")) if grab("ABL_AGG=") else None
    occ = json.loads(grab("ABL_OCCUPANCY=")) if grab("ABL_OCCUPANCY=") else None
    census_raw = grab("ABL_SLEEP_CENSUS=")
    census = json.loads(census_raw) if census_raw else None
    status_raw = grab("ABL_STATUS=")
    status = json.loads(status_raw) if status_raw else None

    # ---- correctness of the produced output, independent of the framework:
    # every shard script writes exactly its own index -> agg.txt must be 0..N-1
    expected = "".join(f"{i}\n" for i in range(n))
    agg_text = None
    for p in sorted(Path(wd).rglob("agg.txt")):
        agg_text = p.read_text()
        break
    if agg_text is not None:
        agg_correct = (agg_text == expected)
    else:
        # no agg file at all (e.g. the aggregation stage never ran) -> not correct
        agg_correct = False

    # ---- marker analysis (per-job execution timestamps, framework-independent)
    starts, ends, spans = {}, {}, {}
    by_proc = Counter()
    for line in marker.read_text().splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        what, idx, ts = parts[0], parts[1], float(parts[2])
        proc_name = what.rsplit("_", 1)[0]
        by_proc[proc_name] += 1
        if what.endswith("_start"):
            starts[(proc_name, idx)] = ts
        elif what.endswith("_end"):
            ends[(proc_name, idx)] = ts
    for key, s in starts.items():
        if key in ends:
            spans[key] = ends[key] - s
    shard_starts = sorted(t for k, t in starts.items() if k[0] == "shard")
    shard_spans = [v for k, v in spans.items() if k[0] == "shard"]
    agg_keys = [k for k in spans if k[0] == "agg"]
    shard_span = (shard_starts[-1] - shard_starts[0]) if len(shard_starts) > 1 else 0.0

    # marker-derived concurrency sweep (independent of the framework)
    events = []
    for k, t in starts.items():
        events.append((t, +1))
    for k, t in ends.items():
        events.append((t, -1))
    events.sort()
    cur = peak = 0
    area = 0.0
    prev = None
    for t, d in events:
        if prev is not None:
            area += cur * (t - prev)
        cur += d
        peak = max(peak, cur)
        prev = t
    total_time = (events[-1][0] - events[0][0]) if events else 0.0

    rec = {
        "tag": tag, "arm": arm, "arm_label": ARM_LABEL[arm], "n": n, "rep": rep,
        "forks": FORKS, "shard_sleep_sec": SHARD_SLEEP, "cache": False,
        "wall_sec": round(wall, 3), "rc": rc,
        "pipeline_run_sec": None if rsec is None else round(float(rsec), 3),
        "sleep_floor_sec": round(n * SHARD_SLEEP / min(n, FORKS), 4),
        "jobs_executed_total": len(starts),
        "jobs_by_proc_starts": dict(by_proc),
        "shard_jobs_started": len(shard_starts),
        "agg_jobs": len(agg_keys),
        "unmatched_starts": len([k for k in starts if k not in ends]),
        "job_start_span_sec": round(shard_span, 3),
        "job_start_rate_per_sec_median_of_start_gaps": None,
        "job_start_rate_per_sec_span": (round((len(shard_starts) - 1) / shard_span, 2)
                                        if shard_span > 0 else None),
        "end_to_end_rate_per_sec": (round(len(shard_starts) / total_time, 2)
                                    if total_time > 0 else None),
        "median_shard_job_duration_sec": (round(statistics.median(shard_spans), 4)
                                          if shard_spans else None),
        "peak_concurrent_jobs_from_markers": peak,
        "mean_concurrent_jobs_from_markers": (round(area / total_time, 3)
                                              if total_time > 0 else None),
        "occupancy_sampler": occ,
        "effective": eff,
        "sleep_census": census,
        "job_status_census": status,
        "correctness": {
            "agg_file_found": agg_text is not None,
            "agg_content_equals_expected_0_to_N_minus_1": agg_correct,
            "n_jobs_marked_failed_before_running": (
                None if status is None
                else status["n_jobs_marked_failed_before_running"]),
            "job_status_histogram": None if status is None else status["job_status_histogram"],
            "all_jobs_finished": (
                None if status is None
                else status["job_status_histogram"] == {"6": n + 1}),
        },
        "agg_outputs": agg,
        "loadavg_before": la_before, "loadavg_after": la_after,
        "marker_log": str(marker), "log": str(log), "workdir": str(wd),
    }
    # per-job overhead: wall-based (comparable with bench/RESULTS.md) and
    # in-process-based (excludes interpreter + import cost)
    rec["overhead_wall_sec"] = round(wall - rec["sleep_floor_sec"], 3)
    rec["overhead_wall_per_job_sec"] = round(rec["overhead_wall_sec"] / n, 4)
    if rec["pipeline_run_sec"] is not None:
        rec["overhead_run_sec"] = round(rec["pipeline_run_sec"] - rec["sleep_floor_sec"], 3)
        rec["overhead_run_per_job_sec"] = round(rec["overhead_run_sec"] / n, 4)
    else:
        rec["overhead_run_sec"] = rec["overhead_run_per_job_sec"] = None
    return rec


def flag(tag, rec):
    print(f"[{tag}] wall={rec['wall_sec']} run={rec['pipeline_run_sec']} rc={rec['rc']} "
          f"shards={rec['shard_jobs_started']}/{rec['n']} agg={rec['agg_jobs']} "
          f"ovh/job={rec['overhead_wall_per_job_sec']} "
          f"rate={rec['job_start_rate_per_sec_span']}/s peak={rec['peak_concurrent_jobs_from_markers']} "
          f"ok={rec['correctness']['agg_content_equals_expected_0_to_N_minus_1']}"
          f"/fin={rec['correctness']['all_jobs_finished']}"
          f"/falsefail={rec['correctness']['n_jobs_marked_failed_before_running']}",
          flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["verify", "calib", "time", "copy"])
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--arms", default="")
    ap.add_argument("--n", default="", help="comma list of N to override ARM_N")
    args = ap.parse_args()
    arms = [a for a in args.arms.split(",") if a] or list(ARM_N)
    if args.n:
        for a in arms:
            ARM_N[a] = [int(x) for x in args.n.split(",") if x]
    t_start = time.perf_counter()

    if args.mode == "copy":
        DEST.mkdir(parents=True, exist_ok=True)
        for sub in ("logs", "markers"):
            src = OUT / sub
            if src.exists():
                shutil.copytree(src, DEST / sub, dirs_exist_ok=True)
        for f in OUT.glob("*.json"):
            shutil.copy2(f, DEST / f.name)
        print(f"copied {OUT} -> {DEST}")
        return

    before = {"pipen": sha_of_tree(HOME / "github/pipen/pipen"),
              "xqute": sha_of_tree(HOME / "bench/.venv/lib/python3.12/site-packages/xqute")}

    if args.mode == "verify":
        recs = []
        for arm in arms:
            rec = run_one(arm, 8, 1, census=True, tag=f"verify_{arm}")
            flag(f"verify_{arm}", rec)
            recs.append(rec)
        after = {"pipen": sha_of_tree(HOME / "github/pipen/pipen"),
                 "xqute": sha_of_tree(HOME / "bench/.venv/lib/python3.12/site-packages/xqute")}
        payload = {"mode": "verify", "source_tree_sha256_before": before,
                   "source_tree_sha256_after": after,
                   "source_unchanged": before == after, "records": recs}
        (OUT / "verify_records.json").write_text(json.dumps(payload, indent=2))
        print("VERIFY source_unchanged =", before == after)
        print("VERIFY total_sec =", round(time.perf_counter() - t_start, 1))
        return

    if args.mode == "calib":
        recs = []
        for arm in arms:
            for n in ARM_N[arm]:
                rec = run_one(arm, n, 1, tag=f"calib_{arm}_n{n}")
                flag(f"calib_{arm}_n{n}", rec)
                recs.append(rec)
        (OUT / "calib_records.json").write_text(json.dumps(recs, indent=2))
        print("CALIB total_sec =", round(time.perf_counter() - t_start, 1))
        return

    # ---- timed matrix
    recs = []
    for arm in arms:
        for n in ARM_N[arm]:
            for rep in range(1, args.reps + 1):
                rec = run_one(arm, n, rep, tag=f"{arm}_n{n}_r{rep}")
                flag(f"{arm}_n{n}_r{rep}", rec)
                recs.append(rec)
    after = {"pipen": sha_of_tree(HOME / "github/pipen/pipen"),
             "xqute": sha_of_tree(HOME / "bench/.venv/lib/python3.12/site-packages/xqute")}
    payload = {"mode": "time", "reps": args.reps, "arms": arms,
               "source_tree_sha256_before": before,
               "source_tree_sha256_after": after,
               "source_unchanged": before == after,
               "driver_total_sec": round(time.perf_counter() - t_start, 1),
               "records": recs}
    (OUT / f"time_records_{'-'.join(arms)}.json").write_text(json.dumps(payload, indent=2))
    print("TIME source_unchanged =", before == after,
          "| driver_total_sec =", payload["driver_total_sec"])


if __name__ == "__main__":
    main()
