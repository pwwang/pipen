#!/usr/bin/env bash
# ARCHIVED (run-once, this machine's paths: $HOME/bench/smk).
# SUPERSEDED by setup_env.sh (SMK_INSTALL in bench.env), which creates the
# snakemake venv anywhere and records it in bench.local.env.
set -u
OUT="$HOME/bench/out"
mkdir -p "$OUT"
if [ ! -x "$HOME/bench/smk/bin/pip" ]; then
  python3 -m venv "$HOME/bench/smk"
fi
"$HOME/bench/smk/bin/pip" install --upgrade pip > "$OUT/smk_pip_upgrade.log" 2>&1
echo "PIP_UPGRADE_RC=$?"
"$HOME/bench/smk/bin/pip" install snakemake > "$OUT/snakemake_install.log" 2>&1
RC=$?
echo "SNAKEMAKE_INSTALL_RC=$RC"
echo "--- first attempt log (may be stale) ---"
tail -3 "$OUT/snakemake_install.log.old" 2>/dev/null || true
if [ "$RC" -ne 0 ]; then
  echo "=== install failed, trying --index-url ==="
  "$HOME/bench/smk/bin/pip" install --index-url https://pypi.org/simple snakemake > "$OUT/snakemake_install_retry.log" 2>&1
  echo "SNAKEMAKE_INSTALL_RETRY_RC=$?"
  tail -15 "$OUT/snakemake_install_retry.log"
else
  tail -4 "$OUT/snakemake_install.log"
fi
"$HOME/bench/smk/bin/python" -c "import snakemake; print('snakemake', snakemake.__version__)" 2>&1 | tail -2
"$HOME/bench/smk/bin/snakemake" --version 2>&1 | tail -2
