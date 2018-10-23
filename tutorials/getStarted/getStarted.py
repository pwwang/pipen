
from pyppl import PyPPL, Proc, Channel

pSort          = Proc(desc = 'Sort files.')
pSort.input    = {"infile:file": Channel.fromPattern("./data/*.txt")}
pSort.output   = "outfile:file:{{i.infile | fn}}.sorted"
pSort.forks    = 5
pSort.exdir    = './export'
pSort.script   = """
  sort -k1r {{i.infile}} > {{o.outfile}}
"""

PyPPL({'_log':{'levels':'all'}}).start(pSort).run()
