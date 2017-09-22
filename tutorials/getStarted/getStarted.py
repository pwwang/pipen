
from pyppl import PyPPL, Proc, Channel

pSort          = Proc(desc = 'Sort files.')
pSort.input    = {"infile:file": Channel.fromPattern("./data/*.txt")}
pSort.output   = "outfile:file:{{in.infile | fn}}.sorted"
pSort.forks    = 5
pSort.exdir    = './export'
pSort.script   = """
  sort -k1r {{in.infile}} > {{out.outfile}} 
""" 

PyPPL().start(pSort).run()
