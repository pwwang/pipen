"""Ablation DAG for the pipen/xqute local-scheduler overhead claim.

Same DAG as bench/bench_pipen_dag.py:  N independent shard jobs, each running
`sleep 0.05` and writing a one-line file, feeding ONE aggregation job
(`cat shardfiles > agg.txt`).  Cache off.  Fresh workdir per run.

On top of that DAG this script adds:

 1. A RUNTIME MONKEY-PATCH LAYER (env `ABL_ARM`) that changes xqute's scheduling
    constants inside this process, at runtime.  NOTHING on disk is modified:
    `~/github/pipen`, `~/github/xqute` and the installed xqute 2.2.0 are untouched.
    The patch table is right below; every patched name is re-read at the await
    site (see comments) and the *effective* values are printed as
    `ABL_EFFECTIVE=<json>` so the driver can log what actually took effect.

 2. A process-tree sampler thread: number of live descendant processes of this
    pipeline process, and how many of them are job wrappers (`job.wrapped.*`).
    This measures the scheduler's *occupancy* independently of the framework's
    own logging.

 3. SHA256 + line count of every `agg.txt` produced (correctness check, arm D).

Env:
  ABL_ARM      arm name, key of PATCH_TABLE (default "A" = unmodified baseline)
  ABL_N        number of fan-out jobs
  ABL_SLEEP    sleep per shard (default 0.05)
  ABL_FORKS    forks (default 32)
  ABL_WORKDIR  pipeline workdir (fresh per run)
  ABL_MARKER   append-only job marker log (one line per *job execution*)
Prints (stdout, one JSON/float per line):
  ABL_EFFECTIVE=<json>   patched + effective values
  PIPELINE_RUN_SEC=<f>   in-process time around Pipeline.run()
  ABL_AGG=<json>         [{"path":..,"sha256":..,"lines":..}, ...]
"""
import hashlib
import json
import os
import shlex
import threading
import time
from pathlib import Path

import pandas as pd

N = int(os.environ["ABL_N"])
SLEEP = os.environ.get("ABL_SLEEP", "0.05")
FORKS = int(os.environ.get("ABL_FORKS", "32"))
WORKDIR = os.environ["ABL_WORKDIR"]
MARKER = shlex.quote(os.environ["ABL_MARKER"])
ARM = os.environ.get("ABL_ARM", "A")

# ====================================================================== #
# THE PATCH TABLE  (arm -> {xqute constant: value to set at runtime})
# ====================================================================== #
PATCH_TABLE = {
    # A: baseline, every xqute constant at its shipped default
    "A": {},
    # B: the submit-loop sleep, awaited after EVERY job submission
    #    (xqute/schedulers/local_scheduler.py:62 `await asyncio.sleep(self.SUBMIT_JOB_SLEEP)`)
    "B": {"SUBMIT_JOB_SLEEP": 0.001},
    # C_*: one constant at a time, everything else at defaults
    #    xqute/xqute.py:192  `await asyncio.sleep(SLEEP_INTERVAL_PRODUCER_MAX_FORKS)`
    "C_pf": {"SLEEP_INTERVAL_PRODUCER_MAX_FORKS": 0.001},
    #    xqute/xqute.py:320  `await asyncio.sleep(SLEEP_INTERVAL_POLLING_JOBS)`
    "C_poll": {"SLEEP_INTERVAL_POLLING_JOBS": 0.001},
    #    the two 1.0 s producer/polling waits together, nothing else changed
    "C_pf_poll": {"SLEEP_INTERVAL_PRODUCER_MAX_FORKS": 0.001,
                  "SLEEP_INTERVAL_POLLING_JOBS": 0.001},
    #    xqute/xqute.py:314  `await asyncio.sleep(SLEEP_INTERVAL_KEEP_FEEDING)`
    "C_kf": {"SLEEP_INTERVAL_KEEP_FEEDING": 0.001},
    #    xqute/scheduler.py:84 `submission_batch: int = DEFAULT_SUBMISSION_BATCH`
    #    read in Scheduler.__init__ as `self.__class__.submission_batch`
    "C_batch": {"SUBMISSION_BATCH": 64},
    # F: the two `sleep 1`s the LOCAL scheduler injects into each job wrapper
    #    (local_scheduler.py:151-166) -- not in the brief's constant list, but
    #    they are what makes each job occupy a fork slot for ~2 s.
    "F": {"WRAPPER_SLEEPS": "removed"},
    # E_all: everything relaxed at once = upper bound on what is recoverable
    #        by tuning xqute's own constants (still no framework code edited)
    "E_all": {
        "SUBMIT_JOB_SLEEP": 0.001,
        "SLEEP_INTERVAL_PRODUCER_MAX_FORKS": 0.001,
        "SLEEP_INTERVAL_POLLING_JOBS": 0.001,
        "SLEEP_INTERVAL_KEEP_FEEDING": 0.001,
        "SUBMISSION_BATCH": 64,
        "WRAPPER_SLEEPS": "removed",
    },
}


def apply_patches(arm: str) -> dict:
    """Set the arm's constants on the LIVE objects and report what took effect.

    Import-path audit (why each target is what it is):
      * SUBMIT_JOB_SLEEP -- class attribute of
        xqute.schedulers.local_scheduler.LocalScheduler, read at the await site
        as `self.SUBMIT_JOB_SLEEP`, so patching the class attribute is picked up
        at call time.  pipen.scheduler.LocalScheduler subclasses it and does NOT
        redefine the attribute, so we patch both (the pipen subclass directly is
        what `self.` resolves to).
      * SLEEP_INTERVAL_* -- imported *by value* into the xqute.xqute module
        namespace (`from .defaults import ...`) and read there as module globals
        at xqute/xqute.py:192/314/320.  Patching xqute.defaults alone would have
        NO effect, so we patch `xqute.xqute.<NAME>` (and the defaults module too,
        so any other reader agrees).
      * DEFAULT_SUBMISSION_BATCH -- imported by value into xqute.scheduler and
        used as a *class-body default* (`submission_batch: int = ...`), already
        frozen when the class was created.  Patching xqute.defaults after import
        therefore has NO effect; what works is patching the class attribute
        `xqute.scheduler.Scheduler.submission_batch`, which is read at
        instantiation time as `self.__class__.submission_batch`.
      * WRAPPER_SLEEPS -- the local scheduler overrides the
        `jobcmd_wrapper_init` property and the `jobcmd_prep` method, each of which
        appends a literal "sleep 1" to the job wrapper script.  We rebind both on
        the class to the *base* Scheduler implementation, which is exactly the
        no-sleep behaviour.
    """
    import xqute.xqute as xq_main
    import xqute.defaults as xq_defaults
    import xqute.scheduler as xq_sched
    import xqute.schedulers.local_scheduler as xq_local
    import pipen.scheduler as pipen_sched

    want = PATCH_TABLE[arm]
    eff: dict = {"arm": arm, "requested": want, "effective": {}}

    if "SUBMIT_JOB_SLEEP" in want:
        v = want["SUBMIT_JOB_SLEEP"]
        xq_local.LocalScheduler.SUBMIT_JOB_SLEEP = v
        pipen_sched.LocalScheduler.SUBMIT_JOB_SLEEP = v
        # effective = what `self.SUBMIT_JOB_SLEEP` inside submit_job() resolves to
        eff["effective"]["SUBMIT_JOB_SLEEP"] = pipen_sched.LocalScheduler.SUBMIT_JOB_SLEEP
        eff["effective"]["SUBMIT_JOB_SLEEP_resolved_from"] = (
            "pipen.scheduler.LocalScheduler (MRO of the instance pipen builds)"
        )

    for name in (
        "SLEEP_INTERVAL_PRODUCER_MAX_FORKS",
        "SLEEP_INTERVAL_POLLING_JOBS",
        "SLEEP_INTERVAL_KEEP_FEEDING",
    ):
        if name in want:
            v = want[name]
            setattr(xq_main, name, v)       # <- the name the await site reads
            setattr(xq_defaults, name, v)   # keep the origin module consistent
            eff["effective"][name] = getattr(xq_main, name)
            eff["effective"][name + "_resolved_from"] = "xqute.xqute module global"

    if "SUBMISSION_BATCH" in want:
        v = want["SUBMISSION_BATCH"]
        xq_sched.Scheduler.submission_batch = v
        xq_defaults.DEFAULT_SUBMISSION_BATCH = v
        eff["effective"]["submission_batch"] = pipen_sched.LocalScheduler.submission_batch
        eff["effective"]["submission_batch_resolved_from"] = (
            "xqute.scheduler.Scheduler.submission_batch (self.__class__ lookup)"
        )

    if want.get("WRAPPER_SLEEPS") == "removed":
        Scheduler = xq_sched.Scheduler
        base_init_prop = Scheduler.__dict__["jobcmd_wrapper_init"]  # property, no "sleep 1"
        xq_local.LocalScheduler.jobcmd_wrapper_init = property(
            lambda self: base_init_prop.fget(self)
        )
        base_prep = Scheduler.__dict__["jobcmd_prep"]                 # no "sleep 1" appended
        xq_local.LocalScheduler.jobcmd_prep = (
            lambda self, job: base_prep(self, job)
        )
        eff["effective"]["wrapper_sleeps"] = "removed (jobcmd_wrapper_init/jobcmd_prep -> base)"

    if not want:
        eff["effective"] = {
            "SUBMIT_JOB_SLEEP": pipen_sched.LocalScheduler.SUBMIT_JOB_SLEEP,
            "SLEEP_INTERVAL_PRODUCER_MAX_FORKS": xq_main.SLEEP_INTERVAL_PRODUCER_MAX_FORKS,
            "SLEEP_INTERVAL_POLLING_JOBS": xq_main.SLEEP_INTERVAL_POLLING_JOBS,
            "SLEEP_INTERVAL_KEEP_FEEDING": xq_main.SLEEP_INTERVAL_KEEP_FEEDING,
            "submission_batch": pipen_sched.LocalScheduler.submission_batch,
            "wrapper_sleeps": "as shipped (2 x sleep 1 per job wrapper)",
        }
    # provenance: byte-identical source hashes of the modules we patched in RAM
    eff["source_files"] = {
        "xqute/schedulers/local_scheduler.py": xq_local.__file__,
        "xqute/xqute.py": xq_main.__file__,
        "xqute/scheduler.py": xq_sched.__file__,
        "pipen/scheduler.py": pipen_sched.__file__,
    }
    eff["source_sha256"] = {
        k: hashlib.sha256(Path(v).read_bytes()).hexdigest()
        for k, v in eff["source_files"].items()
    }
    return eff


EFFECTIVE = apply_patches(ARM)

# ====================================================================== #
# SLEEP CENSUS (env ABL_CENSUS=1): wrap the `asyncio` reference held by the two
# xqute modules that contain the await sites, so every `await asyncio.sleep(x)`
# executed inside them is recorded with its exact argument.  This is the direct,
# observational proof that a patch reaches the await site (or that an arm's
# await site never fires).  It is only enabled for short verification runs.
# ====================================================================== #
if os.environ.get("ABL_CENSUS") == "1":
    import asyncio as _real_asyncio
    import xqute.xqute as _xq_main
    import xqute.schedulers.local_scheduler as _xq_local

    _CENSUS = []

    class _AsyncioProxy:
        """Forwards everything to the real asyncio; records .sleep() calls."""

        def __init__(self, real, where):
            self._real = real
            self._where = where

        def sleep(self, delay, *a, **k):
            _CENSUS.append([self._where, float(delay)])
            return self._real.sleep(delay, *a, **k)

        def __getattr__(self, name):
            return getattr(self._real, name)

    _xq_main.asyncio = _AsyncioProxy(_real_asyncio, "xqute/xqute.py")
    _xq_local.asyncio = _AsyncioProxy(_real_asyncio, "xqute/schedulers/local_scheduler.py")

    # Direct proof that the submission_batch patch reaches the consumer spawner:
    # count which consumer indices Xqute ever starts.
    _CONSUMER_INDEXES = set()
    _orig_consumer = _xq_main.Xqute._consumer

    async def _counting_consumer(self, index):
        _CONSUMER_INDEXES.add(index)
        return await _orig_consumer(self, index)

    _xq_main.Xqute._consumer = _counting_consumer

    EFFECTIVE["sleep_census_enabled"] = True
else:
    _CENSUS = []

print("ABL_EFFECTIVE=" + json.dumps(EFFECTIVE), flush=True)

from pipen import Pipen, Proc  # noqa: E402  (imported after patching, deliberately)


class Shard(Proc):
    """fan-out shard"""

    input = "i"
    input_data = list(range(N))
    forks = FORKS
    cache = False
    output = "outfile:file:shard-{{in.i}}.txt"
    script = (
        "echo shard_start {{in.i}} $(date +%s.%N) >> " + MARKER + "\n"
        "sleep " + SLEEP + "\n"
        "echo {{in.i}} > {{out.outfile}}\n"
        "echo shard_end {{in.i}} $(date +%s.%N) >> " + MARKER
    )


class Agg(Proc):
    """aggregate all shard outputs into one file"""

    requires = Shard
    forks = FORKS
    cache = False
    input = "shardfiles:files"
    output = "outfile:file:agg.txt"
    script = (
        "echo agg_start 0 $(date +%s.%N) >> " + MARKER + "\n"
        "cat {{in.shardfiles | join: ' '}} > {{out.outfile}}\n"
        "echo agg_end 0 $(date +%s.%N) >> " + MARKER
    )
    input_data = lambda ch: pd.DataFrame({"shardfiles": [list(ch.iloc[:, 0])]})


class AblPipeline(Pipen):
    starts = Shard
    workdir = WORKDIR
    forks = FORKS
    cache = False


# ---------------------------------------------------------------------- #
# occupancy sampler: live descendants of this process, and of those the
# job wrappers (`job.wrapped.local*`).  Independent of framework logging.
# ---------------------------------------------------------------------- #
class TreeSampler(threading.Thread):
    def __init__(self, root, interval=0.05):
        super().__init__(daemon=True)
        self.root = root
        self.interval = interval
        self._halt = threading.Event()
        self.samples = []          # (n_descendants_incl_self, n_wrappers)
        self.peak_desc = 0
        self.peak_wrappers = 0

    @staticmethod
    def _snapshot():
        ppid, wrappers = {}, {}
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                with open(f"/proc/{entry}/stat", "rb") as fh:
                    data = fh.read()
                rp = data.rfind(b")")
                ppid[int(entry)] = int(data[rp + 2:].split()[1])
                with open(f"/proc/{entry}/cmdline", "rb") as fh:
                    cl = fh.read()
                wrappers[int(entry)] = 1 if b"job.wrapped" in cl else 0
            except Exception:
                continue
        return ppid, wrappers

    def run(self):
        while not self._halt.is_set():
            try:
                ppid, wrappers = self._snapshot()
                children = {}
                for p, pp in ppid.items():
                    children.setdefault(pp, []).append(p)
                stack, seen = [self.root], set()
                while stack:
                    p = stack.pop()
                    if p in seen:
                        continue
                    seen.add(p)
                    stack.extend(children.get(p, ()))
                ndesc = len(seen)                      # includes self
                nwrap = sum(wrappers.get(p, 0) for p in seen)
                self.samples.append((ndesc, nwrap))
                self.peak_desc = max(self.peak_desc, ndesc)
                self.peak_wrappers = max(self.peak_wrappers, nwrap)
            except Exception:
                pass
            time.sleep(self.interval)

    def stop(self):
        self._halt.set()
        self.join(timeout=5)


if __name__ == "__main__":
    sampler = TreeSampler(os.getpid())
    sampler.start()
    t0 = time.perf_counter()
    AblPipeline().run()
    t1 = time.perf_counter()
    sampler.stop()
    run_sec = t1 - t0
    print(f"PIPELINE_RUN_SEC={run_sec:.6f}", flush=True)

    # correctness: every agg.txt produced anywhere under the workdir
    aggs = []
    for p in sorted(Path(WORKDIR).rglob("agg.txt")):
        try:
            b = p.read_bytes()
        except Exception as e:  # pragma: no cover
            aggs.append({"path": str(p), "error": repr(e)})
            continue
        aggs.append({
            "path": str(p),
            "sha256": hashlib.sha256(b).hexdigest(),
            "lines": len(b.splitlines()),
            "bytes": len(b),
        })
    print("ABL_AGG=" + json.dumps(aggs), flush=True)
    if _CENSUS:
        hist = {}
        for where, delay in _CENSUS:
            hist.setdefault(f"{where}|{delay:g}", 0)
            hist[f"{where}|{delay:g}"] += 1
        print("ABL_SLEEP_CENSUS=" + json.dumps({
            "calls": len(_CENSUS),
            "histogram": dict(sorted(hist.items(), key=lambda kv: -kv[1])),
            "consumer_indexes_seen": sorted(_CONSUMER_INDEXES),
            "n_consumers_seen": len(_CONSUMER_INDEXES),
        }), flush=True)

    # ---- correctness census: what the scheduler *believed* about each job,
    #      read back from the on-disk job metadata (not from a log we control).
    status_hist, rc_hist = {}, {}
    false_fail_before_running = []
    n_job_dirs = 0
    for st in sorted(Path(WORKDIR).rglob("job.status")):
        n_job_dirs += 1
        try:
            v = st.read_text().strip()
        except Exception:  # pragma: no cover
            v = "?"
        status_hist[v] = status_hist.get(v, 0) + 1
        rc = st.parent / "job.rc"
        try:
            rv = rc.read_text().strip() if rc.exists() else "(no rc file)"
        except Exception:  # pragma: no cover
            rv = "?"
        rc_hist[rv] = rc_hist.get(rv, 0) + 1
        err = st.parent / "job.stderr"
        try:
            et = err.read_text() if err.exists() else ""
        except Exception:  # pragma: no cover
            et = ""
        if "fail before running" in et:
            false_fail_before_running.append(str(st.parent.relative_to(WORKDIR)))
    print("ABL_STATUS=" + json.dumps({
        "n_job_dirs": n_job_dirs,
        "job_status_histogram": dict(sorted(status_hist.items())),
        "job_rc_histogram": dict(sorted(rc_hist.items())),
        "n_jobs_marked_failed_before_running": len(false_fail_before_running),
        "jobs_marked_failed_before_running": false_fail_before_running[:20],
        "note": "job.status: 6=FINISHED 3=SUBMITTED 7=FAILED 4=RUNNING; rc=-3 == 'fail before running'",
    }), flush=True)
    nw = [s[1] for s in sampler.samples]
    nd = [s[0] for s in sampler.samples]
    print("ABL_OCCUPANCY=" + json.dumps({
        "sampler_interval_sec": 0.05,
        "n_samples": len(sampler.samples),
        "peak_wrapper_processes": sampler.peak_wrappers,
        "mean_wrapper_processes": round(sum(nw) / len(nw), 3) if nw else None,
        "peak_descendant_processes_incl_self": sampler.peak_desc,
        "mean_descendant_processes_incl_self": round(sum(nd) / len(nd), 3) if nd else None,
    }), flush=True)
