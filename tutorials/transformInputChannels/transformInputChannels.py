
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
pAddPrefix.input   = "infile:file"  # automatically inferred from pSort.output
pAddPrefix.output  = "outfile:file:{{in.infile | fn}}.ln"
pAddPrefix.forks   = 5
pAddPrefix.script  = """
paste -d. <(seq 1 $(wc -l {{in.infile}} | cut -f1 -d' ')) {{in.infile}} > {{out.outfile}}
"""

pMergeFiles = Proc(desc = 'Merge files, each as a column.')
pMergeFiles.depends = pAddPrefix
# ["test1.ln", "test2.ln", ..., "test5.ln"]
pMergeFiles.input = {"infiles:files": lambda ch: [ch.flatten()]}
pMergeFiles.output = "outfile:file:mergedfile.txt"
pMergeFiles.exdir = "./export"
pMergeFiles.script = """
paste {{in.infiles | asquote}} > {{out.outfile}}
"""

PyPPL().start(pSort).run()
