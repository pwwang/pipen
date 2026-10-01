#!/usr/bin/env bash
# Evidence: exact job.runinfo.* inventory of the reduced clean run's OWN workdir.
# (The caching-scope workdir persists after the run; the scaling/concurrency
# workdirs are deleted after each rep by design, so their job dirs no longer
# exist - the run's own check_runinfo.py step covered them while they were live.)
set -uo pipefail
OUT=/mnt/f/E/hermes-workspace/pipen/bench_portability/out_clean_run
SCOPE=/home/pwwang/ws_bench/work/wd_s5_scope
PY=/home/pwwang/ws_bench/.venv/bin/python
echo "# job.runinfo.* files under the caching-scope workdir"
echo "#   $SCOPE"
find "$SCOPE" -name 'job.runinfo.*' | wc -l | sed 's/^/  total job.runinfo.* files: /'
for k in session device time; do
  echo "  job.runinfo.$k: $(find "$SCOPE" -name "job.runinfo.$k" | wc -l) files"
done
echo "  job directories (job.script): $(find "$SCOPE" -name job.script | wc -l)"
echo
echo "# the first 8 such files, verbatim listing"
find "$SCOPE" -name 'job.runinfo.*' | sort | head -8 | sed 's/^/  /'
echo
echo "# scoped re-check: check_runinfo.py on that single workdir"
echo "  (writes runinfo_check_scope.json; the run's own report stays at runinfo_check.json)"
BENCH_OUT_ROOT="$OUT" "$PY" /mnt/f/E/hermes-workspace/pipen/bench/check_runinfo.py "$SCOPE" \
  "--out=$OUT/runinfo_check_scope.json" 2>&1 | sed -n '1,10p'
echo
echo "# the three files of one job (Read/4), with sizes"
ls -l "$SCOPE/CachePipeline/Read/4/" | grep runinfo
echo
echo "# job.runinfo.session (verbatim)"
cat "$SCOPE/CachePipeline/Read/4/job.runinfo.session"
echo
echo "# job.runinfo.time (verbatim)"
cat "$SCOPE/CachePipeline/Read/4/job.runinfo.time"
echo
echo "# job.runinfo.device: sections it contains, then the first 8 lines"
grep -n '^[A-Za-z][A-Za-z ]*$' "$SCOPE/CachePipeline/Read/4/job.runinfo.device" | head -12
head -8 "$SCOPE/CachePipeline/Read/4/job.runinfo.device"
