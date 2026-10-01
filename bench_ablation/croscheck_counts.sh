#!/usr/bin/env bash
# Cross-check: framework's OWN submission count vs the marker-derived job count.
set -u
D=/mnt/f/E/hermes-workspace/pipen/bench_ablation/raw
printf "%-22s %-10s %-10s %s\n" run framework_log_markers marker_lines shards_from_markers
for t in A_n100_r1 A_n500_r1 A_n500_r2 B_n500_r1 C_pf_poll_n500_r1 C_poll_n100_r1 F_n100_r1 E_all_n100_r2; do
  LOG="$D/logs/$t.log"
  MK="$D/markers/marker_$t.log"
  nsub=$(grep -c "Job .* submitted (jid" "$LOG" || true)
  nlines=$(wc -l < "$MK")
  nshard=$(grep -c "^shard_start" "$MK" || true)
  printf "%-22s %-10s %-10s %s\n" "$t" "$nsub" "$nlines" "$nshard"
done
