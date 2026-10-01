#!/usr/bin/env bash
# CLI contract checks for the portable harness (no benchmark is run).
set -uo pipefail
BENCH=/mnt/f/E/hermes-workspace/pipen/bench
PY=/home/pwwang/ws_bench/.venv/bin/python
cd "$BENCH"

echo "=== 1. run_all.sh without an argument (expect usage + rc 64) ==="
bash run_all.sh; echo "rc=$?"
echo
echo "=== 2. per-key BENCH_* overrides are honoured (expect NPROC=3, SCALING_NS=5) ==="
BENCH_NPROC=3 BENCH_SCALING_NS=5 BENCH_RUNINFO=0 "$PY" bench_config.py | grep -E '^(NPROC|SCALING_NS|RUNINFO|SOURCE|PY|SMK) '
echo
echo "=== 3. a config file can be overridden by pointing BENCH_ENV elsewhere ==="
printf 'SCALING_NS=42\nCACHE_TIMING_N=77\n' > /tmp/alt_bench.env
BENCH_ENV=/tmp/alt_bench.env "$PY" bench_config.py | grep -E '^(SCALING_NS|CACHE_TIMING_N|SOURCE) '
echo
echo "=== 4. RUNINFO=0 really disables the plugin (a 3-job DAG, then look for runinfo files) ==="
rm -rf /tmp/pluginoff_wd /tmp/pluginoff_marker.log; : > /tmp/pluginoff_marker.log
BENCH_N=2 BENCH_FORKS=2 BENCH_SLEEP=0.01 BENCH_CACHE=0 BENCH_WORKDIR=/tmp/pluginoff_wd \
  BENCH_MARKER=/tmp/pluginoff_marker.log BENCH_PLUGINS=-runinfo "$PY" bench_pipen_dag.py > /tmp/pluginoff.log 2>&1
echo "rc=$?  runinfo files: $(find /tmp/pluginoff_wd -name 'job.runinfo.*' | wc -l)  (expect 0)"
rm -rf /tmp/pluginoff2_wd /tmp/pluginoff2_marker.log; : > /tmp/pluginoff2_marker.log
BENCH_N=2 BENCH_FORKS=2 BENCH_SLEEP=0.01 BENCH_CACHE=0 BENCH_WORKDIR=/tmp/pluginoff2_wd \
  BENCH_MARKER=/tmp/pluginoff2_marker.log "$PY" bench_pipen_dag.py > /tmp/pluginoff2.log 2>&1
echo "rc=$?  runinfo files: $(find /tmp/pluginoff2_wd -name 'job.runinfo.*' | wc -l)  (expect 9 = 3 jobs x 3 files)"
