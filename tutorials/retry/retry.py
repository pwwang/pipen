
from time import time
from pyppl import PyPPL, Proc

pRetry         = Proc(desc = 'Retry when error happends.')
pRetry.input   = {"in": [0, 1]}
pRetry.errhow  = 'retry'
pRetry.forks   = 2
pRetry.errntry = 3
pRetry.args.t0 = time()
pRetry.lang    = "python"
pRetry.script  = """
from time import time
t = time() - {{args.t0}}
if t < 3:
  raise RuntimeError('Runtime error!')
"""

PyPPL().start(pRetry).run()
