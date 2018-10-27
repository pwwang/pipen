"""
Local runner
"""
from .runner import Runner

class RunnerLocal (Runner):
	"""
	Constructor
	@params:
		`job`:    The job object
		`config`: The properties of the process
	"""
	def __init__ (self, job):
		super(RunnerLocal, self).__init__(job)

		# construct an local script
		self.script = job.script + '.local'
		localsrc  = ['#!/usr/bin/env bash']

		conf = job.config.get('runnerOpts', {})
		conf = conf.get('localRunner', {})

		if 'preScript' in conf:
			localsrc.append (conf['preScript'])

		localsrc.append ('')
		localsrc.append (self.cmd2run)
		localsrc.append ('')

		if 'postScript' in conf:
			localsrc.append (conf['postScript'])
		
		with open (self.script, 'w') as f:
			f.write ('\n'.join(localsrc) + '\n')
