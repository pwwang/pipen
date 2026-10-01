#!/usr/bin/env bash
# Capture the generated job script deterministically: run from a known CWD.
set -u
DEMO=$HOME/aidemo
PIPEN="$DEMO/.venv/bin/pipen"
export PATH="$DEMO/.venv/bin:$PATH"
TESTDATA="$DEMO/testdata"
RUN=$DEMO/run_cli_workdir
rm -rf "$RUN"; mkdir -p "$RUN"; cd "$RUN"

echo "CWD at run time: $(pwd)"
echo
echo "\$ pipen run demo_ns FastqStats --in.r1 <r1> --in.r2 <r2> --envs.min_length 50 --envs.sample_id s1 --outdir ./out"
"$PIPEN" run demo_ns FastqStats \
  --in.r1 "$TESTDATA/s1_R1.fastq.gz" \
  --in.r2 "$TESTDATA/s1_R2.fastq.gz" \
  --envs.min_length 50 \
  --envs.sample_id s1 \
  --outdir ./out 2>&1
echo "RC=$?"

echo
echo "############ everything created under the run directory (incl. hidden)"
find "$RUN" | sort

echo
echo "############ the generated job script"
for f in $(find "$RUN" -name 'job.script' | sort); do
  echo "===== $f ====="
  cat "$f"
  echo "===== end ====="
done

echo
echo "############ the job stdout / stderr / status"
for f in $(find "$RUN" -name 'job.stdout' -o -name 'job.stderr' -o -name 'job.status' -o -name 'job.rc' | sort); do
  echo "--- $f ---"; cat "$f"
done

echo
echo "############ produced outputs"
find "$RUN/out" -type f | sort
cat "$RUN/out/FastqStats/read_stats.tsv"
