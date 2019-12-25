
from time import time
from pyppl import PyPPL, Proc

pRetry         = Proc(desc = 'Retry when error happens.')
pRetry.input   = {"in": [0, 1]}
pRetry.output  = "out:var:1"
pRetry.errhow  = 'retry'
pRetry.forks   = 2
pRetry.errntry = 10
pRetry.args.t0 = time()
pRetry.lang    = "python"
pRetry.script  = """
from time import time, sleep
sleep(.2)
t = time() - {{args.t0}}
from sys import stderr
stderr.write('pyppl.log.debug: %s\\n' % t)
if t < 2:
  raise RuntimeError('Runtime error!')
"""

PyPPL().start(pRetry).run()
