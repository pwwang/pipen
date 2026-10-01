#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_all.sh - the whole pipen benchmark table in one command.
#
#   bash run_all.sh <output-root>              # everything from bench.env
#
#   # reduced-size run (this is the shape the portability verification used):
#   BENCH_NPROC=4 BENCH_REPS=1 BENCH_SCALING_NS=20 BENCH_CONC_FORKS=1,2 \
#   BENCH_CACHE_SCOPE_N=8 BENCH_CACHE_TIMING_N=20 BENCH_CACHE_TIMING_REPS=1 \
#   BENCH_WORK_ROOT=/tmp/bench-work \
#     bash run_all.sh /tmp/bench-out
#
# Steps (caching arm first, then the scaling arm, then snakemake, then the
# analysis that consumes the arms' records):
#   0  config + preflight            bench_config.py, preflight.py
#   1  pipen-runinfo availability    ensure_runinfo.py    (self-describing jobs)
#   2  environment provenance        env_json.py          -> environment.json
#   3  pipen caching arm             driver_pipen.py 5    -> pipen_records_step5.json,
#                                                            pipen_cache_scope.json
#   4  pipen scaling arm             driver_pipen.py 34   -> pipen_records_steps34.json
#   5  snakemake arms                driver_smk.py 345    -> smk_records_steps34.json,
#                                                            smk_records_step5.json,
#                                                            smk_cache_scope.json
#   6  job.runinfo audit             check_runinfo.py     -> runinfo_check.json
#   7  summary                       analyse_all.py       -> summary.json
#   8  per-job evidence              evidence.py          -> evidence_caching.json
#   9  derived numbers               make_report.py       -> derived_numbers.json
#  10  closing summary               summarise_run.py
#
# The full console transcript is appended to <output-root>/run_all.log.
# Configuration lives in exactly one place: bench.env (see bench_config.py),
# overridable per key with BENCH_<KEY>=... environment variables.  Nothing in
# this script or in the drivers is machine specific.
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_ARG="${1:-}"
if [ -z "$OUT_ARG" ]; then
  echo "usage: bash $0 <output-root>" >&2
  echo "  e.g. bash $0 /tmp/bench-out" >&2
  exit 64
fi
# The argument is the output root; it wins over the config file (BENCH_* env wins over both).
export BENCH_OUT_ROOT="$OUT_ARG"
PYBIN="${BENCH_PY:-${PY:-python3}}"

# --- resolve the configuration through the single Python entry point --------
eval "$(PYTHONPATH="$HERE" "$PYBIN" - <<'PY'
import shlex
from bench_config import load
cfg = load()
for key, value in cfg.as_dict().items():
    print(f"BENCH_CFG_{key.upper()}={shlex.quote(str(value))}")
PY
)"

OUT_ROOT="$BENCH_CFG_OUT_ROOT"
WORK_ROOT="$BENCH_CFG_WORK_ROOT"
mkdir -p "$OUT_ROOT" "$WORK_ROOT"
LOG="$OUT_ROOT/run_all.log"

step () {
  local label="$1"; shift
  {
    echo
    echo "############################################################################"
    echo "### STEP: $label"
    echo "### cmd : $*"
    echo "### when: $(date -Is)"
    echo "############################################################################"
  } | tee -a "$LOG"
  "$@" 2>&1 | tee -a "$LOG"
}

echo "### run_all.sh: harness=$HERE" | tee -a "$LOG"
echo "### run_all.sh: config=$BENCH_CFG_SOURCE" | tee -a "$LOG"
echo "### run_all.sh: OUT_ROOT=$OUT_ROOT" | tee -a "$LOG"
echo "### run_all.sh: WORK_ROOT=$WORK_ROOT" | tee -a "$LOG"
echo "### run_all.sh: PY=$BENCH_CFG_PY" | tee -a "$LOG"
echo "### run_all.sh: SMK=${BENCH_CFG_SMK:-<none: snakemake arms will be skipped>}" | tee -a "$LOG"

step "0/10 preflight (config + interpreter + harness files)" "$PYBIN" "$HERE/preflight.py"
step "1/10 pipen-runinfo availability" "$PYBIN" "$HERE/ensure_runinfo.py"
step "2/10 environment provenance" "$PYBIN" "$HERE/env_json.py"
step "3/10 pipen caching arm" "$PYBIN" "$HERE/driver_pipen.py" 5
step "4/10 pipen scaling arm" "$PYBIN" "$HERE/driver_pipen.py" 34
if [ -n "$BENCH_CFG_SMK" ]; then
  step "5/10 snakemake arms" "$PYBIN" "$HERE/driver_smk.py" 345
else
  echo "### SKIP snakemake arms: SMK is empty in the resolved configuration" | tee -a "$LOG"
fi
step "6/10 job.runinfo audit (self-describing job dirs)" "$PYBIN" "$HERE/check_runinfo.py"
step "7/10 summary" "$PYBIN" "$HERE/analyse_all.py"
step "8/10 per-job evidence" "$PYBIN" "$HERE/evidence.py"
step "9/10 derived numbers" "$PYBIN" "$HERE/make_report.py"
step "10/10 closing summary" "$PYBIN" "$HERE/summarise_run.py"

echo | tee -a "$LOG"
echo "### run_all.sh finished OK ($(date -Is))" | tee -a "$LOG"
echo "### artefacts: $OUT_ROOT   transcript: $LOG" | tee -a "$LOG"
