import os, sys

sys.path.insert (0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

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

config = {'logtheme': 'greenOnWhite'}
	
# Copy the following code to README file
from pyppl import pyppl, proc

pSort         = proc(desc = 'Sort files.')
pSort.input   = "infile:file"
pSort.output  = "outfile:file:{{infile | fn}}.sorted"
pSort.forks   = 5
pSort.exdir   = './'
pSort.script  = """
  # difference
  sort -k1r {{infile}} > {{outfile}} 
""" 

pyppl({'loglevels': 'basic'}).starts(pSort).run()
