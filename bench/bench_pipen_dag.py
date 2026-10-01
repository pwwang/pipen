"""Parametrised pipen benchmark DAG: N independent shard jobs -> 1 aggregation job.

Env vars:
  BENCH_N        number of fan-out jobs
  BENCH_SLEEP    sleep per shard (seconds, bash syntax)
  BENCH_FORKS    forks (local scheduler concurrency)
  BENCH_WORKDIR  pipeline workdir
  BENCH_MARKER   append-only log: one line per *job execution* (proc idx epoch)
  BENCH_CACHE    "1" (default) or "0" to disable caching per proc
  BENCH_AGGSLEEP sleep for the aggregation job (default 0)

Prints PIPELINE_RUN_SEC=<float> measured in-process around .run().
"""
import os
import shlex
import time

import pandas as pd
from pipen import Pipen, Proc

N = int(os.environ["BENCH_N"])
SLEEP = os.environ.get("BENCH_SLEEP", "0.05")
AGGSLEEP = os.environ.get("BENCH_AGGSLEEP", "0")
FORKS = int(os.environ.get("BENCH_FORKS") or os.cpu_count() or 1)
WORKDIR = os.environ["BENCH_WORKDIR"]
MARKER = shlex.quote(os.environ["BENCH_MARKER"])
CACHE = os.environ.get("BENCH_CACHE", "1") == "1"
#: BENCH_PLUGINS="-runinfo" disables the pipen-runinfo plugin, so the archived
#: (plugin-free) timing protocol can be reproduced exactly.
PLUGINS = [p for p in os.environ.get("BENCH_PLUGINS", "").split(",") if p]


class Shard(Proc):
    """fan-out shard"""

    input = "i"
    input_data = list(range(N))
    forks = FORKS
    cache = CACHE
    output = "outfile:file:shard-{{in.i}}.txt"
    script = (
        "echo shard_start {{in.i}} $(date +%s.%N) >> " + MARKER + "\n"
        "sleep " + SLEEP + "\n"
        "echo {{in.i}} > {{out.outfile}}\n"
        "echo shard_end {{in.i}} $(date +%s.%N) >> " + MARKER
    )


class Agg(Proc):
    """aggregate all shard outputs into one file"""

    requires = Shard
    forks = FORKS
    cache = CACHE
    input = "shardfiles:files"
    output = "outfile:file:agg.txt"
    script = (
        "echo agg_start 0 $(date +%s.%N) >> " + MARKER + "\n"
        "sleep " + AGGSLEEP + "\n"
        "cat {{in.shardfiles | join: ' '}} > {{out.outfile}}\n"
        "echo agg_end 0 $(date +%s.%N) >> " + MARKER
    )
    input_data = lambda ch: pd.DataFrame({"shardfiles": [list(ch.iloc[:, 0])]})


class DagPipeline(Pipen):
    starts = Shard
    workdir = WORKDIR
    forks = FORKS
    cache = CACHE
    if PLUGINS:
        plugins = PLUGINS


if __name__ == "__main__":
    t0 = time.perf_counter()
    DagPipeline().run()
    t1 = time.perf_counter()
    print(f"PIPELINE_RUN_SEC={t1 - t0:.6f}", flush=True)
