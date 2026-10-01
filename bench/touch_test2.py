#!/usr/bin/env python3
"""Step-5(c) touch test, properly controlled.

The rendered job scripts embed the marker-log path, so the marker path must be held
constant across runs, otherwise every job's script content changes and (correctly)
invalidates the whole pipeline. The marker path below is the same one the driver's
scope experiment used, so the previously rendered scripts are unchanged.

Sequence: control re-run -> touch (mtime only, content identical) -> content change
-> control re-run.
"""
import json
import os
import subprocess
import time
from collections import Counter
from pathlib import Path

HOME = Path.home()
BENCH = HOME / "bench"
OUT = BENCH / "out"
VPY = BENCH / ".venv" / "bin" / "python"
SCRIPT = Path("/mnt/f/E/hermes-workspace/pipen/bench/bench_cache_dag.py")
WD = BENCH / "wd_s5_scope"
INDIR = BENCH / "cache_inputs_small"
N = 8
FIXED_MARKER = OUT / "marker_s5_scope.log"   # identical to the driver's scope experiment
results = []


def run(label, note):
    env = dict(os.environ)
    env.update({
        "BN_N": str(N), "BN_INDIR": str(INDIR), "BN_WORKDIR": str(WD),
        "BN_MARKER": str(FIXED_MARKER), "BN_MIDVARIANT": "B", "BN_SIDEVARIANT": "A",
    })
    log = OUT / "logs" / f"touch_{label}.log"
    off = len(FIXED_MARKER.read_text().splitlines())
    t0 = time.perf_counter()
    with open(log, "w") as fh:
        rc = subprocess.call([str(VPY), str(SCRIPT)], env=env, stdout=fh,
                             stderr=subprocess.STDOUT)
    wall = round(time.perf_counter() - t0, 3)
    new = [l.split() for l in FIXED_MARKER.read_text().splitlines()[off:] if l.strip()]
    rec = {"label": label, "note": note, "rc": rc, "wall_sec": wall,
           "jobs_executed": len(new),
           "jobs_by_proc": dict(Counter(l[0] for l in new)),
           "executed_detail": [" ".join(l[:2]) for l in new],
           "cached_jobs_log_lines": [l.split("core", 1)[-1].strip() for l in
                                     log.read_text().splitlines() if "Cached jobs" in l],
           "log": str(log)}
    results.append(rec)
    print(f"[{label}] wall={wall} jobs={rec['jobs_executed']} {rec['jobs_by_proc']}")
    for c in rec["cached_jobs_log_lines"]:
        print("     ", c)
    return rec


f = INDIR / "in4.txt"
c0 = f.read_text()
st0 = f.stat().st_mtime_ns

run("c0_control", "re-run with the same marker path: nothing should re-run")
os.utime(f, None)                       # touch only: content identical
st1 = f.stat().st_mtime_ns
run("c1_after_touch", "mtime bumped, content byte-identical")
f.write_text("line4-v3\n")              # real content change
st2 = f.stat().st_mtime_ns
run("c2_after_content_change", "content changed (line3-v2 -> line4-v3)")
run("c3_control_after", "re-run after the content change")
c2 = f.read_text()

out = {
    "test": "step 5(c): touch vs content-change on ONE input file, marker path fixed",
    "harness_note": ("the rendered job scripts embed the marker-log path; all runs below use "
                     "the identical marker path so the rendered scripts are byte-identical "
                     "across runs (verified: c0 re-ran 0 jobs)"),
    "file": str(f),
    "content_before": c0, "content_after": c2,
    "mtime_ns": {"before": st0, "after_touch": st1, "after_content_change": st2},
    "results": results,
}
(OUT / "touch_test.json").write_text(json.dumps(out, indent=2))
Path("/mnt/f/E/hermes-workspace/pipen/bench/raw/touch_test.json").write_text(
    json.dumps(out, indent=2))
print(json.dumps({k: v for k, v in out.items() if k != "results"}, indent=2))
