#!/usr/bin/env python3
"""pipen benchmark driver: steps 3 (overhead/scaling), 4 (concurrency), 5 (caching).

Runs inside WSL. Writes JSON + raw logs under ~/bench/out/. No number is invented:
every value is either measured here or copied verbatim from a raw log.
"""
import json
import os
import shutil
import statistics
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path

HOME = Path.home()
BENCH = HOME / "bench"
OUT = BENCH / "out"
LOGS = OUT / "logs"
VPY = BENCH / ".venv" / "bin" / "python"
SCRIPT = Path("/mnt/f/E/hermes-workspace/pipen/bench")
NPROC = os.cpu_count()
SLEEP = "0.05"

LOGS.mkdir(parents=True, exist_ok=True)
records = []


# --------------------------------------------------------------------------- #
# peak RSS of the whole process tree, sampled from /proc
# --------------------------------------------------------------------------- #
class TreeRSSSampler(threading.Thread):
    PAGE = 4096

    def __init__(self, pid, interval=0.05):
        super().__init__(daemon=True)
        self.root = pid
        self.interval = interval
        self.peak_kb = 0
        self.n_samples = 0
        self._halt = threading.Event()

    @staticmethod
    def _snapshot():
        ppid, rss = {}, {}
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                with open(f"/proc/{entry}/stat", "rb") as fh:
                    data = fh.read()
                rp = data.rfind(b")")
                fields = data[rp + 2:].split()
                ppid[int(entry)] = int(fields[1])
                rss[int(entry)] = int(fields[21]) * 4096 // 1024
            except Exception:
                continue
        return ppid, rss

    def run(self):
        while not self._halt.is_set():
            try:
                ppid, rss = self._snapshot()
                children = {}
                for p, pp in ppid.items():
                    children.setdefault(pp, []).append(p)
                stack, seen, total = [self.root], set(), 0
                while stack:
                    p = stack.pop()
                    if p in seen:
                        continue
                    seen.add(p)
                    total += rss.get(p, 0)
                    stack.extend(children.get(p, ()))
                self.peak_kb = max(self.peak_kb, total)
                self.n_samples += 1
            except Exception:
                pass
            time.sleep(self.interval)

    def stop(self):
        self._halt.set()
        self.join(timeout=5)


def loadavg():
    return open("/proc/loadavg").read().split()[:3]


def run_pipen(tag, env_extra, record):
    """Run one pipeline invocation; return updated record with timings."""
    marker = OUT / f"marker_{tag}.log"
    marker.write_text("")
    env = dict(os.environ)
    env["BENCH_MARKER"] = str(marker)
    env.update(env_extra)
    log = LOGS / f"{tag}.log"
    la_before = loadavg()
    t0 = time.perf_counter()
    with open(log, "w") as fh:
        proc = subprocess.Popen(
            [str(VPY), str(SCRIPT / record["_script"])],
            env=env, stdout=fh, stderr=subprocess.STDOUT,
        )
        sampler = TreeRSSSampler(proc.pid)
        sampler.start()
        rc = proc.wait()
        sampler.stop()
    wall = time.perf_counter() - t0
    la_after = loadavg()

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
        pipeline_ok=(rc == 0 and run_sec is not None),
        cached_jobs_log_lines=cached_lines,
        jobs_executed=len(lines),
        jobs_by_proc=dict(by_proc),
        peak_tree_rss_mb=round(sampler.peak_kb / 1024, 1),
        rss_samples=sampler.n_samples,
        loadavg_before=la_before,
        loadavg_after=la_after,
        marker_log=str(marker),
        log=str(log),
    )
    return record


def stats(values):
    v = sorted(values)
    return {
        "n": len(v),
        "min": round(v[0], 3),
        "median": round(statistics.median(v), 3),
        "max": round(v[-1], 3),
        "mean": round(sum(v) / len(v), 3),
        "all": [round(x, 3) for x in v],
    }


# --------------------------------------------------------------------------- #
# STEP 3: overhead / scaling, cache disabled, fresh workdir per rep
# --------------------------------------------------------------------------- #
def step3(reps=3):
    global records
    for n in (1, 10, 100, 500):
        for rep in range(1, reps + 1):
            tag = f"s3_n{n}_r{rep}"
            wd = BENCH / f"wd_{tag}"
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
            rec["sleep_floor_sec"] = round(n * 0.05 / min(n, NPROC), 3)
            rec["overhead_vs_sleep_floor_sec"] = round(
                (rec["pipeline_run_sec"] or 0) - rec["sleep_floor_sec"], 3)
            rec["overhead_per_job_sec"] = round(
                rec["overhead_vs_sleep_floor_sec"] / n, 4)
            shutil.rmtree(wd, ignore_errors=True)
            records.append(rec)
            print(f"[s3] {tag} wall={rec['wall_sec']} run={rec['pipeline_run_sec']} "
                  f"jobs={rec['jobs_executed']} rss={rec['peak_tree_rss_mb']}MB", flush=True)


# --------------------------------------------------------------------------- #
# STEP 4: concurrency scaling
# --------------------------------------------------------------------------- #
def step4(n=20, reps=1):
    global records
    for forks in (1, 2, 4, NPROC):
        for rep in range(1, reps + 1):
            tag = f"s4_n{n}_f{forks}_r{rep}"
            wd = BENCH / f"wd_{tag}"
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
            rec["sleep_floor_sec"] = round(n * 0.05 / min(n, forks), 3)
            rec["overhead_vs_sleep_floor_sec"] = round(
                (rec["pipeline_run_sec"] or 0) - rec["sleep_floor_sec"], 3)
            shutil.rmtree(wd, ignore_errors=True)
            records.append(rec)
            print(f"[s4] {tag} wall={rec['wall_sec']} run={rec['pipeline_run_sec']} "
                  f"jobs={rec['jobs_executed']}", flush=True)


# --------------------------------------------------------------------------- #
# STEP 5: caching evidence
# --------------------------------------------------------------------------- #
def make_inputs(indir, n, version=1):
    shutil.rmtree(indir, ignore_errors=True)
    indir.mkdir(parents=True)
    for i in range(n):
        (indir / f"in{i}.txt").write_text(f"line{i}-v{version}\n")


def step5_scope(n=8):
    """Caching + invalidation-scope experiment on a fresh workdir."""
    global records
    indir = BENCH / "cache_inputs_small"
    wd = BENCH / "wd_s5_scope"
    marker = OUT / "marker_s5_scope.log"
    make_inputs(indir, n)
    shutil.rmtree(wd, ignore_errors=True)
    marker.write_text("")
    phases = []

    def one(label, extra=None, note=""):
        env = {
            "BN_N": str(n), "BN_INDIR": str(indir), "BN_WORKDIR": str(wd),
            "BN_MARKER": str(marker), "BN_MIDVARIANT": "A", "BN_SIDEVARIANT": "A",
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

    r1 = one("r1_cold", note="fresh workdir, cache on: everything must execute")
    r2 = one("r2_rerun", note="immediate re-run, nothing changed")
    # (c) modify one input file
    p = indir / f"in{n - 4}.txt"      # in3.txt for n=8
    p.write_text("line3-v2\n")
    r3 = one("r3_input3_changed", note=f"content of {p.name} rewritten")
    # (d) change the script of the Mid process only
    r4 = one("r4_mid_script_changed", extra={"BN_MIDVARIANT": "B"},
             note="Mid process script variant A -> B")
    r5 = one("r5_rerun", extra={"BN_MIDVARIANT": "B"},
             note="re-run immediately after r4, nothing else changed (variant stays B)")

    cands = sorted(set(
        list(Path(BENCH).glob("CachePipeline-output/**/agg.txt"))
        + list(wd.rglob("agg.txt"))
    ))
    if not cands:
        raise FileNotFoundError(f"agg.txt not found under {wd} or {BENCH}/CachePipeline-output")
    agg_out = cands[0]
    return {
        "phases": phases,
        "agg_output_file": str(agg_out),
        "agg_output_content": agg_out.read_text(),
        "agg_output_candidates": [str(c) for c in cands],
        "modified_input": str(p),
        "modified_input_content": p.read_text(),
    }


def step5_timing(n=100, reps=1):
    """Cold vs warm timings at a size where job execution actually costs time."""
    global records
    indir = BENCH / "cache_inputs_big"
    make_inputs(indir, n)
    for rep in range(1, reps + 1):
        wd = BENCH / f"wd_s5_time_r{rep}"
        shutil.rmtree(wd, ignore_errors=True)
        marker = OUT / f"marker_s5_time_r{rep}.log"
        marker.write_text("")
        for label in ("cold", "warm1", "warm2"):
            off = len(marker.read_text().splitlines())
            rec = {"step": "5_caching_timing", "tag": f"s5_time_n{n}_{label}_r{rep}",
                   "n": n, "forks": NPROC, "cache": True, "rep": rep,
                   "_script": "bench_cache_dag.py", "note": label}
            run_pipen(f"s5_time_n{n}_{label}_r{rep}", {
                "BN_N": str(n), "BN_INDIR": str(indir), "BN_WORKDIR": str(wd),
                "BN_MARKER": str(marker), "BN_MIDVARIANT": "A", "BN_SIDEVARIANT": "A",
            }, rec)
            after = [l.split() for l in marker.read_text().splitlines() if l.strip()]
            new = after[off:]
            rec["jobs_executed"] = len(new)
            rec["jobs_by_proc"] = dict(Counter(l[0] for l in new))
            records.append(rec)
            print(f"[s5t] {label} wall={rec['wall_sec']} run={rec['pipeline_run_sec']} "
                  f"jobs={rec['jobs_executed']}", flush=True)
        shutil.rmtree(wd, ignore_errors=True)


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    t_start = time.perf_counter()
    scope = None
    if "3" in only:
        step3()
    if "4" in only:
        step4()
    if "5" in only:
        scope = step5_scope()
        step5_timing()
    (OUT / "pipen_records.json").write_text(json.dumps(records, indent=2))
    if scope:
        (OUT / "pipen_cache_scope.json").write_text(json.dumps(scope, indent=2))
    print(f"TOTAL_DRIVER_SEC={time.perf_counter() - t_start:.1f}", flush=True)
