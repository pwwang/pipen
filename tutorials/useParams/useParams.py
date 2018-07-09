
from pyppl import PyPPL, Proc, Channel, params

params('prefix', '--param-')

params.datadir    \
  .setRequired()  \
  .setDesc('The data directory containing the data files.')

# or
# params.datadir.required = True
# params.datadir.desc     = 'The data directory containing the data files.'

params = params.parse()

pSort         = Proc(desc = 'Sort files.')
pSort.input   = {"infile:file": Channel.fromPattern(params.datadir + '/*.txt')}
pSort.output  = "outfile:file:{{in.infile | fn}}.sorted"
pSort.forks   = 5
pSort.exdir   = './export'
pSort.script  = """
  sort -k1r {{in.infile}} > {{out.outfile}}
"""

PyPPL().start(pSort).run()
