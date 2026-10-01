# pipen benchmark harness — portability notes

Scope: everything needed to re-run the pipen-vs-Snakemake benchmark harness
(`F:/E/hermes-workspace/pipen/bench/`) on a **different machine**, from the
archived materials, without editing code. Written for a reviewer of the pipen
paper who wants to check or extend the measurements.

> **What was measured, and what was not.**
> The published numbers in `bench/RESULTS.md` (pipen 1.2.3 vs Snakemake 9.27.0,
> N=500 wall 55.896 s / 7.284 s, 12.97× caching speed-up at N=100, …) come from
> the **earlier full-size run**. They were *not* reproduced here.
> The portability work was verified with a **reduced-size run** (N=20 scaling,
> N=20 concurrency at 2 fork levels, N=8 caching scope, N=20 cold/warm caching,
> 1 rep) on a **clean virtualenv at a different path**. Reduced-run observations
> are labelled as such everywhere below.
> `bench/RESULTS.md` and `bench/raw/` were not modified (verified: 0 files in
> `raw/` with an mtime on the portability date).

---

## 1. Inventory: machine assumptions that were baked into the harness

Raw grep evidence of the pre-change state: `bench_portability/evidence/inventory_before.txt`
(161 matching lines). Pristine copies of the six modified Python files:
`bench_portability/orig/`.

### 1a. Absolute paths and interpreters

| file | assumption (pre-change) |
|---|---|
| `driver_pipen.py` | `HOME/bench`, `OUT=~/bench/out`, `VPY=~/bench/.venv/bin/python` (the pipen interpreter), `SCRIPT=/mnt/f/E/hermes-workspace/pipen/bench` |
| `driver_smk.py` | `sys.path.insert(0, "/mnt/f/…/bench")`, `SMK=~/bench/smk/bin/snakemake`, `SMKDIR=/mnt/f/…/bench` |
| `analyse_all.py` | `OUT=~/bench/out`, results copied to `DEST=/mnt/f/…/bench` (+ `DEST/raw`), `~/bench/.venv/bin/python` used to spawn `analyse_marker.py` |
| `evidence.py` | `OUT=~/bench/out`, `DEST=/mnt/f/…/bench`, `RAW=DEST/raw`, scope workdir `~/bench/wd_s5_scope/CachePipeline`, inputs `~/bench/cache_inputs_small` |
| `make_report.py` | `OUT=~/bench/out`, writes `DEST/raw/derived_numbers.json` |
| `env_json.py` | pipen checkout `~/github/pipen`, `venv_py=~/bench/.venv/bin/python`, snakemake version probed from `~/bench/smk/bin/python`, `df -hT / /mnt/f ~` |
| `bench_pipen_dag.py`, `bench_cache_dag.py` | concurrency as a code constant (`forks = 32` in 5 places in the caching DAG; `BENCH_FORKS` default 1 in the scaling DAG) |
| `hello_pipen.py` | default data file `/tmp/pipen_hello_data.txt` |
| legacy one-off scripts (`setup.sh`, `verify.sh`, `calibrate.sh`, `diag.sh`, `install_smk.sh`, `package*.sh`, `run_*.sh`, `inspect_*.sh`, `debug_*.sh`, `gap_analysis.sh`, `smk_smoke.sh`, `probe_*.py`, `touch_test2.py`) | `$HOME/bench`, `/mnt/f/…/bench`, `~/bench/.venv/lib/python3.12/site-packages` — run-once provenance of the archived session, not part of the re-runnable path |

### 1b. Protocol sizes hardcoded in code (not parameterisable)

`driver_pipen.py`: step 3 `N ∈ (1, 10, 100, 500)`, `reps=3`; step 4 `N=20`,
`forks ∈ (1, 2, 4, nproc)`; step 5 scope `N=8`; step 5 timing `N=100`;
sleep literal `"0.05"`; `nproc = os.cpu_count()` (correct, but not overridable).
`driver_smk.py`: the same matrix with `--cores = os.cpu_count()`.
`analyse_all.py`: marker-file names of the full-size run (`*n500*`, `*n100*`,
`*n20*`) were enumerated in a literal list, plus two hardcoded N=100 diagnostic
data points quoted from the archived run.
`evidence.py`: job counts `Read/Mid/Side = 8, Agg = 1` and the modified-input
path were literals.

### 1c. Non-obvious hazards found while making this portable

1. **Marker logs are the job-count measurement, and they were written under
   `OUT_ROOT`.** Concurrent per-job appends (`>>`) silently lose lines on a 9p
   mount. Measured on this box, same N=20 DAG, same code, only the marker
   filesystem differing: **42/42 lines on ext4, 29/42 on `/mnt/f` (9p)** —
   `bench_portability/evidence/diag_marker.out`. Fixed: markers now live under
   `WORK_ROOT` (documented as "must be local"), and the exact bytes are copied
   to `OUT_ROOT/markers/` for the record; the closing summary asserts every
   arm's marker-line count against the DAG's arithmetic expectation.
2. **`OUT_ROOT` on a network mount also reorders the driver's own job counts**,
   so the failure is silent unless checked. `preflight.py` now warns when
   `WORK_ROOT` or `OUT_ROOT` is on `9p/cifs/nfs/…`.
3. **pipen exports an end-process output to `<cwd>/<PipelineName>-output/`**,
   i.e. wherever the driver's cwd happened to be. The drivers now run the
   pipelines with `cwd=WORK_ROOT`, and additionally archive each run's final
   `agg.txt` plus its sha256 under `OUT_ROOT/artefacts/` — that is the
   cross-arm artefact a reviewer compares. (Invoking a DAG script by hand, e.g.
   `python3 bench_pipen_dag.py`, still drops `<Pipeline>-output/` into the
   caller's cwd — run it from a scratch directory.)
4. **The archived workflow could not be replayed as-is**: the drivers wrote
   `pipen_records.json`, while the analysis stage expected
   `pipen_records_steps34.json` / `*_step5.json` / `smk_records_*` (the archived
   session renamed files between steps). `run_all.sh` now runs the arms in the
   documented order with matching filenames.
5. **RUNINFO default vs. the archived protocol**: the published timings were
   measured with pipen-runinfo *not installed*, and the plugin self-activates
   as soon as it is importable. `RUNINFO=0` therefore does not just skip
   checks — it passes `plugins=["-runinfo"]` to the pipelines (verified:
   0 runinfo files with the setting, 3 × 21 files without).

---

## 2. What changed

New files (all in `bench/`):

| file | purpose |
|---|---|
| `bench.env` | the **single** configuration file; every key has a sane default, each one commented with what an empty value means |
| `bench_config.py` | stdlib-only loader: defaults ← `bench.env` (or `bench.local.env`, or `$BENCH_ENV`) ← `BENCH_<KEY>` env overrides; path/int/bool/list accessors, `py`/`smk` resolution, module probing |
| `run_all.sh` | one command for the whole table: preflight → runinfo → environment → pipen caching arm → pipen scaling arm → snakemake arms → runinfo audit → summary → evidence → derived numbers → closing summary; tees everything to `<OUT_ROOT>/run_all.log` |
| `setup_env.sh` | creates the two virtualenvs anywhere (`venv/pipen`, `venv/snakemake` by default), installs the pinned specs from `bench.env`, writes `bench.local.env` with `PY`/`SMK` |
| `preflight.py` | PASS/FAIL checks (interpreter, pipen/pandas importable, harness files, writability) + filesystem warnings |
| `ensure_runinfo.py` | makes sure the pipeline interpreter can import pipen-runinfo (installs it if `RUNINFO_INSTALL=1`) |
| `check_runinfo.py` | lists every job directory's `job.runinfo.session`/`.device`/`.time`, counts them, prints one of each verbatim, writes `runinfo_check.json`; exits non-zero if `RUNINFO=1` and nothing was produced |
| `summarise_run.py` | closing summary: artefacts, per-N medians, cold/warm, invalidation phases, measurement-integrity cross-check, `agg.txt` sha256 comparison across arms |

Modified:

| file | change |
|---|---|
| `driver_pipen.py` | all paths/sizes from `bench_config`; markers on `WORK_ROOT` + archived copies; `cwd=WORK_ROOT`; `agg.txt` archive + sha256; `BENCH_PLUGINS` passthrough; writes `pipen_records_steps34.json`, `pipen_records_step5.json`, `pipen_cache_scope.json`, `pipen_run_meta.json`; records `runinfo_version`, `runinfo_enabled`, `rc_ok` |
| `driver_smk.py` | same config-driven treatment; snakemake executable from config (error message if unset); same marker/`agg.txt` archiving; writes `smk_records_steps34.json`, `smk_records_step5.json`, `smk_cache_scope.json` |
| `bench_pipen_dag.py`, `bench_cache_dag.py` | concurrency from `BENCH_FORKS`/`BN_FORKS` (default `os.cpu_count()`), `BENCH_PLUGINS`/`BN_PLUGINS` plugin control; no other behavioural change |
| `analyse_all.py` | config-driven; preferred arm files with legacy fallback; marker lookup across `OUT/markers`, `OUT`, `WORK/markers`; tolerant of absent arms (`missing_inputs`); correct `smk_*` labels; N=100 diagnostic entries now carry their archived provenance |
| `evidence.py` | config-driven; per-phase executed jobs now come from the scope records (the archived run's `phase_executed_jobs` were empty because the marker-file path clobbered them — a bug, not a number change); job/branch matching by index fixed; unavailable sections reported instead of raising |
| `make_report.py` | config-driven; `statistics.median` instead of `v[1]` (identical for the 3-rep archived protocol, valid for 1 rep); every section degrades to `null` + a `missing` list instead of aborting; optional copy to `ARCHIVE` |
| `env_json.py` | config-driven interpreter/checkout/disk paths; records `bench_config`, `snakemake_executable`, `pipen_runinfo_version`; `<not configured…>` instead of failing when `PIPEN_REPO` is empty |
| `hello_pipen.py` | default data file from `tempfile.gettempdir()` |
| `setup.sh`, `install_smk.sh` | banner pointing at `setup_env.sh`; kept verbatim as provenance (they still contain this machine's `$HOME/bench` paths, and are not part of the re-runnable path) |

Untouched: `bench/RESULTS.md`, `bench/raw/**` (0 files with a portability-date
mtime), `bench_common.py`, `analyse_marker.py`, the two `Snakefile`s (already
env-parameterised), and the legacy exploratory scripts listed in §1a.

---

## 3. Configuration

`bench/bench.env` (read by `bench_config.py` and `run_all.sh`; `bench.local.env`
written by `setup_env.sh` takes precedence over it; `BENCH_<KEY>` environment
variables beat both):

| key | default | meaning |
|---|---|---|
| `ROOT` | auto (harness dir) | where the drivers/Snakefiles live |
| `PY` | `sys.executable` | interpreter that has pipen (runs the pipelines) |
| `SMK` | first `snakemake` on PATH | snakemake executable for the comparison arms |
| `OUT_ROOT` | `<ROOT>/out` | records, logs, markers, summaries; `run_all.sh <dir>` sets it |
| `WORK_ROOT` | `<OUT_ROOT>/work` | pipeline workdirs, inputs, marker logs — **must be local disk** |
| `NPROC` | `os.cpu_count()` | concurrency of the "max cores" arms |
| `REPS` | `3` | repeats per scaling point (the archived protocol) |
| `SCALING_NS` | `1,10,100,500` | N values of the scaling arm |
| `CONC_N`, `CONC_FORKS` | `20`, `1,2,4,MAX` | concurrency arm (`MAX` = `NPROC`) |
| `CACHE_SCOPE_N`, `CACHE_TIMING_N`, `CACHE_TIMING_REPS` | `8`, `100`, `1` | caching arm sizes |
| `SLEEP` | `0.05` | useful work per job |
| `RUNINFO`, `RUNINFO_INSTALL` | `1`, `1` | per-job `job.runinfo.*` provenance and permission to install the plugin |
| `BASE_PYTHON`, `PIPEN_INSTALL`, `PIPEN_RUNINFO_PKG`, `SMK_INSTALL` | `python3`, `pipen==1.2.3`, `pipen-runinfo`, `snakemake==9.27.0` | only used by `setup_env.sh` |
| `PIPEN_REPO`, `ARCHIVE`, `LOGLEVEL` | empty, empty, `info` | optional git metadata, optional extra copy destination, pipen log level |

No key is required: the harness runs with the defaults on any Linux/WSL box that
has `bash`, `python3`, and the two tools' virtualenvs.

---

## 4. What a reviewer runs

```bash
# 0. one-time: create the two virtualenvs (anywhere; defaults to $HARNESS/venv/*)
bash bench/setup_env.sh                  # or: bash setup_env.sh /data/venv/pipen /data/venv/smk
                                         # writes bench/bench.local.env with PY= and SMK=

# 1. the whole table, one command (defaults = the archived protocol: REPS=3,
#    N ∈ {1,10,100,500}, forks {1,2,4,MAX}, caching N=8/N=100)
bash bench/run_all.sh /data/bench-out
```

Reduced-size variant (what the portability verification used, ≈3.5 min here):

```bash
BENCH_NPROC=8 BENCH_REPS=1 BENCH_SCALING_NS=20 BENCH_CONC_FORKS=1,2 \
BENCH_CACHE_SCOPE_N=8 BENCH_CACHE_TIMING_N=20 BENCH_CACHE_TIMING_REPS=1 \
BENCH_WORK_ROOT=/data/bench-work \
  bash bench/run_all.sh /data/bench-out-reduced
```

Expected runtime (measured, 32-core WSL2 box, `NPROC=8`, reduced settings):
preflight/runinfo/environment ≈ 4 s · pipen caching arm 61 s · pipen scaling arm
119 s (dominated by the `forks=1` N=20 point at ~62 s) · snakemake arms 13 s ·
analysis ≈ 1 s → **197 s total** (`bench_portability/run_logs/01_run_all_reduced.log`).
First-time virtualenv creation adds ≈ 40 s (pipen side) + ≈ 20 s (snakemake side)
— `bench_portability/run_logs/00_setup_env.log`. The full-size protocol is
≈18 min of pipeline runs by the archived run's own accounting
(`bench/RESULTS.md`, caveat 10) plus ≈1 min of analysis.

### What to compare

1. **`agg.txt` content, byte for byte.** Each run archives
   `OUT_ROOT/artefacts/agg_<tool>_<tag>.txt` plus the sha256 in the records JSON,
   and the closing summary prints the cross-arm comparison. Both frameworks must
   produce identical bytes for the same N (archived claim: "agg.txt
   byte-identical across arms").
2. **`job.runinfo.session` per job directory** (see §5.3 for the exact files and
   a verbatim example): interpreter, shell and package versions of the job that
   actually ran, plus `job.runinfo.device` (host/CPU/mem/disk/network/GPU) and
   `job.runinfo.time` (GNU `time -v` accounting: CPU %, max RSS, page faults).
3. **Job counts from the marker logs** — the run prints a per-arm integrity
   cross-check (marker lines vs. the DAG's expected count) and writes
   `OUT_ROOT/integrity_check.json`. Any `LOW` flag means the marker filesystem
   dropped lines; move `WORK_ROOT` to local disk and re-run.
4. **`OUT_ROOT/derived_numbers.json`** (and `summary.json`) against
   `bench/raw/derived_numbers.json` for the full-size protocol. `missing_inputs`
   lists what a reduced run legitimately does not have.

---

## 5. Verification that was actually performed

### 5.1 Clean environment, different path

`bash bench/setup_env.sh ~/ws_bench/.venv ~/ws_bench/smk-venv` created fresh
virtualenvs at **`/home/pwwang/ws_bench/.venv`** and
**`/home/pwwang/ws_bench/smk-venv`** (the archived run used `~/bench/.venv` and
`~/bench/smk`), installing `pipen==1.2.3`, `pandas`, `pipen-runinfo` and
`snakemake==9.27.0` from PyPI with no index fallback and no `--trusted-host`:
verbatim log `bench_portability/run_logs/00_setup_env.log`; versions printed at
the end of it — `pipen 1.2.3 | pandas 3.0.6`, `pipen-runinfo 1.1.5`,
`snakemake 9.27.0`.

### 5.2 Reduced-size end-to-end run from the clean venvs

Command (verbatim, `bench_portability/run_cleanenv_reduced.sh`):

```bash
BENCH_NPROC=8 BENCH_REPS=1 BENCH_SCALING_NS=20 BENCH_CONC_FORKS=1,2 \
BENCH_CACHE_SCOPE_N=8 BENCH_CACHE_TIMING_N=20 BENCH_CACHE_TIMING_REPS=1 \
BENCH_WORK_ROOT=/home/pwwang/ws_bench/work \
  bash bench/run_all.sh /mnt/f/E/hermes-workspace/pipen/bench_portability/out_clean_run
```

Result: `RUN_ALL_RC=0`, total 197 s. Verbatim console output:
`bench_portability/out_clean_run/run_all.log` (43 KB) and
`bench_portability/run_logs/01_run_all_reduced.log`. Selected lines:

```
[s5] r1_cold wall=9.066 jobs=25 {'Read': 8, 'Mid': 8, 'Side': 8, 'Agg': 1}
[s5] r2_rerun wall=0.963 jobs=0 {}
[s5] r3_input3_changed wall=8.947 jobs=4 {'Read': 1, 'Mid': 1, 'Side': 1, 'Agg': 1}
[s5] r4_mid_script_changed wall=5.092 jobs=9 {'Mid': 8, 'Agg': 1}
[s5] r5_rerun wall=1.063 jobs=0 {}
[s5t] cold wall=27.392 jobs=61 ; warm1 wall=0.917 jobs=0 ; warm2 wall=0.969 jobs=0
[s3] s3_n20_r1 wall=12.868 run=12.418 jobs=42 rss=266.7MB
[s4] s4_n20_f1_r1 wall=61.926 jobs=42 ; s4_n20_f2_r1 wall=31.806 jobs=42
[smk s3] smk_s3_n20_r1 wall=1.78 jobs=42 ; [smk s4] c1 2.744 / c2 2.15
# integrity: 10/10 arms match their expected marker-line count
N=20    pipen=9cfbaaab688df1c3...  snakemake=9cfbaaab688df1c3...  IDENTICAL
```

These are **reduced-run observations at N=20/forks∈{1,2}/NPROC=8, one rep**;
they are consistent in direction with the published full-size numbers but are
not the published numbers and were not compared to them numerically here.

### 5.3 pipen-runinfo: self-describing job directories

`RUNINFO=1` (default) installed and used pipen-runinfo 1.1.5. From
`check_runinfo.py` in the run (`runinfo_check.json`), and a scoped re-check of
the caching-scope workdir (`runinfo_check_scope.json`, evidence
`bench_portability/evidence/runinfo_files.txt`):

```
job dirs found            : 25
with session+device+time  : 25
with at least one runinfo : 25   (cache-DAG workdir; 75 files = 25 x 3)
job.runinfo.session: 25   job.runinfo.device: 25   job.runinfo.time: 25
```

One job's three files, verbatim (`wd_s5_scope/CachePipeline/Read/4/`, sizes
363 B / 398 B / 6955 B):

```
# job.runinfo.session                      # job.runinfo.time
# Generated by pipen_runinfo v1.1.5        # Generated by pipen-runinfo v1.1.5
# Lang: bash                               Command: bash …/Read/4/job.script
SHELL          /usr/bin/fish               Voluntary context switches: 20
BASH_VERSION   5.2.21(1)-release           Involuntary context switches: 0
BASH_ARGV0     …/Read/4/job.script         Percentage of CPU this job got: 125%
BASH_SOURCE    …/Read/4/job.script         Major page faults: 0
proc-exe       /usr/bin/bash               Minor page faults: 1176
proc-exe-version GNU bash, 5.2.21…         Maximum resident set size (kB): 3496
                                           Elapsed real time (s): 0.00 / Exit status: 0
```

Notes for a reviewer: for the bash-language jobs these DAGs use, the session file
records the shell (`BASH_VERSION`, `proc-exe`/`proc-exe-version`) rather than a
Python interpreter — `SHELL` is just the login-shell environment variable. The
device file carries Scheduler / Hostname / CPU / Memory / Disk / Network / GPU
sections; `job.runinfo.time` needs GNU `time` and says so in the file if it is
missing. Cached jobs are not re-executed, so their job directories keep the
runinfo files of the execution that produced them.

### 5.4 Analysis replay from the archived records (no re-measurement)

Copying the archived `bench/raw/*.json` + `bench/raw/markers/` into a fresh
output root and running `analyse_all.py` + `make_report.py` with
`WORK_ROOT=~/bench` (the archived workdirs) reproduces the published derived
numbers **exactly** — log `bench_portability/run_logs/03_archive_replay.log`:
pipen N=500 wall median 55.036 (published 55.036), Snakemake 7.284 (7.284),
overhead/job 0.1085 vs 0.0130, ratio 7.56×, pipen caching cold 40.287 s → warm
3.107 s = 12.97× (all `same`), observed job-start rates 9.1/s and 108.6/s
(`same`). `bench/raw/` was written to only through *copies* in
`bench_portability/out_archive_replay/`.

---

### 5.5 CLI/config contract checks

`evidence/check_cli_contract.sh` → `evidence/cli_contract.out`: `run_all.sh`
without an argument prints usage and exits 64; `BENCH_NPROC=3 BENCH_SCALING_NS=5
BENCH_RUNINFO=0` are all honoured; `BENCH_ENV=/tmp/alt_bench.env` switches the
config file; and `plugins=["-runinfo"]` produces 0 runinfo files for a 3-job DAG
while the default produces 9 (3 jobs × 3 files).

---

## 6. What still assumes this machine / is not proven

1. **Platform: Linux only, in practice WSL2.** `bench_common.py`,
   `driver_pipen.py` and `preflight.py` read `/proc` (job/process RSS tree
   sampling, `/proc/loadavg`, `/proc/mounts`); `bench_cache_dag.py` uses bash
   process substitution semantics in job scripts; the marker and shell snippets
   are POSIX bash. Nothing was tested outside Ubuntu 24.04 under WSL2.
2. **`bench/bench.local.env`** (written by `setup_env.sh` on this box) points at
   `/home/pwwang/ws_bench/.venv` and `/home/pwwang/ws_bench/smk-venv`. It is
   machine-local scratch and must **not** be archived; delete it and the harness
   falls back to `bench.env` + PATH.
3. **Version source differs from the archived run.** The archived numbers came
   from an *editable install of a checkout*
   (`~/github/pipen`, commit `6ffb10a…`, `git describe 1.2.2-3-g6ffb10a`,
   version string 1.2.3). The portable default installs the **released**
   `pipen==1.2.3` from PyPI. For an exact re-measurement set
   `PIPEN_INSTALL="-e /path/to/pipen"` and `PIPEN_REPO=/path/to/pipen` (the
   latter only fills the git fields of `environment.json`).
4. **runinfo perturbs the timings, and by how much is unresolved here.** Two
   3-rep A/B rounds at N=20/forks=8 gave +2.024 s (≈+17 %, round 1) and +0.029 s
   (≈+0.2 %, round 2) median difference between plugin-off and plugin-on
   (`run_logs/02_runinfo_ab.log`, `evidence/ab_runinfo_round1_quoted.txt`). The
   between-round spread exceeds the effect, so **no claim is made** about the
   plugin's timing cost; the archived numbers were measured plugin-free, and
   `RUNINFO=0` reproduces that protocol (it really disables the plugin).
5. **Absolute times are load-dependent.** The archived run documented 4
   CPU-burning sibling processes and `loadavg` 4.4–7.0 on 32 cores; the
   portability runs saw `loadavg` 2–9. Ratios are more robust than absolutes,
   and a reviewer should record `loadavg_before/after` (already in every record).
6. **Two analysis inputs remain quoted from the archived run**: the N=100
   single-rep diagnostic pair in `analyse_all.py`, now labelled with
   `measured_in: "archived full-size run"`, and the untouched legacy scripts in
   §1a. Neither is re-measured by `run_all.sh`.
7. **Not attempted here:** the full-size (N=500) run, the `touch`-vs-content
   experiment driver (`touch_test2.py`), and Nextflow. The reduced run exercises
   the same code paths, not the same sizes.
8. `WORK_ROOT` and `OUT_ROOT` are forced to exist by `run_all.sh`; a read-only
   archive directory cannot be used as `OUT_ROOT` (use `ARCHIVE=` to copy
   results elsewhere instead).

---

## 7. Evidence file map (`bench_portability/`)

```
PORTABILITY.md                            this document
orig/{driver_pipen,driver_smk,analyse_all,evidence,make_report,env_json}.py
                                          pre-change copies for diffing
evidence/inventory_before.txt             grep of every path/machine assumption before
evidence/diag_marker.{sh,out}             9p-vs-ext4 marker-line-loss measurement
evidence/probe_plugins.{sh,out}           RUNINFO=0 really disables the plugin
evidence/diag_runinfo_scope.sh            regenerates the runinfo inventory
evidence/runinfo_files.txt                job.runinfo.* listing + verbatim samples
evidence/ab_runinfo_round1_quoted.txt     first A/B round (the script was since fixed)
evidence/check_cli_contract.{sh,out}      CLI/config contract checks (usage, overrides, plugin off)
run_logs/00_setup_env.log                 clean-venv creation, verbatim
run_logs/01_run_all_reduced.log           reduced clean-env run, verbatim console
run_logs/02_runinfo_ab.log                runinfo on/off A/B, round 2
run_logs/03_archive_replay.log            archived records replayed through the analysis
run_cleanenv_reduced.sh                   the verification command
run_runinfo_ab.sh                         the A/B command
run_archive_replay.sh                     the replay command
out_clean_run/                            artefacts of the reduced clean-env run
    run_all.log, summary.json, derived_numbers.json, integrity_check.json,
    evidence_caching.json, environment.json, runinfo_check.json,
    runinfo_check_scope.json (scoped re-check), pipen_records_*.json,
    smk_records_*.json, *_cache_scope.json, pipen_run_meta.json,
    artefacts/agg_*.txt, logs/, logs_smk/, markers/ (archived copies)
out_archive_replay/                       analysis-only replay of the archived records
```

Running the harness regenerates `bench/__pycache__` (Python bytecode for
`bench_config.py`/`bench_common.py`) and `bench.local.env` (`setup_env.sh`); both
are local scratch, neither is part of the archived materials.
