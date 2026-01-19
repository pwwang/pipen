from pipen import Proc, run


# Example: Sort input file
class P1(Proc):
    """Sort input file"""

    # Define input: expects a file path
    input = "infile"

    # Provide sample data for testing
    input_data = ["/tmp/data.txt"]

    # Define output: a file called "sorted.txt"
    output = "outfile:file:intermediate.txt"

    # The script to execute
    # {{ in.infile }} will be replaced with the input file path
    # {{ out.outfile }} will be replaced with the output file path
    script = """
    cat {{ in.infile }} | sort > {{ out.outfile }}
    """


# Example: Paste line number
class P2(Proc):
    """Paste line number"""

    # This process depends on SortFile
    requires = P1

    # Input is a file (output from SortFile)
    input = "infile:file"

    # Output is a file called "numbered.txt"
    output = "outfile:file:result.txt"

    # Script adds line numbers (1-3 in this case)
    script = """
    paste <(seq 1 3) {{ in.infile }} > {{ out.outfile }}
    """


# Expected Output:
# ============
# After running: python example.py
# And creating test data: echo -e "3\n2\n1" > /tmp/data.txt
#
# The pipeline will create:
#
# 1. /tmp/data.txt (input data)
# 2. .pipen/MyPipeline/P1/0/output/intermediate.txt (sorted output from P1)
# 3. .pipen/MyPipeline/P2/0/output/result.txt (numbered output from P2)
# 4. MyPipeline-output/P2/result.txt (final exported output)
#
# The log will show:
# ```
# MYPIPELINE: 100%|██████████████████████████████| 2/2 [00:00<00:00, 0.35 procs/s]
# ```
#
# Where you'll see "CACHED" for P2's second run if inputs haven't changed

# class MyPipeline(Pipen):
#     starts = P1

if __name__ == "__main__":
    # MyPipeline().run()
    # Before running the pipeline, make sure to create the input file
    # $ echo -e "3\n2\n1" > /tmp/data.txt
    run("MyPipeline", starts=P1, desc="My pipeline")
