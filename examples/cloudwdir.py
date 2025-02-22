"""An example using cloud workdir/outdiur"""

from pathlib import Path

from dotenv import load_dotenv
from pipen import Proc, Pipen

BUCKET = "gs://handy-buffer-287000.appspot.com"
load_dotenv(Path(__file__).parent.parent / ".env")


class MyProcess(Proc):
    """A process using mako templating"""

    input = "a"
    input_data = [1]
    output = "outfile:file:{{in.a}}.txt"
    script = "cloudsh touch {{out.outfile}}"


class MyCloudDirPipeline(Pipen):
    starts = MyProcess
    workdir = f"{BUCKET}/pipen-test/clouddir-pipeline/workdir"
    outdir = f"{BUCKET}/pipen-test/clouddir-pipeline/outdir"


if __name__ == "__main__":
    MyCloudDirPipeline().run()
