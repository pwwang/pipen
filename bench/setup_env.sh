#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup_env.sh - create the two virtualenvs the harness needs, from a clean
# machine, and record their locations in bench.local.env.
#
#   bash setup_env.sh [pipen-venv-dir] [snakemake-venv-dir]
#     defaults: <harness>/venv/pipen  and  <harness>/venv/snakemake
#
# What gets installed comes from bench.env (BASE_PYTHON, PIPEN_INSTALL,
# PIPEN_RUNINFO_PKG, SMK_INSTALL).  PIPEN_INSTALL defaults to pipen==1.2.3, the
# version the archived numbers were measured with; point it at a checkout
# ("-e /path/to/pipen") to benchmark a working tree instead.
#
# bench.local.env is machine-local and must NOT be archived; bench.env stays the
# portable, machine-independent configuration (see bench_config.py).
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPEN_VENV="${1:-$HERE/venv/pipen}"
SMK_VENV="${2:-$HERE/venv/snakemake}"

# Resolve the install specs through the single Python entry point.
BASE_PY="${BENCH_BASE_PYTHON:-python3}"
eval "$(PYTHONPATH="$HERE" "$BASE_PY" - <<'PY'
import shlex
from bench_config import load
cfg = load()
for src, dst in (("pipen_install", "BENCH_PIPEN_INSTALL"),
                 ("pipen_runinfo_pkg", "BENCH_RUNINFO_PKG"),
                 ("smk_install", "BENCH_SMK_INSTALL")):
    print(f"{dst}={shlex.quote(cfg.raw(src))}")
PY
)"

echo "### base interpreter : $BASE_PY ($($BASE_PY --version 2>&1))"
echo "### pipen venv       : $PIPEN_VENV"
echo "### snakemake venv   : $SMK_VENV"
echo "### pipen install    : $BENCH_PIPEN_INSTALL + pandas + $BENCH_RUNINFO_PKG"
echo "### snakemake install: $BENCH_SMK_INSTALL"

if [ ! -x "$PIPEN_VENV/bin/python" ]; then
  echo "### creating $PIPEN_VENV"
  "$BASE_PY" -m venv "$PIPEN_VENV"
fi
echo "### installing the pipen side (this downloads from PyPI)"
# shellcheck disable=SC2086  # the spec may legitimately be several words ("-e /path")
"$PIPEN_VENV/bin/python" -m pip install $BENCH_PIPEN_INSTALL pandas "$BENCH_RUNINFO_PKG"

if [ ! -x "$SMK_VENV/bin/snakemake" ]; then
  echo "### creating $SMK_VENV"
  "$BASE_PY" -m venv "$SMK_VENV"
fi
echo "### installing the snakemake side (this downloads from PyPI)"
# shellcheck disable=SC2086
"$SMK_VENV/bin/python" -m pip install $BENCH_SMK_INSTALL

{
  echo "# written by setup_env.sh on $(date -Is); machine-local, do not archive."
  echo "PY=$PIPEN_VENV/bin/python"
  echo "SMK=$SMK_VENV/bin/snakemake"
} > "$HERE/bench.local.env"

echo
echo "### versions"
"$PIPEN_VENV/bin/python" -c "import pipen, pandas; print('pipen', pipen.__version__, '| pandas', pandas.__version__)"
"$PIPEN_VENV/bin/python" -c "import importlib.metadata as m; print('pipen-runinfo', m.version('pipen-runinfo'))"
"$SMK_VENV/bin/snakemake" --version | sed 's/^/snakemake /'
echo
echo "### wrote $HERE/bench.local.env (PY/SMK).  Next:"
echo "###   bash $HERE/run_all.sh /tmp/bench-out"
echo "### reduced-size example:"
echo "###   BENCH_NPROC=4 BENCH_REPS=1 BENCH_SCALING_NS=20 BENCH_CONC_FORKS=1,2 \\"
echo "###     BENCH_CACHE_TIMING_N=20 BENCH_WORK_ROOT=/tmp/bench-work \\"
echo "###     bash $HERE/run_all.sh /tmp/bench-out-reduced"
