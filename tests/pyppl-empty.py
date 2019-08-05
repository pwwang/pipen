
from pyppl.plugin import hookimpl, prerun, postrun, addmethod

@hookimpl
def setup(config):
	config['pempty'] = 0
