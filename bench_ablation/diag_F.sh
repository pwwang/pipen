#!/usr/bin/env bash
set -u
for ARM in verify_F verify_E_all verify_A; do
  echo "##################### $ARM #####################"
  R="$HOME/bench_abl/wd/$ARM/AblPipeline"
  echo "--- tree (depth 3, dirs+files count) ---"
  find "$R" -maxdepth 3 | sed "s|$R|<WD>|" | sort | head -40
  echo "--- Agg job metadir ---"
  A="$R/Agg"
  if [ -d "$A" ]; then
    find "$A" -maxdepth 3 -type f | sed "s|$A|<AGG>|" | sort | head -30
    for f in $(find "$A" -name 'job.status' -o -name 'job.rc' | head -5); do
      echo "  $f => $(cat "$f" 2>/dev/null)"
    done
  else
    echo "  (no Agg workdir!)"
  fi
  echo "--- grep log for process banners / queued lines ---"
  L="$HOME/bench_abl/out/logs/$ARM.log"
  grep -n "START\|>>>\|Pushing job\|Skip submitting\|Cached\|failed\|Failed" "$L" | head -30
  echo
done
