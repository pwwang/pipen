#!/usr/bin/env python3
"""Analyse a pipen marker log (job start/end epochs) -> observed parallelism."""
import sys
from collections import defaultdict

path = sys.argv[1]
starts, ends = {}, {}
with open(path) as f:
    for line in f:
        parts = line.split()
        if len(parts) != 3:
            continue
        kind, idx, ts = parts
        ts = float(ts)
        if kind == "shard_start":
            starts[int(idx)] = ts
        elif kind == "shard_end":
            ends[int(idx)] = ts

if not starts:
    print("no shard_start lines")
    sys.exit(0)

t0 = min(starts.values())
t1 = max(ends.values()) if ends else max(starts.values())
print(f"jobs={len(starts)} ends={len(ends)}")
print(f"first_start={t0:.6f} last_end={t1:.6f} span={t1 - t0:.3f}s")

# observed concurrency: for each job, [start, end]; sweep
events = []
for i, s in starts.items():
    e = ends.get(i, s)
    events.append((s, 1))
    events.append((e, -1))
events.sort()
cur = peak = 0
busy_area = 0.0
prev = None
for t, d in events:
    if prev is not None:
        busy_area += cur * (t - prev)
    cur += d
    peak = max(peak, cur)
    prev = t
span = t1 - t0
print(f"peak_concurrent_jobs={peak}")
print(f"mean_concurrent_jobs={busy_area / span:.2f}")
print(f"sum_job_durations={sum(ends.get(i, starts[i]) - s for i, s in starts.items()):.3f}s")
durs = sorted(ends.get(i, starts[i]) - s for i, s in starts.items())
print(f"job_duration_s: min={durs[0]:.4f} median={durs[len(durs)//2]:.4f} max={durs[-1]:.4f}")
# queueing: spread of start times
ss = sorted(starts.values())
print(f"start_spread={ss[-1] - ss[0]:.3f}s  (first job start delayed by "
      f"{ss[0] - t0:.3f}s after the earliest)")
