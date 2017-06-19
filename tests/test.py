import os
import sys
import shutil
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)

from pyppl import pyppl, proc

pSort         = proc()
pSort.input   = "infile:file"
pSort.output  = "outfile:file:{{infile | fn}}.sorted"
pSort.script  = """
  sort -k1r {{infile}} > {{outfile}}
""" 

pCombine      = proc()
# Will use pSort's output channel as input
pCombine.depends  = pSort
# Modify the channel, "collapse" returns the common directory of the files
# The files are at: <workdir>/<job.id>/output/test?.txt.sorted
# So the common directory is <workdir>/
pCombine.input    = {"indir:file": lambda ch: ch.collapse()}
pCombine.output   = "outfile:file:{{indir | fn}}.sorted"
# Export the final result file
pCombine.exdir    = "./workdir" 
pCombine.script   = """
> {{outfile}}
for infile in {{indir}}/*/output/*.sorted; do
	cat $infile >> {{outfile}}
done
"""
try:
	pyppl().starts(pSort).run()
	shutil.rmtree ('./workdir')
except Exception as ex:
	sys.stderr.write(str(ex))
	if os.path.exists('./workdir'):
		shutil.rmtree ('./workdir')