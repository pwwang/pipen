#!/usr/bin/env bash
set -u
D=/mnt/f/E/hermes-workspace/pipen/bench_ablation/raw
O="$HOME/bench_abl/out"
echo "=== F: raw/ inventory ==="
echo "logs:    $(ls -1 "$D/logs" | wc -l) files, $(du -sh "$D/logs" | cut -f1)"
echo "markers: $(ls -1 "$D/markers" | wc -l) files, $(du -sh "$D/markers" | cut -f1)"
echo "json:    $(ls -1 "$D"/*.json | wc -l) files"
echo "total:   $(du -sh "$D" | cut -f1)"
echo
echo "=== biggest files in raw/ ==="
find "$D" -type f -printf '%s\t%p\n' | sort -rn | head -8
echo
echo "=== json inventory ==="
ls -la "$D"/*.json
echo
echo "=== source (WSL) out/ inventory ==="
echo "logs:    $(ls -1 "$O/logs" | wc -l) files, $(du -sh "$O/logs" | cut -f1)"
echo "markers: $(ls -1 "$O/markers" | wc -l) files"
echo "logs listing:"; ls -1 "$O/logs" | sort | sed 's/^/    /'
echo "markers listing:"; ls -1 "$O/markers" | sort | sed 's/^/    /'
echo
echo "=== all time_* logs present for every rep? ==="
for t in A_n100_r1 A_n100_r2 A_n100_r3 A_n500_r1 A_n500_r2 A_n500_r3 B_n100_r1 B_n500_r3 \
         C_pf_n100_r1 C_poll_n100_r3 C_kf_n100_r1 C_batch_n100_r1 C_pf_poll_n100_r1 C_pf_poll_n500_r3 \
         F_n100_r1 E_all_n100_r2 verify_A verify_C_pf_poll; do
  printf "  %-22s log=%s marker=%s\n" "$t" \
    "$([ -f "$D/logs/$t.log" ] && echo ok || echo MISSING)" \
    "$([ -f "$D/markers/marker_$t.log" ] && echo ok || echo MISSING)"
done
echo
echo "=== workspace file listing (F:) ==="
ls -la /mnt/f/E/hermes-workspace/pipen/bench_ablation/
