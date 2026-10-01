#!/usr/bin/env bash
set -u
R="$HOME/bench_abl/wd/verify_F/AblPipeline"
echo "--- shard output dir (F) ---"
ls -la "$R/Shard/0/output/" 2>&1
echo
echo "--- shard status/rc (F) ---"
for i in 0 1 7; do
  echo "Shard/$i: status=$(cat "$R/Shard/$i/job.status" 2>&1) rc=$(cat "$R/Shard/$i/job.rc" 2>&1)"
done
echo
echo "--- files in Shard/0 (F, full list) ---"
ls -la "$R/Shard/0/"
echo
echo "--- any 'Agg' mention in F log ---"
grep -n "Agg" "$HOME/bench_abl/out/logs/verify_F.log"
echo
echo "--- F log, non-banner lines (drop the ascii banner block) ---"
grep -v "I core    [║│╭╰═─]" "$HOME/bench_abl/out/logs/verify_F.log" | tail -12
echo
echo "--- E_all log, non-banner lines ---"
grep -v "I core    [║│╭╰═─]" "$HOME/bench_abl/out/logs/verify_E_all.log" | tail -12
echo
echo "--- A log, non-banner lines ---"
grep -v "I core    [║│╭╰═─]" "$HOME/bench_abl/out/logs/verify_A.log" | tail -12
