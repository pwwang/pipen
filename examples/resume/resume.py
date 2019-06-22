"""
	    p1         p8
	 /      \    /
	p2        p3
	 \      /
		p4
	 /      \
	p5        p6
	 \      /
	    p7
"""

from sys import stderr
from shutil import rmtree
from pyppl import Proc, PyPPL
from pyppl.exception import PyPPLProcRelationError

p1  = Proc()
p2  = Proc()
p3  = Proc()
p4  = Proc()
p5  = Proc()
p6  = Proc()
p7  = Proc()
p8  = Proc()

p7.depends  = p5, p6
p5.depends  = p4
p6.depends  = p4
p4.depends  = p2, p3
p2.depends  = p1
p3.depends  = p1, p8

p1.input = {'in':0}
p8.input = {'in':0}

config   = {'_log': {'levels': 'base'}}
logger   = lambda msg: stderr.write("%s\n%s\n%s\n" % ('-'*80, msg, '-'*80))
clear    = lambda: [setattr(p, 'resume', '') for p in [p1,p2,p3,p4,p5,p6,p7,p8]]

logger('Run the pipeline first')
# run first
PyPPL(config).start(p1, p8).run()

# resume from p8, failed. Cannot get to p7
try:
	logger("Resume from p8.")
	clear()
	PyPPL(config).start(p1, p8).resume(p8).run()
except PyPPLProcRelationError as ex:
	logger("Cannot only resume from p8: %s" % ex)

# even without p1, p2, p3 and p8's workdir
for p in [p1,p2,p3,p8]:
	rmtree(p.workdir, ignore_errors=True)
logger('Resume from p4.')
clear()
PyPPL(config).start(p1, p8).resume(p4).run()

# but you can't do it for resume2, which will load the data from proc.settings for prior processes
try:
	logger('Resume2 from p4.')
	clear()
	PyPPL(config).start(p1, p8).resume2(p4).run()
except Exception as ex:
	logger("Cannot resume2 from p4: %s" % ex)

# but you can still resume from p4
logger('Resume from p4.')
clear()
PyPPL(config).start(p1, p8).resume(p4).run()



