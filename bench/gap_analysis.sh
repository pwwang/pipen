#!/usr/bin/env bash
set -u
echo "=== pipen: does it pass submission_batch / subm_batch? ==="
grep -rn "submission_batch\|subm_batch" "${HOME}/github/pipen/pipen/"*.py | head -20
echo "=== xqute: consumer count + queue ==="
grep -n "subm_batch\|maxsize\|Queue(" "$HOME/bench/.venv/lib/python3.12/site-packages/xqute/xqute.py" | head -20
echo "=== gap analysis of job starts (pipen N=500 forks=32, N=100, N=20 forks=32) ==="
"$HOME/bench/.venv/bin/python" - <<'PY'
from pathlib import Path
import statistics
for name in ["marker_s3_n100_r1", "marker_s3_n500_r1", "marker_s4_n20_f32_r1"]:
    ts = []
    for line in (Path.home()/"bench"/"out"/f"{name}.log").read_text().splitlines():
        p = line.split()
        if len(p) == 3 and p[0] == "shard_start":
            ts.append(float(p[2]))
    ts.sort()
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    small = [g for g in gaps if g < 0.01]
    big = [g for g in gaps if g >= 0.01]
    print(f"--- {name}: n={len(ts)} span={ts[-1]-ts[0]:.3f}s")
    print(f"    gaps: min={min(gaps)*1000:.2f}ms median={statistics.median(gaps)*1000:.2f}ms "
          f"mean={statistics.mean(gaps)*1000:.2f}ms max={max(gaps)*1000:.2f}ms")
    print(f"    gaps<10ms: {len(small)}  gaps>=10ms: {len(big)}")
    if big:
        print(f"    big-gap median={statistics.median(big)*1000:.1f}ms  small-gap median={statistics.median(small)*1000:.2f}ms" if small else "")
PY
echo "=== same for snakemake N=500 ==="
"$HOME/bench/.venv/bin/python" - <<'PY'
from pathlib import Path
import statistics
ts = []
for line in (Path.home()/"bench"/"out"/"marker_smk_s3_n500_r1.log").read_text().splitlines():
    p = line.split()
    if len(p) == 3 and p[0] == "shard_start":
        ts.append(float(p[2]))
ts.sort()
gaps = [b - a for a, b in zip(ts, ts[1:])]
print(f"n={len(ts)} span={ts[-1]-ts[0]:.3f}s gaps median={statistics.median(gaps)*1000:.2f}ms mean={statistics.mean(gaps)*1000:.2f}ms")
PY
