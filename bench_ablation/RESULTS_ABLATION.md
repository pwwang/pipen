# Ablation: what actually causes pipen's per-job local-scheduling overhead

Scope: `pipen` 1.2.3 (editable install of `~/github/pipen`, commit `6ffb10a`) + `xqute` 2.2.0
(venv `~/bench/.venv`, python 3.12) on the same 32-core WSL2 box that `../bench/RESULTS.md`
measured. **Nothing on disk was modified**: the ablation is applied at runtime by
monkey-patching the constants inside the running process, and the whole source tree is hashed
before and after every timed batch (`raw/derived_ablation.json` -> `driver_source_integrity`;
`source_unchanged: true` in all three batches).

**Every number below is computed from a saved raw log/JSON** (`raw/`, artifact map in section 8).
Statistic for every number: **median of 3 independent runs, min-max in parentheses**.
Wall = end-to-end subprocess wall clock of `python abl_dag.py` (includes interpreter + pipen
import, ~0.6 s); `overhead/job` = (wall - sleep floor)/N with sleep floor = N x 0.05/min(N,32) --
the *same* definition as `../bench/RESULTS.md` section 3, so the two documents are comparable.
Job counts and job-start rates come from per-job timestamps written by the job scripts themselves
(`shard_start i <epoch.N>` / `shard_end i <epoch.N>`), never from framework log lines.

> **Headline**
>
> **1. The existing benchmark's causal claim is refuted.** Lowering
> `xqute.schedulers.local_scheduler.LocalScheduler.SUBMIT_JOB_SLEEP` from 0.1 s to 0.001 s (100x,
> proven by the sleep census to reach all 9/9 submit-loop awaits) changes the N=500 wall time from
> **55.896 s to 56.118 s** (min-max 55.991-56.826,
> ratio 1.004x) and overhead/job from
> **0.1102 s to 0.1107 s**. That is **no gain** --
> within run-to-run spread the patched arm is slightly slower. The 0.1 s submit sleep is not on the
> throughput-critical path at forks=32.
>
> **2. The per-job cost is set by the two 1.0 s waits declared next to it**
> (`SLEEP_INTERVAL_PRODUCER_MAX_FORKS`, `SLEEP_INTERVAL_POLLING_JOBS`). Lowering *those two only*
> (nothing else changed, `SUBMIT_JOB_SLEEP` left at its default 0.1) gives
> **55.896 s -> 38.310 s** at N=500 and overhead/job
> **0.1102 s -> 0.0751 s**, with all 501 jobs
> FINISHED and the aggregation output byte-identical to the baseline: it closes
> **36.1 % of the gap to Snakemake's 0.013 s/job**
> (wall-based check: 38.310 s vs 55.896 s baseline and
> 7.284 s Snakemake = 36.2 % closed).
>
> **3. The residual cost is structural, not a tunable sleep.** After the fix each job still occupies
> a fork slot for **2.28 s** while doing **0.0521 s**
> of work, because xqute's local scheduler injects two hardcoded `sleep 1`s into every job wrapper
> (`xqute/schedulers/local_scheduler.py:151-166`). Deleting them (arm F) reaches
> 0.0661 s/job at N=100 (68.4 % of the gap closed) but is
> **disqualified: 99-100 of 100 jobs are then falsely marked FAILED** and the aggregation
> stage never runs. Those sleeps are a correctness guard, not waste.

## 1. The await sites, and where each patch target comes from

Read-only audit of the installed xqute 2.2.0 (`probe_xqute.sh`, `probe_scheduler.sh`,
`probe_xqute_main.sh`, `probe_pipen.sh`, `probe_template.sh`; per-run SHA256 of every patched module
in `raw/verify_records_pass1.json` and `raw/verify_records.json` -> `effective.source_sha256`).

| # | constant | shipped value | await site (file:line) | how the name is read there | patch target that actually works |
|---|---|---|---|---|---|
| 1 | `LocalScheduler.SUBMIT_JOB_SLEEP` | 0.1 | `xqute/schedulers/local_scheduler.py:62` | instance attribute `self.SUBMIT_JOB_SLEEP`, re-resolved on every call | `pipen.scheduler.LocalScheduler.SUBMIT_JOB_SLEEP` (class attribute; pipen subclasses xqute's class and does not redefine it) |
| 2 | `SLEEP_INTERVAL_PRODUCER_MAX_FORKS` | 1.0 | `xqute/xqute.py:192` | module global of `xqute.xqute` (imported *by value* at line 18) | `xqute.xqute.SLEEP_INTERVAL_PRODUCER_MAX_FORKS` -- patching `xqute.defaults` would have NO effect |
| 3 | `SLEEP_INTERVAL_POLLING_JOBS` | 1.0 | `xqute/xqute.py:320` | module global of `xqute.xqute` | `xqute.xqute.SLEEP_INTERVAL_POLLING_JOBS` (and `xqute.defaults` for consistency) |
| 4 | `SLEEP_INTERVAL_KEEP_FEEDING` | 0.1 | `xqute/xqute.py:314`, only while `self._keep_feeding` | module global of `xqute.xqute` | `xqute.xqute.SLEEP_INTERVAL_KEEP_FEEDING`; pipen *does* use keep-feeding mode (`pipen/proc.py:507`, `run_until_complete(keep_feeding=True)`), so this arm was run rather than skipped |
| 5 | `DEFAULT_SUBMISSION_BATCH` | 8 | `xqute/scheduler.py:84` (`submission_batch: int = DEFAULT_SUBMISSION_BATCH`) | class-body default, **already frozen at import**; the instance reads `self.__class__.submission_batch` in `__init__` (line 111) | `xqute.scheduler.Scheduler.submission_batch` (class attribute) -- patching `xqute.defaults.DEFAULT_SUBMISSION_BATCH` after import has NO effect |
| 6 | (not in the brief) two hardcoded `sleep 1`s | 2 x 1.0 s per job | `xqute/schedulers/local_scheduler.py:151-166` (`jobcmd_wrapper_init` property and `jobcmd_prep` both append `sleep 1`) | literal text injected into every job's wrapper script | rebind both names on `LocalScheduler` to the base `Scheduler` implementations (arm F) |

Constant 6 is why constant 1 is irrelevant. It lives *inside the job wrapper*: it adds 2 s to every
job's lifetime, and because a job counts against `forks` for its whole lifetime, the sustainable job
rate is bounded by forks / 2.05 s ~= 15.6 jobs/s at forks=32 regardless of N -- it is a permanent
throughput ceiling, not a one-off 2 s cost. The 0.1 s submit sleep, by contrast, is paid on a path
that overlaps with job execution (8 consumers can submit in parallel), so it is invisible as long as
submission is not the slowest stage.

### The exact monkey-patch code used (sliced verbatim out of `abl_dag.py`)

```python
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
```

## 2. Proof that each patch reaches the await site (N=8 runs with `ABL_CENSUS=1`)

The two xqute modules that contain the await sites get a proxy `asyncio` object, so every
`await asyncio.sleep(x)` executed *inside them* is recorded with its exact argument; the consumer
spawner is additionally wrapped to record which consumer indexes are started. Raw:
`raw/verify_records_pass1.json` (arms A..E_all) and `raw/verify_records.json` (the `C_pf_poll` arm,
added after the first pass), logs `raw/logs/verify_*.log`.

| arm | `await asyncio.sleep()` calls observed inside xqute (histogram) | consumers started | wall s | shard jobs | agg jobs | `job.status` histogram | jobs falsely marked FAILED (rc=-3) |
|---|---|---|---|---|---|---|---|
| A | `xqute/schedulers/local_scheduler.py` -> 0.1 s x9<br>`xqute/xqute.py` -> 1 s x5<br>`xqute/xqute.py` -> 0.1 s x2 | 8 | 6.025 | 8/8 | 1 | {"6": 9} | 0 |
| B | `xqute/schedulers/local_scheduler.py` -> 0.001 s x9<br>`xqute/xqute.py` -> 1 s x4<br>`xqute/xqute.py` -> 0.1 s x2 | 8 | 5.024 | 8/8 | 1 | {"6": 9} | 0 |
| C_pf | `xqute/schedulers/local_scheduler.py` -> 0.1 s x9<br>`xqute/xqute.py` -> 1 s x5<br>`xqute/xqute.py` -> 0.1 s x2 | 8 | 6.016 | 8/8 | 1 | {"6": 9} | 0 |
| C_poll | `xqute/xqute.py` -> 0.001 s x1438<br>`xqute/schedulers/local_scheduler.py` -> 0.1 s x9<br>`xqute/xqute.py` -> 0.1 s x2 | 8 | 4.947 | 8/8 | 1 | {"6": 9} | 0 |
| C_kf | `xqute/xqute.py` -> 0.001 s x20<br>`xqute/schedulers/local_scheduler.py` -> 0.1 s x9<br>`xqute/xqute.py` -> 1 s x6 | 8 | 6.827 | 8/8 | 1 | {"6": 9} | 0 |
| C_batch | `xqute/schedulers/local_scheduler.py` -> 0.1 s x9<br>`xqute/xqute.py` -> 1 s x5<br>`xqute/xqute.py` -> 0.1 s x2 | 64 | 6.012 | 8/8 | 1 | {"6": 9} | 0 |
| C_pf_poll | `xqute/xqute.py` -> 0.001 s x1464<br>`xqute/schedulers/local_scheduler.py` -> 0.1 s x9<br>`xqute/xqute.py` -> 0.1 s x2 | 8 | 4.975 | 8/8 | 1 | {"6": 9} | 0 |
| F | `xqute/schedulers/local_scheduler.py` -> 0.1 s x8<br>`xqute/xqute.py` -> 1 s x2<br>`xqute/xqute.py` -> 0.1 s x1 | 8 | 2.871 | 8/8 | 0 | {"3": 8} | 8 |
| E_all | `xqute/xqute.py` -> 0.001 s x55<br>`xqute/schedulers/local_scheduler.py` -> 0.001 s x9 | 64 | 0.994 | 8/8 | 0 | {"6": 8, "7": 1} | 0 |

Reading: arm A awaits the shipped values 9x 0.1 s -- 9 = 8 shard + 1 aggregation submissions, one
per job, exactly the await site at `local_scheduler.py:62`. Arm B awaits 9x **0.001 s** at the same
site, which is the direct proof that the runtime patch reaches the submit loop. `C_batch` starts 64
consumers instead of 8, so that patch is effective too. `C_poll` shows the polling loop firing 1438x
inside one 4.9 s run (>250 Hz spin; its CPU cost is measured in section 6). `C_kf` shows the
keep-feeding loop firing ~20x, i.e. that loop barely ever runs (it exits as soon as pipen calls
`stop_feeding()`), which is why arm C_kf has no effect. Arm F shows only 8 submits -- its aggregation
job is never submitted at all (section 5). All canvassed `job.status` values are 6 (FINISHED) except
in the arms that remove the wrapper guard sleeps.

## 3. Timed matrix (cache off, fresh workdir per run, forks=32, 3 reps per cell)

`job-start rate` = (shard jobs - 1) / (last shard start - first shard start), from the job-written
marker timestamps. `mean fork-slot occupancy` = forks / rate: how long one fork slot is held per job,
to compare against the job's own median duration. `output correct` = the produced `agg.txt` is
byte-identical to the baseline's AND to the expected `0\n1\n...\nN-1\n`; `false failures` = job
dirs whose stderr contains xqute's own "fail before running" message (`job.rc == -3`).

Load context: the 1-minute `loadavg` moved between 4.1 and 7.6 across the session (per-run
before/after values in `raw/time_records_*.json`), i.e. the same order of uncontrolled background
load the original benchmark reported (`../bench/RESULTS.md` section 1); the box was not idle for
either experiment.

Coverage: A and B at N=100 and N=500 (3 reps each) as the brief requires; the C arms 3 reps at N=100
(the brief bounds arm C to N=100); plus the extra `C_pf_poll` arm at N=500 so that the
recoverable-fraction statement does not have to be extrapolated from N=100.

Reading note: at N=100 the DAG no longer saturates 32 forks in the fast arms (peak concurrency
5-7 of 32), so `mean fork-slot occupancy` is a lower bound there, not a ceiling; at N=500 it is the
binding quantity. Arms with mechanically identical behaviour can differ by 4-8 % at N=100 (e.g.
`C_kf` and `C_batch` come out 4-6 % *slower* than A for no mechanistic reason, and arm B 8.5 %
slower while its N=500 wall is only 0.4 % slower) -- that is this box's noise band, and it is why
"no effect" is claimed only when the N=500 numbers agree too.

| arm | N | wall median (min-max) | in-process run median | overhead/job median (min-max) | ratio vs baseline A (wall) | job-start rate median (jobs/s) | median job duration (s) | mean fork-slot occupancy (s) = 32/rate | peak concurrent jobs | shard jobs started, 3 reps | agg jobs | output correct | all jobs FINISHED | false failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 100 | **15.150** (15.142-15.306) | 14.519 | 0.1499 (0.1499-0.1515) | 1.000x | 7.95 | 0.0519 | 4.025 | 8 | [100, 100, 100] | [1, 1, 1] | yes | yes | [0, 0, 0] |
| A | 500 | **55.896** (55.035-56.314) | 55.193 | 0.1102 (0.1085-0.1111) | 1.000x | 8.92 | 0.0520 | 3.587 | 19 | [500, 500, 500] | [1, 1, 1] | yes | yes | [0, 0, 0] |
| B | 100 | **16.440** (15.692-17.455) | 15.799 | 0.1628 (0.1554-0.1730) | 1.085x | 8.71 | 0.0520 | 3.674 | 7 | [100, 100, 100] | [1, 1, 1] | yes | yes | [0, 0, 0] |
| B | 500 | **56.118** (55.991-56.826) | 55.387 | 0.1107 (0.1104-0.1121) | 1.004x | 8.87 | 0.0519 | 3.608 | 13 | [500, 500, 500] | [1, 1, 1] | yes | yes | [0, 0, 0] |
| C_pf | 100 | **13.179** (13.089-14.242) | 12.553 | 0.1302 (0.1293-0.1409) | 0.870x | 12.39 | 0.0520 | 2.583 | 5 | [100, 100, 100] | [1, 1, 1] | yes | yes | [0, 0, 0] |
| C_poll | 100 | **12.035** (11.998-12.077) | 11.347 | 0.1188 (0.1184-0.1192) | 0.794x | 14.35 | 0.0520 | 2.230 | 6 | [100, 100, 100] | [1, 1, 1] | yes | yes | [0, 0, 0] |
| C_kf | 100 | **16.073** (15.984-16.345) | 15.463 | 0.1592 (0.1583-0.1619) | 1.061x | 10.31 | 0.0520 | 3.104 | 11 | [100, 100, 100] | [1, 1, 1] | yes | yes | [0, 0, 0] |
| C_batch | 100 | **15.746** (15.296-15.769) | 15.093 | 0.1559 (0.1514-0.1561) | 1.039x | 9.91 | 0.0520 | 3.229 | 6 | [100, 100, 100] | [1, 1, 1] | yes | yes | [0, 0, 0] |
| C_pf_poll | 100 | **11.501** (11.390-11.724) | 10.869 | 0.1135 (0.1123-0.1157) | 0.759x | 15.39 | 0.0521 | 2.079 | 6 | [100, 100, 100] | [1, 1, 1] | yes | yes | [0, 0, 0] |
| C_pf_poll | 500 | **38.310** (38.164-39.121) | 37.619 | 0.0751 (0.0748-0.0767) | 0.685x | 14.06 | 0.0521 | 2.276 | 13 | [500, 500, 500] | [1, 1, 1] | yes | yes | [0, 0, 0] |
| F | 100 | **6.763** (6.018-6.927) | 6.120 | 0.0661 (0.0586-0.0677) | 0.446x | 24.27 | 0.0520 | 1.319 | 7 | [100, 100, 100] | [0, 0, 0] | **NO** | **NO** | [100, 99, 100] |
| E_all | 100 | **2.957** (2.945-3.100) | 2.305 | 0.0280 (0.0279-0.0294) | 0.195x | 54.40 | 0.0520 | 0.588 | 5 | [99, 100, 100] | [0, 1, 0] | **NO** | **NO** | [0, 0, 1] |

For reference, the same quantities measured by the original benchmark on this box
(`../bench/RESULTS.md` section 3, 3 reps): baseline pipen N=100 **15.081 s** / 0.1492 s per job,
N=500 **55.036 s** / 0.1085 s per job; Snakemake `--cores 32` N=100 **2.898 s** / 0.0274 s per job,
N=500 **7.284 s** / 0.0130 s per job. The arm-A numbers reproduced here
(N=100 15.150 s, N=500 55.896 s) agree with that baseline to
within 0.069 s and
0.860 s respectively -- the harness,
the machine and the DAG are reproducible across sessions.

## 4. Which constant is responsible, and how much is recoverable (N=100 unless stated)

| arm | what was patched | overhead/job median (min-max) | ratio vs A | gap to Snakemake's 0.0274 s/job closed | verdict |
|---|---|---|---|---|---|
| A | nothing (shipped defaults) | 0.1499 (0.1499-0.1515) | 1.000x | 0.0 % | valid, correctness verified |
| B | `SUBMIT_JOB_SLEEP` 0.1 -> 0.001 | 0.1628 (0.1554-0.1730) | 1.085x | -10.5 % | valid, correctness verified |
| C_pf | `SLEEP_INTERVAL_PRODUCER_MAX_FORKS` 1.0 -> 0.001, alone | 0.1302 (0.1293-0.1409) | 0.870x | 16.1 % | valid, correctness verified |
| C_poll | `SLEEP_INTERVAL_POLLING_JOBS` 1.0 -> 0.001, alone | 0.1188 (0.1184-0.1192) | 0.794x | 25.4 % | valid, correctness verified |
| C_kf | `SLEEP_INTERVAL_KEEP_FEEDING` 0.1 -> 0.001, alone | 0.1592 (0.1583-0.1619) | 1.061x | -7.6 % | valid, correctness verified |
| C_batch | `DEFAULT_SUBMISSION_BATCH` 8 -> 64, alone | 0.1559 (0.1514-0.1561) | 1.039x | -4.9 % | valid, correctness verified |
| C_pf_poll (extra, not in brief) | producer + polling waits together -> 0.001, nothing else | 0.1135 (0.1123-0.1157) | 0.759x | 29.7 % | valid, correctness verified |
| F (extra, not in brief) | the two hardcoded `sleep 1`s in the job wrapper deleted, alone | 0.0661 (0.0586-0.0677) | 0.446x | 68.4 % | **INVALID - breaks correctness** |
| E_all (extra, not in brief) | everything above relaxed together | 0.0280 (0.0279-0.0294) | 0.195x | 99.5 % | **INVALID - breaks correctness** |

N=500 (only the arms measured there):

| arm | overhead/job median (min-max) | wall median (min-max) | ratio vs A (wall) | gap to Snakemake's 0.013 s/job closed | verdict |
|---|---|---|---|---|---|
| A | 0.1102 (0.1085-0.1111) | 55.896 (55.035-56.314) | 1.000x | 0.0 % | baseline |
| B | 0.1107 (0.1104-0.1121) | 56.118 (55.991-56.826) | 1.004x | -0.5 % | valid, no gain |
| C_pf_poll (extra) | **0.0751** (0.0748-0.0767) | **38.310** (38.164-39.121) | 0.685x | **36.1 %** | valid, correctness verified |

**Plain statement of the result.**

* **The constant responsible is NOT `SUBMIT_JOB_SLEEP`.** Cutting it from 0.1 s to 0.001 s (100x,
  proven by the sleep census to reach all 9/9 submit-loop awaits) leaves the N=500 wall time at
  **56.118 s against 55.896 s unpatched**
  (ratio 1.004x) and the N=500 overhead at
  **0.1107 s/job against 0.1102 s/job**; at N=100 the pair
  is 16.440 s vs 15.150 s. Marginal per-job cost
  ((wall(N=500) - wall(N=100))/400): baseline **0.10187 s/job**, patched
  **0.09919 s/job** -- a 2.6 % difference in the favourable
  direction, i.e. 2.7 ms/job out of the ~100 ms/job being explained, and it does not show up in the
  N=500 wall time (0.4 % *worse*, and 8.5 % worse at N=100, inside the noise band described above).
  The "Mechanism" paragraph of `../bench/RESULTS.md` section 3 ("`SUBMIT_JOB_SLEEP = 0.1`,
  awaited after every job submission ... consistent with the measured ~110 ms/job marginal cost") is
  **refuted by direct measurement**.
* **What is responsible: the two 1.0 s waits in the same file.** `SLEEP_INTERVAL_POLLING_JOBS` -- the
  poller notices a finished job only once per second, so a freed fork slot is wasted for up to 1 s --
  and `SLEEP_INTERVAL_PRODUCER_MAX_FORKS` -- the producer sleeps a full second each time it finds no
  free slot instead of re-checking as soon as one frees. Alone at N=100: `C_poll`
  12.035 s (0.794x, rate
  14.35 jobs/s) and `C_pf` 13.179 s
  (0.870x, rate 12.39 jobs/s);
  both effects are the same mechanism, and together they give **11.501 s
  (0.759x) at N=100 and 38.310 s
  (0.685x) at N=500**. `SLEEP_INTERVAL_KEEP_FEEDING` and
  `DEFAULT_SUBMISSION_BATCH` are non-factors (16.073 s and
  15.746 s vs 15.150 s baseline: no effect beyond noise,
  both slightly slower), which is what the code predicts -- the keep-feeding loop exits almost
  immediately, and submission was never the bottleneck (8 consumers x 1/0.1 s = 80 submits/s available
  against ~9 jobs/s consumed).
* **Recoverable fraction with valid tuning only: 36.1 % of the gap at N=500.**
  Lowering the producer and polling waits from 1.0 s to 0.001 s (and nothing else) reduces the per-job
  overhead from **0.1102 s to 0.0751 s**, i.e. it closes
  **36.1 % of the gap to Snakemake's 0.013 s/job**
  (0.0972 s/job gap ->
  0.0621 s/job residual; wall-based
  36.2 %, 38.310 s vs 55.896 s baseline and
  7.284 s Snakemake). At N=100 the same arm closes 29.7 % of the
  overhead gap. **63.9 % of the gap is not recoverable by tuning any constant
  named in the brief.**
* **What the residual is, measured.** After that fix the job-start rate at N=500 is
  **14.06 jobs/s**, i.e. a fork slot stays occupied **2.28 s per job**
  while the job's own median duration is only **0.0521 s** -- a
  44x amplification. About 2.0 s of that is the two hardcoded
  `sleep 1`s in the wrapper, which alone impose a ceiling of 32/2.05 = 15.6 jobs/s at
  forks=32; the measured 14.06 jobs/s sits just below it, the remainder being the
  ~0.2 s of per-job wrapper/spawn cost that no constant in the brief covers. Once the 1 s quantisation
  is removed, throughput is essentially set by the guard sleeps.
* **In-principle bound, not shippable: 99.5 % of the N=100 gap.** Arm `E_all` (all of the
  above *plus* the guard sleeps deleted) reaches 0.0280 s/job at N=100 --
  statistically indistinguishable from Snakemake's 0.0274 s/job -- but only
  1 of its 3 runs produced a correct pipeline (per-rep output-correct flags
  [False, True, False], shard jobs per rep [99, 100, 100]), so it is not a configuration a paper can
  recommend. It does bound the size of the recoverable cost: essentially all of the gap is framework
  latency, not process spawn or the job's own sleep.

## 5. Correctness check (arm D), and the arm it disqualified

Every run is checked four ways, all from artifacts the framework does not control: (a) the
aggregation output must be byte-identical to the baseline's and to the expected `0\n1\n...\nN-1\n`;
(b) the marker count must be exactly N shard + 1 agg; (c) every `job.status` must be 6 (FINISHED) with
`job.rc` 0; (d) no `job.stderr` may contain xqute's "fail before running" message (`rc=-3`).

* **Arms A, B, C_pf, C_poll, C_kf, C_batch, C_pf_poll pass all four checks in all 3 reps.** In
  particular lowering `SUBMIT_JOB_SLEEP` is *safe* -- outputs byte-identical to the baseline (N=8
  SHA256 `d59784813bbf8e9a47929bbd4195498a43979c690f9e799cfe2e14522217c48d` for A and B; the N=100/500
  aggregations match `0..N-1` in every rep). It simply does not help.
  Note on job counting: at the default `loglevel=info` pipen emits **no per-job log lines at all**
  (a 101-job run produces 41 log lines, all pipeline/proc banners -- `croscheck_counts.sh`), so there
  is no framework-supplied job count to agree with, and the marker timestamps are the only source of
  the executed-job counts in this document (which is what the brief asks for). The marker counts are
  exact and stable: 100/100 and 500/500 shard jobs plus exactly 1 aggregation job in every rep of
  every valid arm.
* **Arm F is a fake win and is excluded from every recoverable-fraction number above.** N=100: wall
  6.763 s (0.446x) and overhead
  0.0661 s/job (68.4 % of the gap) -- but
  **[99-100] of 100 jobs are marked FAILED with `rc=-3` in all 3 reps**, no `agg.txt` is produced
  anywhere in the workdir, the aggregation job is never submitted (`agg=0`), and the pipeline still
  exits rc=0. A reader who looked only at wall time would call this a
  2.2x win.
* **Mechanism of the F breakage** (read off the artifacts, not guessed): `LocalScheduler.submit_job`
  returns only after awaiting `SUBMIT_JOB_SLEEP` (0.1 s), and the *consumer* writes `SUBMITTED` into
  `job.status` only after that returns (`xqute/scheduler.py:196,201`), while the job wrapper's own
  `RUNNING`/`FINISHED` writes happen a few ms after the process starts. With the guard `sleep 1`s gone
  the wrapper writes `FINISHED` at ~60 ms and the scheduler then overwrites the status file with
  `SUBMITTED` at ~100 ms; the pid is already dead and the file says 3, so `job_fails_before_running()`
  (`local_scheduler.py:115-149`) declares the job failed with `rc=-3`. Observed at N=8:
  `job.status` histogram `{'3': 8}`, `job.rc` histogram `{'-3': 8}`; at N=100, 99-100 per rep
  (`raw/logs/F_n100_r*.log`, `ABL_STATUS=` lines). The two `sleep 1`s exist precisely to preserve that
  write ordering: they are a correctness guard for sub-second jobs, which is why they cannot simply be
  deleted.
* `E_all` sits between the two: it removes the guard sleeps but also cuts `SUBMIT_JOB_SLEEP` to 1 ms,
  which changes the interleaving, so its failures are non-deterministic (`[False, True, False]`) -- one run
  lost a shard job entirely (`[99, 100, 100]`), two runs never produced the aggregation. Its speed
  number is reported only as an upper bound.

## 6. What the valid tuning costs in CPU (1 rep each, N=100, whole process tree)

| arm | wall s | user s | sys s | total CPU s | CPU per job |
|---|---|---|---|---|---|
| A | 16.249 | 6.568 | 2.144 | 8.712 | 87.1 ms |
| C_poll | 14.882 | 11.851 | 5.588 | 17.439 | 174.4 ms |
| C_pf_poll | 11.616 | 11.279 | 5.496 | 16.775 | 167.7 ms |

Measured with bash `time` around the pipeline invocation (kernel-propagated child rusage, so it
covers the pipeline process and every job wrapper it waited for). Raw: `raw/cpu_probe.txt`, logs
`raw/logs/cpuprobe_*.log`. Single runs, not 3-rep medians -- treat as indicative. The 1 ms polling
interval turns the O(N)-per-iteration status poll (`Scheduler.check_all_done` re-reads every job's
status file on every iteration) into a hot loop: CPU per job rises from
87.1 ms for the baseline to
174.4 ms for `C_poll`
(2.0x the CPU) for a
8 % wall-time gain.
`C_pf_poll` costs the same CPU as `C_poll` but is faster in wall time, so the producer-side constant
is nearly free while the wall-time gain of the polling constant is bought with CPU. A production
setting would want an intermediate interval (e.g. 20-50 ms) and a correspondingly smaller
`recheck_interval` (`DEFAULT_RECHECK_INTERVAL = 60` polls, so that failure detection is not scaled
down 1000x with the interval) -- neither was tested here.

## 7. What I did NOT test

* **No Snakemake re-run.** Snakemake's 7.284 s / 0.0130 s-per-job (N=500) and 2.898 s / 0.0274 s-per-job
  (N=100) are quoted from `../bench/RESULTS.md` section 3 (same machine, same DAG, 3 reps,
  `--cores 32`), measured in an earlier session; the loadavg recorded here (4.1-7.6) is the same order,
  but no Snakemake arm was re-measured inside this ablation. Nothing here is a fresh head-to-head
  number.
* **N=500 only for A, B and the extra `C_pf_poll`.** C arms are N=100 by the brief's bound; `F` and
  `E_all` are N=100 only, because they are disqualified by the correctness check.
* **`submission_batch` was only raised (8 -> 64), never lowered** (1-2, which serialises submissions,
  was not tested). **`SUBMIT_JOB_SLEEP` was only lowered, never removed entirely.**
* **Other per-job work inside the same wrapper was not ablated**: the 20 KB `/tmp` spaceholder written
  by `dd` plus a `sha256sum` for every job (xqute's wrapper template), the `set -x -u -E -o pipefail`
  tracing, the two status-file writes per job, and pipen's per-job signature files. Any of these could
  be part of the residual ~0.075 s/job.
* **Only the local scheduler.** SGE/Slurm/SSH/container schedulers, cloud workdirs,
  `SLEEP_INTERVAL_CLOUD_FILE_CHECK` and `SLEEP_INTERVAL_GBATCH_STATUS_CHECK` untouched.
* **Happy path only.** No failing job, no retry, no `error_strategy=halt`, no timeout, no cache-on
  runs. In particular I did not test whether a 1 ms polling interval changes *failure* detection
  latency (`recheck_interval=60` polls becomes 60 ms instead of 60 s) -- a behaviour change a user
  must consider before adopting `C_pf_poll`.
* **Only forks=32 and N >> forks.** The claim "`SUBMIT_JOB_SLEEP` is irrelevant" is established for
  that regime only. At forks<=4 the original benchmark measured 0.3-1.2 jobs/s and the submit loop
  could plausibly become the binding constraint there -- untested.
* **No real pipeline**: no I/O-heavy or long-running jobs, no multi-process recipes, no real
  bioinformatics workload; the DAG is exactly the original benchmark's 500 x (`sleep 0.05` + one
  1-line file) + 1 aggregation job.

## 8. Raw artifacts, integrity, and how to reproduce

```
bench_ablation/
  RESULTS_ABLATION.md          this file (generated, deterministic from raw/)
  abl_dag.py                   the DAG + the runtime monkey-patch layer + the sleep census
  driver_ablation.py           runs the arms, parses logs/markers, writes the records (verify/calib/time/copy)
  make_report_ablation.py      analysis -> raw/derived_ablation.json
  emit_results_ablation.py     this markdown generator (every number comes from raw/)
  cpu_probe.sh                 the CPU-cost probe of section 6
  croscheck_counts.sh          the framework-log vs marker-count cross-check of section 5
  inventory.sh                 artifact inventory (file counts / sizes of raw/)
  probe_xqute.sh probe_scheduler.sh probe_xqute_main.sh probe_pipen.sh probe_template.sh
  diag_F.sh diag_F2.sh         read-only source audits + the arm-F diagnostics of sections 1 and 5
  raw/
    verify_records_pass1.json  section 2: sleep census / effective constants / module SHA256s, arms A..E_all
    verify_records.json        section 2: same, for the C_pf_poll arm (added after the first pass)
    time_records_A-B.json      section 3: arms A and B, N=100 and N=500, 3 reps each
    time_records_C_pf-C_poll-C_kf-C_batch-C_pf_poll-F-E_all.json
                               section 3: C arms + F + E_all, N=100, 3 reps each
    time_records_C_pf_poll.json  section 3: C_pf_poll at N=500, 3 reps
    derived_ablation.json      derived numbers + source-tree hashes + marginal costs + gap-closure fractions
    cpu_probe.txt              section 6
    logs/                      full stdout of every run (A_*, B_*, C_*, F_*, E_all_*, verify_*, cpuprobe_*)
    markers/                   per-job start/end epoch timestamps for every run
```

Reproduction (inside WSL, order matters); each batch hashes
`~/github/pipen/pipen` and the installed `xqute` tree before and after, and `source_unchanged` is
`true` for all three (`raw/derived_ablation.json` -> `driver_source_integrity`):

```bash
~/bench/.venv/bin/python driver_ablation.py verify
~/bench/.venv/bin/python driver_ablation.py time --arms A,B --n 100,500 --reps 3
~/bench/.venv/bin/python driver_ablation.py time --arms C_pf,C_poll,C_kf,C_batch,C_pf_poll,F,E_all --n 100 --reps 3
~/bench/.venv/bin/python driver_ablation.py time --arms C_pf_poll --n 500 --reps 3
bash cpu_probe.sh
~/bench/.venv/bin/python driver_ablation.py copy       # ~/bench_abl/out -> raw/
~/bench/.venv/bin/python make_report_ablation.py       # -> raw/derived_ablation.json
~/bench/.venv/bin/python emit_results_ablation.py      # -> RESULTS_ABLATION.md
```

Total measured pipeline wall time (all arms, all reps, including the discarded first `verify` pass and
the CPU probe): **~15.1 min** against the ~12 min guidance. The overrun is the two mandated N=500 arms
(A and B, ~2.9 min each at 3 reps) plus the extra `C_pf_poll` N=500 arm (~1.9 min) that was added so
the recoverable fraction is a measurement rather than an extrapolation. No number in this document is
estimated from a model.

