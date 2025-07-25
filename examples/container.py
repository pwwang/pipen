import sys
from pipen import Proc, Pipen


class MyProcess(Proc):

    input = "a"
    input_data = [1]
    output = "outfile:file:{{in.a}}.txt"
    script = "echo {{in.a}} > {{out.outfile}}"


# Works even when metadir/outdir mounted
class MyProcess2(Proc):
    requires = MyProcess
    input = "infile:file"
    output = "outfile:file:{{in.infile.stem}}2.txt"
    script = "echo 123 > {{out.outfile}}"
    export = True


# Works even when metadir/outdir mounted
class MyProcess3(Proc):
    requires = MyProcess2
    input = "infile:file"
    output = "outfile:file:{{in.infile.stem}}3.txt"
    script = "echo 456 > {{out.outfile}}"


class MyContainerPipeline(Pipen):
    starts = MyProcess
    loglevel = "DEBUG"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python container.py <docker|apptainer>")
        sys.exit(1)

    container_type = sys.argv[1].lower()
    if container_type == "docker":
        MyContainerPipeline(
            scheduler="container",
            scheduler_opts={
                "image": "bash:latest",
                "entrypoint": "/usr/local/bin/bash",
            },
        ).run()
    else:
        MyContainerPipeline(
            scheduler="container",
            scheduler_opts={
                "bin": "apptainer",
                "image": "bash_latest.sif",
                "entrypoint": "/usr/local/bin/bash",
            },
        ).run()
