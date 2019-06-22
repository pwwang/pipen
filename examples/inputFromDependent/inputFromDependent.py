
from pyppl import PyPPL, Proc, Channel


pSort        = Proc(desc = 'Sort files.')
pSort.input  = {"infile:file": Channel.fromPattern("./data/*.txt")}
pSort.output = "outfile:file:{{i.infile | fn}}.sorted"
pSort.forks  = 5
pSort.script = """
  sort -k1r {{i.infile}} > {{o.outfile}}
"""

pAddPrefix         = Proc(desc = 'Add line number to each line.')
pAddPrefix.depends = pSort
# automatically inferred from pSort.output
pAddPrefix.input   = "infile:file"
pAddPrefix.output  = "outfile:file:{{i.infile | fn}}.ln"
pAddPrefix.exdir   = './export'
pAddPrefix.forks   = 5
pAddPrefix.script  = """
paste -d. <(seq 1 $(wc -l {{i.infile}} | cut -f1 -d' ')) {{i.infile}} > {{o.outfile}}
"""

PyPPL().start(pSort).run()
