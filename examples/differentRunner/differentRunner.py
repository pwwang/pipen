from pathlib import Path
from pyppl import PyPPL, Proc, Channel

pSort         = Proc(desc = 'Sort files.')
pSort.input   = {"infile:file": Channel.fromPattern("./data/*.txt")}
pSort.output  = "outfile:file:{{i.infile | __import__('pathlib').Path | .name}}.sorted"
# specify the runner
#pSort.runner  = dict(runner = 'sge', sge_q = '1-day')
pSort.runner  = 'dry'
pSort.forks   = 5
pSort.script  = """
  sort -k1r {{i.infile}} > {{o.outfile}}
"""

PyPPL(logger_level = 'debug').start(pSort).run()

assert pSort.channel.get().read_text().strip() == ''

