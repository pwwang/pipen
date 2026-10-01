#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# A/B: what does enabling pipen-runinfo cost per job?
#
# The published (archived) numbers were measured with pipen-runinfo NOT
# installed.  The portable harness turns it ON by default so that every job
# directory is self-describing.  This script quantifies the difference on the
# same DAG, same N, same forks, same local filesystem, alternating the two
# settings so a drifting machine load hits both equally.
#
#   DAG        : bench_pipen_dag.py (N=20 shards -> 1 aggregation job)
#   forks      : 8          cache: off         sleep/job: 0.05s
#   reps       : 3 per setting, alternating on/off/on/off/on/off
#
# Output: bench_portability/run_logs/02_runinfo_ab.log (this script's stdout)
# ---------------------------------------------------------------------------
set -uo pipefail

BENCH=/mnt/f/E/hermes-workspace/pipen/bench
PORT=/mnt/f/E/hermes-workspace/pipen/bench_portability
PY=/home/pwwang/ws_bench/.venv/bin/python          # clean venv (has pipen-runinfo)
W=/home/pwwang/ws_bench/ab_work
REPS=3

mkdir -p "$W"
# Run the DAG from a scratch cwd: pipen exports <Pipeline>-output/ into the
# pipeline's cwd (the drivers set it to WORK_ROOT; a direct run uses $W so the
# harness directory stays clean).
cd "$W"
export BENCH_DAG="$BENCH/bench_pipen_dag.py"

echo "# A/B: pipen-runinfo ON (default of the portable harness) vs OFF (archived protocol)"
echo "# interpreter: $PY"
"$PY" -c "import importlib.metadata as m; print('# pipen-runinfo installed:', m.version('pipen-runinfo'))"
echo

for rep in $(seq 1 "$REPS"); do
  for mode in off on; do
    wd="$W/wd_${mode}_r${rep}"
    marker="$W/marker_${mode}_r${rep}.log"
    rm -rf "$wd"
    : > "$marker"
    if [ "$mode" = off ]; then plugins="-runinfo"; else plugins=""; fi
    out="$("$PY" - "$wd" "$marker" "$plugins" <<'PY'
import os, subprocess, sys, time
wd, marker, plugins = sys.argv[1], sys.argv[2], sys.argv[3]
env = dict(os.environ)
env.update({
    "BENCH_N": "20", "BENCH_FORKS": "8", "BENCH_SLEEP": "0.05",
    "BENCH_CACHE": "0", "BENCH_WORKDIR": wd, "BENCH_MARKER": marker,
})
if plugins:
    env["BENCH_PLUGINS"] = plugins
t0 = time.perf_counter()
proc = subprocess.run([sys.executable, os.environ["BENCH_DAG"]], env=env,
                      capture_output=True, text=True)
wall = time.perf_counter() - t0
lines = [l for l in open(marker) if l.strip()]
print(f"rc={proc.returncode} wall={wall:.3f} marker_lines={len(lines)}")
PY
)"
    echo "runinfo=$mode rep=$rep  $out"
    # count runinfo files produced by this run
    nfiles=$(find "$wd" -name 'job.runinfo.session' | wc -l)
    echo "                    job.runinfo.session files in this workdir: $nfiles"
  done
done
echo
echo "# raw workdirs kept for inspection: $W"
