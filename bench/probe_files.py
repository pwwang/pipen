"""Probe: verify the files-aggregation pattern ({{in.<key>}} for a `files` input)."""
import os
import shlex
from pathlib import Path

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
        "echo \"shard " + "{{in.i}}\" >> " + shlex.quote(LOG) + "\n"
        "echo {{in.i}} > {{out.outfile}}"
    )


class Agg(Proc):
    """aggregate"""

    requires = Shard
    input = "infiles:files"
    output = "outfile:file:agg.txt"
    script = (
        "echo agg >> " + shlex.quote(LOG) + "\n"
        "cat {{in.infiles}} > {{out.outfile}}"
    )


class ProbePipeline(Pipen):
    starts = Shard
    workdir = WORKDIR
    forks = 4


if __name__ == "__main__":
    ProbePipeline().run()
    print("RENDERED_AGG_SCRIPT:")
    agg_wd = Path(WORKDIR).parent / "ProbePipeline" / "Agg" / "0" / "job.script"
    print(agg_wd.read_text() if agg_wd.exists() else f"<no script at {agg_wd}>")
    print("AGG_OUTPUT:")
    outfiles = list((Path(WORKDIR).parent / "ProbePipeline" / "Agg").rglob("agg.txt"))
    for of in outfiles:
        print("==", of)
        print(of.read_text())
