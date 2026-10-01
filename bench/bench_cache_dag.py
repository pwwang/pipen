"""Caching-evidence DAG: Read(N) -> {Mid(N) | Side(N)} -> Agg(1).

Env:
  BN_N, BN_INDIR, BN_WORKDIR, BN_MARKER, BN_MIDVARIANT (A|B), BN_SIDEVARIANT (A|B)
  BN_FORKS  local concurrency, default = os.cpu_count() (the archived run used 32)
Every job appends one line to BN_MARKER: "<Proc> <detail> <epoch>".
"""
import os

import pandas as pd
from pipen import Pipen, Proc

N = int(os.environ["BN_N"])
INDIR = os.environ["BN_INDIR"]
WORKDIR = os.environ["BN_WORKDIR"]
MARKER = os.environ["BN_MARKER"]
MIDV = os.environ.get("BN_MIDVARIANT", "A")
SIDEV = os.environ.get("BN_SIDEVARIANT", "A")
#: concurrency is a machine property, not a constant of the DAG
FORKS = int(os.environ.get("BN_FORKS") or os.cpu_count() or 1)
#: BN_PLUGINS="-runinfo" disables the pipen-runinfo plugin (archived protocol).
PLUGINS = [p for p in os.environ.get("BN_PLUGINS", "").split(",") if p]

SED = {"A": "sed 's/^/A:/'", "B": "sed 's/^/B:/'"}  # pylint: disable=invalid-name


class Read(Proc):
    """read each input file"""

    input = "infile:file"
    input_data = [f"{INDIR}/in{i}.txt" for i in range(N)]
    forks = FORKS
    output = "outfile:file:r-{{in.infile.name}}"
    script = (
        'echo "Read {{in.infile.name}} $(date +%s.%N)" >> ' + MARKER + "\n"
        "cat {{in.infile}} > {{out.outfile}}"
    )


class Mid(Proc):
    """mid branch"""

    requires = Read
    forks = FORKS
    input = "infile:file"
    output = "outfile:file:m-{{in.infile.name}}"
    script = (
        'echo "Mid {{in.infile.name}} $(date +%s.%N)" >> ' + MARKER + "\n"
        "cat {{in.infile}} | " + SED[MIDV] + " > {{out.outfile}}"
    )


class Side(Proc):
    """sibling branch (unrelated to Mid)"""

    requires = Read
    forks = FORKS
    input = "infile:file"
    output = "outfile:file:s-{{in.infile.name}}"
    script = (
        'echo "Side {{in.infile.name}} $(date +%s.%N)" >> ' + MARKER + "\n"
        "cat {{in.infile}} | " + SED[SIDEV] + " > {{out.outfile}}"
    )


class Agg(Proc):
    """aggregate both branches"""

    requires = [Mid, Side]
    forks = FORKS
    input = "midfiles:files, sidefiles:files"
    output = "outfile:file:agg.txt"
    script = (
        'echo "Agg agg $(date +%s.%N)" >> ' + MARKER + "\n"
        "echo '# MID' > {{out.outfile}}\n"
        "cat {{in.midfiles | join: ' '}} >> {{out.outfile}}\n"
        "echo '# SIDE' >> {{out.outfile}}\n"
        "cat {{in.sidefiles | join: ' '}} >> {{out.outfile}}"
    )
    input_data = lambda ch_mid, ch_side: pd.DataFrame(
        {"midfiles": [list(ch_mid.iloc[:, 0])], "sidefiles": [list(ch_side.iloc[:, 0])]}
    )


class CachePipeline(Pipen):
    starts = Read
    workdir = WORKDIR
    forks = FORKS
    loglevel = os.environ.get("BENCH_LOGLEVEL", "info")
    if PLUGINS:
        plugins = PLUGINS


if __name__ == "__main__":
    CachePipeline().run()
