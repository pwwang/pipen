#!/usr/bin/env bash
# Does --out.<key> override the output filename? (observed not to, for the biopipen run)
set -u
DEMO=$HOME/aidemo
PIPEN="$DEMO/.venv/bin/pipen"
export PATH="$DEMO/.venv/bin:$PATH"
RUN=$DEMO/run_out_override
rm -rf "$RUN"; mkdir -p "$RUN"; cd "$RUN"

echo "### pipen run demo_ns FastqStats ... --out.stats custom_stats.tsv"
"$PIPEN" run demo_ns FastqStats \
  --in.r1 "$DEMO/testdata/s1_R1.fastq.gz" \
  --in.r2 "$DEMO/testdata/s1_R2.fastq.gz" \
  --out.stats custom_stats.tsv \
  --outdir ./out 2>&1 | grep -E "out.stats|outdir|>>>" 
echo "RC=$?"
echo "--- files produced ---"
find "$RUN/out" -type f | sort
echo "--- generated job script ---"
cat "$RUN/.pipen/FastqStats/FastqStats/0/job.script" 2>&1
