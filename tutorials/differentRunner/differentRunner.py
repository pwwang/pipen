from sys import argv
from pyppl import PyPPL, Proc, Channel

pSort         = Proc(desc = 'Sort files.')
pSort.input   = {"infile:file": Channel.fromPattern("./data/*.txt")}
pSort.output  = "outfile:file:{{in.infile | fn}}.sorted"
# specify the runner
#pSort.runner  = 'sge'
# specify the runner options
#pSort.sgeRunner = {
#	"sge.q" : "1-day"
#}
pSort.forks   = 5
pSort.exdir   = './export'
pSort.script  = """
  sort -k1r {{in.infile}} > {{out.outfile}}
"""

PyPPL().start(pSort).run('local' if len(argv) <= 1 else argv[1])
# or run all process with sge runner:
# PyPPL().start(pSort).run('sge')
# or:
# PyPPL({
#	'proc': {
#		'runner': 'sge',
#		'sgeRunner': {'sge.q': '1-day'}
#	}
# }).start(pSort).run()
