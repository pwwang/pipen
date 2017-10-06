
from pyppl import PyPPL, Proc, Channel

pSort          = Proc(desc = 'Sort files.')
pSort.input    = {"infile:file": Channel.fromPattern("./data/*.txt")}
# Notice the different between builtin template engine and Jinja2
pSort.output   = "outfile:file:{{ fn(in.infile) }}.sorted"
# pSort.output   = "outfile:file:{{in.infile | fn}}.sorted"
pSort.forks    = 5
# You have to have Jinja2 installed (pip install Jinja2)
pSort.template = 'Jinja2'
pSort.exdir    = './export'
pSort.script   = """
  sort -k1r {{in.infile}} > {{out.outfile}}
"""

PyPPL().start(pSort).run()
