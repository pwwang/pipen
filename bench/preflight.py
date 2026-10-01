#!/usr/bin/env python3
"""Preflight for run_all.sh: check the configured environment before timing anything.

Prints one PASS/FAIL line per requirement and exits non-zero if any hard
requirement is unmet.  A missing Snakemake is only a warning (the snakemake arms
are then skipped); a pipeline interpreter without pipen/pandas is fatal.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_config import load  # noqa: E402

cfg = load()
fail = 0
degraded = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    print(("PASS  " if ok else "FAIL  ") + label + (f"   [{detail}]" if detail else ""))
    if not ok:
        fail += 1


print(cfg.describe())
print()

py = cfg.py
check(Path(py).exists(), f"pipeline interpreter exists: {py}")
check(cfg.python_has("pipen"), "pipen importable by the pipeline interpreter")
check(cfg.python_has("pandas"), "pandas importable by the pipeline interpreter")
if cfg.smk:
    check(Path(cfg.smk).exists() or bool(cfg.smk), f"snakemake executable: {cfg.smk}")
else:
    print("WARN  no snakemake executable configured (SMK empty in the config): "
          "the snakemake arms will be SKIPPED.  Set SMK=/path/to/snakemake or "
          "run setup_env.sh.")
for name in ("bench_pipen_dag.py", "bench_cache_dag.py", "smk_dag/Snakefile",
             "smk_cache/Snakefile", "analyse_marker.py", "driver_pipen.py",
             "driver_smk.py"):
    check((cfg.root / name).exists(), f"harness file present: {name}")
check(Path(cfg.path("out_root")).is_dir(), f"OUT_ROOT exists: {cfg.path('out_root')}")
check(Path(cfg.path("work_root")).is_dir(), f"WORK_ROOT exists: {cfg.path('work_root')}")
for key in ("out_root", "work_root"):
    p = cfg.path(key)
    try:
        probe = p / ".bench_write_probe"
        probe.write_text("ok")
        probe.unlink()
        writable = True
    except Exception:
        writable = False
    check(writable, f"{key} writable: {p}")

print()
print(f"INFO  NPROC={cfg.nproc}  REPS={cfg.int('reps')}  SCALING_NS={cfg.list('scaling_ns')}")
print(f"INFO  CONC_N={cfg.int('conc_n')}  CONC_FORKS={cfg.list('conc_forks')}  "
      f"CACHE_SCOPE_N={cfg.int('cache_scope_n')}  CACHE_TIMING_N={cfg.int('cache_timing_n')}  "
      f"CACHE_TIMING_REPS={cfg.int('cache_timing_reps')}  SLEEP={cfg.raw('sleep')}")
print(f"INFO  RUNINFO={int(cfg.bool('runinfo'))} (job.runinfo.session/device/time per job "
      f"via pipen-runinfo)")
print(f"INFO  expect ~{cfg.int('cache_timing_n') * 3 + 1} jobs in the cold caching run, "
      f"{cfg.int('cache_scope_n') * 3 + 1} in the scope run")

# --- filesystem sanity ------------------------------------------------------
# The per-job marker logs are the job-count measurement and are appended to
# concurrently by every job process.  That is only reliable on a local
# filesystem: measured on this box, the same N=20 run lost 13 of 42 marker lines
# when the markers lived on a 9p mount (/mnt/f) and lost none on ext4.
NETWORK_FS = ("9p", "cifs", "smb3", "nfs", "nfs4", "fuse.sshfs", "virtiofs", "drvfs")


def fs_type(path: Path) -> str:
    try:
        best, best_len = None, -1
        for line in Path("/proc/mounts").read_text().splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            mp = parts[1].replace("\\040", " ")
            if str(path).startswith(mp) and len(mp) > best_len:
                best, best_len = parts[2], len(mp)
        return best or "?"
    except Exception:
        return "?"


for key in ("work_root", "out_root"):
    p = cfg.path(key)
    fstype = fs_type(p)
    if fstype in NETWORK_FS:
        if key == "work_root":
            print(f"WARN  {key} is on a {fstype} mount ({p}): concurrent per-job marker "
                  f"appends can lose lines there.  Point WORK_ROOT at a local disk for "
                  f"a valid measurement.")
            degraded += 1
        else:
            print(f"INFO  {key} is on a {fstype} mount ({p}): fine for archived "
                  f"artefacts, but keep WORK_ROOT local (timings and markers are "
                  f"written there).")
    else:
        print(f"INFO  {key} filesystem: {fstype} ({p})")

if degraded:
    print(f"\nINFO  {degraded} measurement-integrity warning(s) above (see WARN lines).")

if fail:
    print(f"\nPREFLIGHT FAILED ({fail} requirement(s)).  Fix the config in {cfg.source} "
          f"or run setup_env.sh, then re-run.")
sys.exit(1 if fail else 0)
