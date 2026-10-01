#!/usr/bin/env bash
# Step 2 + 3 + 4: install the demo namespace packages, capture the CLI surface,
# run the process and show the produced output file.
set -u
RAW=/mnt/f/E/hermes-workspace/pipen/ai_demo/raw
SRC=/mnt/f/E/hermes-workspace/pipen/ai_demo
DEMO=$HOME/aidemo
VPY="$DEMO/.venv/bin/python"
PIPEN="$DEMO/.venv/bin/pipen"
TESTDATA="$DEMO/testdata"
mkdir -p "$RAW" "$TESTDATA"

# ---- stage the packages into WSL home (pipen run must import them) ----------
rm -rf "$DEMO/demo_ns" "$DEMO/demo_extra_ns"
cp -r "$SRC/demo_ns" "$DEMO/demo_ns"
cp -r "$SRC/demo_extra_ns" "$DEMO/demo_extra_ns"

echo "############ STAGE: pip install -e of the two namespace packages"
"$VPY" -m pip install -e "$DEMO/demo_ns" -e "$DEMO/demo_extra_ns" 2>&1
echo "PIP_INSTALL_RC=$?"

echo
echo "############ registered entry points in group 'pipen_cli_run'"
"$VPY" - <<'PY'
from importlib.metadata import distributions
for dist in distributions():
    for ep in dist.entry_points:
        if ep.group == "pipen_cli_run":
            print(f"{dist.metadata['Name']}__{ep.name} -> {ep.value}")
PY

# ---- test data --------------------------------------------------------------
python3 - "$TESTDATA" <<'PY'
import gzip, os, sys, random
out = sys.argv[1]
random.seed(0)
def w(path, n, lo, hi):
    with gzip.open(path, "wt") as fh:
        for i in range(n):
            L = random.randint(lo, hi)
            fh.write(f"@read{i}\n{''.join(random.choice('ACGT') for _ in range(L))}\n+\n{'I' * L}\n")
w(os.path.join(out, "s1_R1.fastq.gz"), 40, 40, 80)
w(os.path.join(out, "s1_R2.fastq.gz"), 40, 40, 80)
print("wrote test FASTQ files to", out)
PY
ls -l "$TESTDATA"

# ---- STEP 3: capture the CLI surface ---------------------------------------
echo
echo "############ STEP 3a: pipen --help"
"$PIPEN" --help 2>&1
echo "RC=$?"

echo
echo "############ STEP 3b: pipen run --help"
"$PIPEN" run --help 2>&1
echo "RC=$?"

echo
echo "############ STEP 3c: pipen run demo_ns --help"
"$PIPEN" run demo_ns --help 2>&1
echo "RC=$?"

echo
echo "############ STEP 3d: pipen run demo_ns FastqStats --help"
"$PIPEN" run demo_ns FastqStats --help 2>&1
echo "RC=$?"

echo
echo "############ STEP 3e: pipen run demo_ns CountReads --help"
"$PIPEN" run demo_ns CountReads --help 2>&1
echo "RC=$?"

# ---- STEP 4: run it for real ------------------------------------------------
OUTDIR="$DEMO/out_fastqstats"
rm -rf "$OUTDIR"
echo
echo "############ STEP 4a: pipen run demo_ns FastqStats ..."
"$PIPEN" run demo_ns FastqStats \
  --in.r1 "$TESTDATA/s1_R1.fastq.gz" \
  --in.r2 "$TESTDATA/s1_R2.fastq.gz" \
  --envs.min_length 50 \
  --envs.sample_id s1 \
  --outdir "$OUTDIR" 2>&1
echo "RC=$?"

echo
echo "############ STEP 4b: tree of the produced outdir"
find "$OUTDIR" -type f | sort

echo
echo "############ STEP 4c: ls -l of the process output directory"
ls -l "$OUTDIR/FastqStats" 2>&1

echo
echo "############ STEP 4d: cat of the produced output file"
cat "$OUTDIR/FastqStats/read_stats.tsv" 2>&1
echo "--- end of produced file ---"

echo
echo "############ STEP 4e: the auto-generated job script (proof of the class->shell path)"
cat "$OUTDIR/FastqStats/0/job.script" 2>&1 || find "$OUTDIR" -name 'job.script' | head

echo
echo "############ STEP 4f: second namespace, run through the same CLI path"
OUTDIR2="$DEMO/out_gc"
rm -rf "$OUTDIR2"
printf '>s1\nACGTACGTGGCCNNACGT\n>s2\nGGGGCCCCAAAATTTT\n' > "$TESTDATA/toy.fasta"
"$PIPEN" run demo_extra_ns FastaGc --in.fasta "$TESTDATA/toy.fasta" --outdir "$OUTDIR2" 2>&1
echo "RC=$?"
cat "$OUTDIR2/FastaGc/gc.tsv" 2>&1
