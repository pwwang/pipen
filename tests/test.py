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
pCombine.input    = {"infiles:files": lambda ch: [ch.toList()]}
pCombine.output   = "outfile:file:{{infiles | [0] | fn}}_etc.sorted"
# Export the final result file
pCombine.exdir    = "./workdir" 
pCombine.script   = """
> {{outfile}}
for infile in {{infiles | asquote}}; do
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