import os, sys
sys.path.insert (0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

from pyppl import pyppl, proc, params

params.infiles.setType(list).setRequired().setDesc("Input files.")
params.runner.setValue('local').setDesc('The runner.')
params.forks.setValue(5).setType(int).setDesc('How many jobs to run simultaneously.')
params.parse()

pSort         = proc(desc = "Sort files.")
pSort.input   = {"infile:file": params.infiles.value}
pSort.output  = "outfile:file:{{infile | fn}}.sorted"
pSort.forks   = 5
pSort.runner  = params.runner.value
pSort.script  = """
  sort -k1r {{infile}} > {{outfile}}
""" 

pyppl().starts(pSort).run()
