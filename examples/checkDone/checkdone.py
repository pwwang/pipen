import sys
import cmdy
from os import path
from pyppl import PyPPL, Proc
from pyppl.utils import fs

p        = Proc()
p.input  = 'i:var'
p.input  = [0]
p.output = 'outfile:file:{{i.i}}.txt'
p.script = 'echo {{i.i}} > {{o.outfile}}'

config = dict(default = dict(_log = dict(leveldiffs = 'debug')))
# run the pipeline first anyway
PyPPL(config).start(p).run()
# remove the cache file
fs.remove(path.join(p.workdir, '1', 'job.cache'))

if len(sys.argv) == 1: # no arguments
	# run the pipeline again
	PyPPL(config).start(p).run()
	exit(0)

if sys.argv[1] == 'fail':
	with open(path.join(p.workdir, '1', 'job.rc'), 'w') as frc:
		frc.write('1')
	# run the pipeline again
	PyPPL(config).start(p).run()
	exit(0)

if sys.argv[1] == 'newer':
	cmdy.touch(path.join(p.workdir, '1', 'job.script'))
	# run the pipeline again
	PyPPL(config).start(p).run()
	exit(0)
