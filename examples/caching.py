"""An example showing how caching works"""

from pathlib import Path
from pipen import Pipen, Proc


class AProcess(Proc):
    """A normal process"""

    # Input: expects a file path
    input = "infile:file"
    # Output: uses input filename as output filename
    output = "outfile:file:{{in.infile.name}}"

    # Simple script: just copy input to output
    script = "cat {{in.infile}} > {{out.outfile}}"


class MyPipeline(Pipen):
    starts = AProcess
    # Enable debugging information so you will see why jobs are not cached
    loglevel = "debug"


if __name__ == "__main__":
    # Create input file if it doesn't exist
    infile = "/tmp/pipen_example_caching.txt"
    if not Path(infile).exists():
        Path(infile).write_text("123")

    # Run pipeline with the input file
    # Jobs will run on first execution
    MyPipeline().set_data([infile]).run()

    print("\n" + "=" * 60)
    print("Run this script repeatedly, you will see that jobs are cached")
    print("=" * 60)

# Expected Output:
# ============
# First run:
# ```
# AProcess: >>> [END]
# AProcess: CACHED   <--- Jobs are cached on second run
# ```
#
# Second run (no changes):
# ```
# AProcess: >>> [END]
# AProcess: CACHED   <--- Jobs are cached because inputs unchanged
# ```
#
# To "de-cache" jobs, either:
# 1. touch the input file
# 2. change any part of input, output, script
# 3. run with cache=False or set it to AProcess and run again
