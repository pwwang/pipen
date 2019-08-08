
from pyppl.plugin import hookimpl, prerun, postrun, addmethod
from pyppl import logger

@hookimpl
def setup(config):
	config.envs.plugin = 'test'
	config['ptest'] = 0

@prerun
def pplPreRun(ppl):
	logger.info('PYPPL PRERUN')

@postrun
def pplPostRun(ppl):
	logger.info('PYPPL POSTRUN')

@hookimpl
def pypplInit(ppl):
	addmethod(ppl, 'preRun', pplPreRun)
	addmethod(ppl, 'postRun', pplPostRun)

@hookimpl
def procSetAttr(proc, name, value):
	if name == 'ptest':
		proc.props['ptest'] = int(value) * 10

@hookimpl
def procGetAttr(proc, name):
	if name == 'ptest':
		return 0 if 'ptest' not in proc.props else proc.props.ptest * 10

@hookimpl
def procPreRun(proc):
	"""After a process starts"""
	logger.info(proc.name() + ' STARTED')

@hookimpl
def procPostRun(proc):
	"""After a process has done"""
	logger.info(proc.name() + ' ENDED')


@hookimpl
def pypplPreRun(ppl):
	"""A set of functions run when pipeline starts"""
	logger.info('PIPELINE STARTED')

@hookimpl
def pypplPostRun(ppl):
	"""A set of functions run when pipeline ends"""
	logger.info('PIPELINE ENDED')

@hookimpl
def jobPreRun(job):
	"""A set of functions run when job starts"""
	logger.info('JOB %s STARTED' % job.index)

@hookimpl
def jobPostRun(job):
	"""A set of functions run when job ends"""
	logger.info('JOB %s ENDED' % job.index)

@hookimpl
def jobFail(job):
	logger.info('Job %s failed' % job.index)

