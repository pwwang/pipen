"""Step 2 verification: pipen 2-process hello-world with input_data.

Mirrors the README quickstart: P1 sorts an input file, P2 numbers the lines.
Env: HELLO_WORKDIR (required), HELLO_OUTDIR (required), HELLO_DATA (optional,
defaults to a file in the system temp dir).
"""
import os
import tempfile
from pathlib import Path

from pipen import Proc, Pipen

DATA = Path(os.environ.get("HELLO_DATA", str(Path(tempfile.gettempdir()) / "pipen_hello_data.txt")))
WORKDIR = os.environ["HELLO_WORKDIR"]
OUTDIR = os.environ["HELLO_OUTDIR"]

DATA.write_text("3\n2\n1\n")


class SortFile(Proc):
    """Sort input file"""

    input = "infile"
    input_data = [str(DATA)]
    output = "outfile:file:intermediate.txt"
    script = "cat {{in.infile}} | sort > {{out.outfile}}"


class NumberLines(Proc):
    """Paste line number"""

    requires = SortFile
    input = "infile:file"
    output = "outfile:file:result.txt"
    script = "paste <(seq 1 3) {{in.infile}} > {{out.outfile}}"


class HelloPipeline(Pipen):
    starts = SortFile
    workdir = WORKDIR
    outdir = OUTDIR


if __name__ == "__main__":
    HelloPipeline().run()
