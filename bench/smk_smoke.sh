#!/usr/bin/env bash
set -u
echo "=== snakemake --rerun-triggers choices ==="
"$HOME/bench/smk/bin/snakemake" --help 2>&1 | grep -A 6 "rerun-triggers"
echo "=== smoke: N=5 cores=4 ==="
WD="$HOME/bench/smk_smoke"
rm -rf "$WD"
mkdir -p "$WD"
: > "$HOME/bench/out/marker_smoke.log"
BN_N=5 BN_SLEEP=0.05 BN_MARKER="$HOME/bench/out/marker_smoke.log" \
  "$HOME/bench/smk/bin/snakemake" --cores 4 -s /mnt/f/E/hermes-workspace/pipen/bench/smk_dag/Snakefile \
  > "$HOME/bench/out/smk_smoke.log" 2>&1
echo "SMK_SMOKE_RC=$?"
tail -12 "$HOME/bench/out/smk_smoke.log"
echo "--- marker ---"
cat "$HOME/bench/out/marker_smoke.log"
echo "--- workdir ---"
find "$WD" -type f | head -20
WOROOT="$WD"
