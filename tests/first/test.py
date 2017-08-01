import os, sys

sys.path.insert (0, "/home/m161047/tools/pyppl")
sys.path.insert (0, "/home/m161047/tools/bioprocs")
sys.path.insert (0, "/home/m161047/tools/bioaggrs")

# `python test.py clean` to clean the data
if len(sys.argv) == 2 and sys.argv[1] == 'clean':
	try:
		import shutil
		if os.path.exists('./workdir'):
			shutil.rmtree ('./workdir')
		for i in range(1, 6):
			if os.path.exists('./test' + str(i) + '.sorted'):
				os.remove ('./test' + str(i) + '.sorted')
	except: 
		pass
	sys.exit(0)
	
# Copy the following code to README file
from pyppl import pyppl, proc

pSort         = proc(desc = 'Sort files.')
pSort.input   = "infile:file"
pSort.output  = "outfile:file:{{infile | fn}}.sorted"
pSort.forks   = 5
pSort.exdir   = './'
pSort.script  = """
  sort -k1r {{infile}} > {{outfile}}
""" 

pyppl().starts(pSort).run()