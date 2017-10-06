
from pyppl import PyPPL, Proc, Channel


pSort        = Proc(desc = 'Sort files.')
pSort.input  = {"infile:file": Channel.fromPattern("./data/*.txt")}
pSort.output = "outfile:file:{{in.infile | fn}}.sorted"
pSort.forks  = 5
pSort.script = """
  sort -k1r {{in.infile}} > {{out.outfile}}
"""

pAddPrefix         = Proc(desc = 'Add line number to each line.')
pAddPrefix.depends = pSort
# automatically inferred from pSort.output
pAddPrefix.input   = "infile:file"
pAddPrefix.output  = "outfile:file:{{in.infile | fn}}.ln"
pAddPrefix.exdir   = './export'
pAddPrefix.forks   = 5
pAddPrefix.script  = """
paste -d. <(seq 1 $(wc -l {{in.infile}} | cut -f1 -d' ')) {{in.infile}} > {{out.outfile}}
"""

PyPPL().start(pSort).run()
