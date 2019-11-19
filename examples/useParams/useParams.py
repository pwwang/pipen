from os import path
from pyppl import PyPPL, Proc, Channel
from pyparam import params

def fn(fpath):
  return path.basename(fpath).split('.')[0]

params.datadir.required = True
params.datadir.desc     = 'The data directory containing the data files.'

params = params._parse()

pSort         = Proc(desc = 'Sort files.')
pSort.input   = {"infile:file": Channel.fromPattern(params['datadir'] + '/*.txt')}
pSort.output  = "outfile:file:{{i.infile | fn}}.sorted"
pSort.forks   = 5
pSort.exdir   = './export'
pSort.envs.fn = fn
pSort.script  = """
  sort -k1r {{i.infile}} > {{o.outfile}}
"""

PyPPL().start(pSort).run()
