from pipen import Proc, run


class P1(Proc):
    """Sort input file"""

    input = "infile"
    input_data = ["/tmp/data.txt"]
    output = "outfile:file:intermediate.txt"
    script = "cat {{in.infile}} | sort > {{out.outfile}}"


class P2(Proc):
    """Paste line number"""

    requires = P1
    input = "infile:file"
    output = "outfile:file:result.txt"
    script = "paste <(seq 1 3) {{in.infile}} > {{out.outfile}}"


# class MyPipeline(Pipen):
#     starts = P1

if __name__ == "__main__":
    # MyPipeline().run()
    # Before running the pipeline, make sure to create the input file
    # $ echo -e "3\n2\n1" > /tmp/data.txt
    run("MyPipeline", starts=P1, desc="My pipeline")
