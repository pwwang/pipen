"""An example showing using callback to modify the channel

It's a more complete example from README.md
"""
from pathlib import Path
import random
from pipen import Proc, Pipen
from pipen.channel import Channel


def wc(path):
    """Count lines in the file"""
    i = 0
    with Path(path).open() as f:
        for line in f:
            i += 1
    return i


class P1(Proc):
    """Sort input file"""

    input = "infile:file"
    output = "outfile:file:intermediate.txt"
    script = "cat {{in.infile}} | sort > {{out.outfile}}"


class P2(Proc):
    """Paste line number"""

    requires = P1
    input = "infile:file, nlines"
    # use the callback to add number of lines for each file
    input_data = lambda ch: ch.assign(nlines=ch.outfile.apply(wc))  # noqa: E731
    output = "outfile:file:result.txt"
    script = "paste <(seq 1 {{in.nlines}}) {{in.infile}} > {{out.outfile}}"


def prepare_input_data():
    """Prepare input data"""
    tmpdir = "/tmp/pipen_example_input_data_callback/"
    Path(tmpdir).mkdir(exist_ok=True)

    for i in range(10):
        seq = list(range(i + 2))
        random.shuffle(seq)
        seq = (f"{i}_{x}" for x in seq)

        Path(tmpdir).joinpath(f"{i}.txt").write_text("\n".join(seq))

    return Channel.from_glob(f"{tmpdir}/*.txt")


class MyPipeline(Pipen):
    starts = [P1]
    data = [prepare_input_data()]
    forks = 3


if __name__ == "__main__":
    MyPipeline().run()
