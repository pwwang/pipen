#!/usr/bin/env bash
# CPU-cost probe: A vs C_poll vs C_pf_poll at N=100, 1 rep each, with bash `time`.
# Purpose: the 1 ms producer/polling interval turns an O(N)-per-iteration status
# poll into a busy loop; this measures how much CPU time that costs.
# Writes ~/bench_abl/out/cpu_probe.txt (copied to raw/ later).
set -u
OUT="$HOME/bench_abl/out/cpu_probe.txt"
VENV="$HOME/bench/.venv/bin/python"
DAG=/mnt/f/E/hermes-workspace/pipen/bench_ablation/abl_dag.py
: > "$OUT"
TIMEFORMAT='real=%3R user=%3U sys=%3S'
for ARM in A C_poll C_pf_poll; do
  WD="$HOME/bench_abl/wd/cpuprobe_$ARM"
  rm -rf "$WD"; mkdir -p "$WD"
  MK="$HOME/bench_abl/out/markers/marker_cpuprobe_$ARM.log"
  : > "$MK"
  echo "### arm=$ARM n=100 forks=32 rep=1" >> "$OUT"
  { time ABL_ARM=$ARM ABL_N=100 ABL_FORKS=32 ABL_SLEEP=0.05 \
      ABL_WORKDIR="$WD" ABL_MARKER="$MK" ABL_CENSUS=0 \
      "$VENV" "$DAG" > "$HOME/bench_abl/out/logs/cpuprobe_$ARM.log" 2>&1 ; } 2>> "$OUT"
  echo "jobs=$(( $(wc -l < "$MK") / 2 ))  (marker lines / 2)" >> "$OUT"
  rm -rf "$WD"
done
echo "--- cpu_probe.txt ---"
cat "$OUT"
