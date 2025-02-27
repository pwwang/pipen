"""An example using cloud workdir/outdiur"""

from dotenv import load_dotenv
from pipen import Proc, Pipen

load_dotenv()
BUCKET = "gs://handy-buffer-287000.appspot.com"


class MyProcess(Proc):
    """A process"""

    input = "a"
    input_data = [1]
    output = "outfile:file:{{in.a}}.txt"
    script = "cloudsh touch {{out.outfile}}"


class MyProcess2(Proc):
    """Another process"""
    requires = MyProcess
    input = "infile:file"
    output = "outfile:file:{{in.infile.stem}}2.txt"
    script = "cloudsh cat {{in.infile}} | cloudsh sink {{out.outfile}}"


class MyCloudDirPipeline(Pipen):
    starts = MyProcess
    workdir = f"{BUCKET}/pipen-test/clouddir-pipeline/workdir"
    outdir = f"{BUCKET}/pipen-test/clouddir-pipeline/outdir"


if __name__ == "__main__":
    MyCloudDirPipeline().run()
