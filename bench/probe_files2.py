"""Probe 2: absolute-path fan-out outputs + collapse_files() -> exactly 1 aggregation job."""
import os
import shlex
from pathlib import Path

from pipen import Proc, Pipen
from pipen.channel import collapse_files

WORKDIR = os.environ["PROBE_WORKDIR"]
N = int(os.environ.get("PROBE_N", "4"))
LOG = os.environ["PROBE_LOG"]
SHARD_DIR = os.path.join(WORKDIR, "shards")
os.makedirs(SHARD_DIR, exist_ok=True)


class Shard(Proc):
    """fan-out shard"""

    input = "i"
    input_data = list(range(N))
    output = "outfile:file:" + SHARD_DIR + "/shard-{{in.i}}.txt"
    script = (
        "echo \"shard\\t{{in.i}}\" >> " + shlex.quote(LOG) + "\n"
        "echo {{in.i}} > {{out.outfile}}"
    )


class Agg(Proc):
    """aggregate"""

    requires = Shard
    input = "sharddir:dir"
    input_data = lambda ch: ch >> collapse_files()
    output = "outfile:file:agg.txt"
    script = (
        "echo agg >> " + shlex.quote(LOG) + "\n"
        "cat {{in.sharddir}}/*.txt > {{out.outfile}}"
    )


class Probe2Pipeline(Pipen):
    starts = Shard
    workdir = WORKDIR
    forks = 8


if __name__ == "__main__":
    Probe2Pipeline().run()
    base = Path(WORKDIR) / "Probe2Pipeline"
    print("SHARD_JOBS:", sorted(p.name for p in (base / "Shard").iterdir()))
    print("AGG_JOBS:", sorted(p.name for p in (base / "Agg").iterdir()))
    print("AGG_SCRIPT:")
    for s in sorted((base / "Agg").rglob("job.script")):
        print(f"--- {s}")
        print(s.read_text())
    print("AGG_OUTPUT_DIRS:")
    for d in sorted((base / "Agg").iterdir()):
        for f in d.rglob("*"):
            print("  ", f, "->", (f.read_text().strip() if f.is_file() and f.stat().st_size < 500 else f.stat().st_size))
