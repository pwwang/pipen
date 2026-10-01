#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Archive replay (ANALYSIS ONLY - no benchmark is re-run).
#
# Points the analysis stage at COPIES of the archived raw records
# (bench/raw/*.json, bench/raw/markers/) and checks that the derived numbers
# come out the same as the published bench/raw/derived_numbers.json.
#
# bench/raw/ and bench/RESULTS.md are never written to: OUT_ROOT is a fresh
# directory under bench_portability/, and ARCHIVE is left empty.
# ---------------------------------------------------------------------------
set -uo pipefail

BENCH=/mnt/f/E/hermes-workspace/pipen/bench
PORT=/mnt/f/E/hermes-workspace/pipen/bench_portability
REPLAY="$PORT/out_archive_replay"
PY=/home/pwwang/ws_bench/.venv/bin/python
# the archived workdirs/inputs still live in the WSL home of the original run
ARCHIVED_WORK=/home/pwwang/bench

rm -rf "$REPLAY"
mkdir -p "$REPLAY/markers"
for f in pipen_records_steps34.json pipen_records_step5.json pipen_cache_scope.json \
         smk_records_steps34.json smk_records_step5.json smk_cache_scope.json \
         environment.json evidence_caching.json; do
  cp "$BENCH/raw/$f" "$REPLAY/$f"
done
cp "$BENCH"/raw/markers/*.log "$REPLAY/markers/" 2>/dev/null || echo "# (no raw/markers/*.log)"
echo "# replayed $(ls "$REPLAY" | wc -l) archived inputs into $REPLAY"
echo "# markers: $(ls "$REPLAY/markers" | wc -l) files"

export BENCH_OUT_ROOT="$REPLAY"
export BENCH_WORK_ROOT="$ARCHIVED_WORK"
export BENCH_ARCHIVE=""

echo
echo "=== analyse_all.py (archive replay) ==="
"$PY" "$BENCH/analyse_all.py" > "$REPLAY/analysis.log" 2>&1
echo "rc=$?  (log: $REPLAY/analysis.log)"
tail -3 "$REPLAY/analysis.log"

echo
echo "=== make_report.py (archive replay) ==="
"$PY" "$BENCH/make_report.py" > "$REPLAY/derived.log" 2>&1
echo "rc=$?  (log: $REPLAY/derived.log)"

echo
echo "=== published vs replayed (key numbers) ==="
"$PY" - "$BENCH/raw/derived_numbers.json" "$REPLAY/derived_numbers.json" <<'PY'
import json, sys
pub = json.load(open(sys.argv[1]))
rep = json.load(open(sys.argv[2]))
rows = [
    ("pipen scaling N=500 wall median", pub["pipen_scaling"][-1], rep["pipen_scaling"][-1]),
    ("smk   scaling N=500 wall median", pub["smk_scaling"][-1], rep["smk_scaling"][-1]),
]
for label, a, b in rows:
    for k in ("n", "wall_median", "overhead_per_job_median", "rss_median_mb", "jobs"):
        flag = "same" if a.get(k) == b.get(k) else "DIFF"
        print(f"  {flag:4} {label:34} {k:26} published={a.get(k)!r:>12}  replayed={b.get(k)!r}")
pt, rt = pub["pipen_caching_timing"], rep["pipen_caching_timing"]
for k in ("n", "total_jobs", "cold_run_jobs", "cold_wall_sec", "warm1_wall_sec",
          "speedup_cold_over_warm1"):
    flag = "same" if pt.get(k) == rt.get(k) else "DIFF"
    print(f"  {flag:4} {'pipen caching':34} {k:26} published={pt.get(k)!r:>12}  replayed={rt.get(k)!r}")
for k in ("ratio_pipen_over_smk", "pipen_overhead_per_job", "smk_overhead_per_job"):
    a, b = pub["head_to_head"][-1].get(k), rep["head_to_head"][-1].get(k)
    flag = "same" if a == b else "DIFF"
    print(f"  {flag:4} {'head-to-head N=500':34} {k:26} published={a!r:>12}  replayed={b!r}")
for lbl in ("pipen_s3_n500_r1", "smk_s3_n500_r1"):
    a = pub["observed_parallelism"].get(lbl, {})
    b = rep["observed_parallelism"].get(lbl, {})
    for k in ("jobs", "peak_concurrent_jobs", "job_start_rate_per_sec"):
        flag = "same" if a.get(k) == b.get(k) else "DIFF"
        print(f"  {flag:4} {lbl:34} {k:26} published={a.get(k)!r:>12}  replayed={b.get(k)!r}")
PY
