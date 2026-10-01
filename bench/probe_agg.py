"""Probe: aggregation job that declares the list of all shard files as its `files` input."""
import os
import shlex
from pathlib import Path

import pandas as pd
from pipen import Proc, Pipen

WORKDIR = os.environ["PROBE_WORKDIR"]
N = int(os.environ.get("PROBE_N", "4"))
LOG = os.environ["PROBE_LOG"]


class Shard(Proc):
    """fan-out shard"""

    input = "i"
    input_data = list(range(N))
    output = "outfile:file:shard-{{in.i}}.txt"
    script = (
        "echo \"shard\\t{{in.i}}\" >> " + shlex.quote(LOG) + "\n"
        "sleep 0.05\n"
        "echo {{in.i}} > {{out.outfile}}"
    )


class AggFiles(Proc):
    """aggregate: one job, `files` input holding every shard output"""

    requires = Shard
    input = "shardfiles:files"
    output = "outfile:file:agg.txt"
    script = (
        "echo agg >> " + shlex.quote(LOG) + "\n"
        "cat {{in.shardfiles | join: ' '}} > {{out.outfile}}"
    )

    # single row whose cell is the list of all upstream output files
    input_data = lambda ch: pd.DataFrame({"shardfiles": [list(ch.iloc[:, 0])]})


class ProbeAggPipeline(Pipen):
    starts = Shard
    workdir = WORKDIR
    forks = 8


if __name__ == "__main__":
    ProbeAggPipeline().run()
    base = Path(WORKDIR) / "ProbeAggPipeline"
    print("SHARD_JOBS:", sorted(p.name for p in (base / "Shard").iterdir()))
    print("AGG_JOBS:", sorted(p.name for p in (base / "AggFiles").iterdir()))
    for s in sorted((base / "AggFiles").rglob("job.script")):
        print(f"--- {s}\n{s.read_text()}")
    for d in sorted((base / "AggFiles").iterdir()):
        for f in (d / "output").rglob("*"):
            print("  OUT", f, "->", repr(f.read_text() if f.is_file() else ""))
    print("SIGNATURE:")
    for s in sorted((base / "AggFiles").rglob("job.signature.toml")):
        print(s.read_text())
