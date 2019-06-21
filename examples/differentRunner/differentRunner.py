from pathlib import Path
from pyppl import PyPPL, Proc, Channel

mockdir = Path(__file__).resolve().parent.parent.parent / 'tests' / 'mocks'

pSort         = Proc(desc = 'Sort files.')
pSort.input   = {"infile:file": Channel.fromPattern("./data/*.txt")}
pSort.output  = "outfile:file:{{i.infile | fn}}.sorted"
# specify the runner
pSort.runner  = 'sge'
# specify the runner options
# using mock sge commands
pSort.sgeRunner = {
  "qsub" : mockdir / 'qsub',
  "qstat" : mockdir / 'qstat',
  "qdel" : mockdir / 'qdel',
}
pSort.preCmd = 'rm -f %s' % (mockdir / 'sge.jobs.log') # clear the queue
pSort.forks   = 5
pSort.exdir   = './export'
pSort.script  = """
  sort -k1r {{i.infile}} > {{o.outfile}}
"""

PyPPL().start(pSort).run()

