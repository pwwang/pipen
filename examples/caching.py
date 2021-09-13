"""An example showing how caching works"""

from pathlib import Path
from pipen import Pipen, Proc

class AProcess(Proc):
    """A normal process"""
    input = "infile:file"
    output = "outfile:file:{{in.infile.split('/')[-1]}}"
    script = "cat {{in.infile}} > {{out.outfile}}"

infile = "/tmp/pipen_example_caching.txt"
if not Path(infile).exists():
    Path(infile).write_text("123")

AProcess.input_data = [infile]

# Enable debugging information so you will see why jobs are not cached
# if you are not
Pipen(loglevel="debug").run(AProcess)


# Run this script the repeatedly, you will see the jobs are cached

# To "de-cache" the jobs, either
# 1. touch the input file
# 2. change any part of input, output, script
# 3. run:
#    PIPEN_default_cache=0 python caching.py
# 4. Pass cache=False or set it to AProcess and run again
