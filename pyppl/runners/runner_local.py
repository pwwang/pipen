"""
# A runner wrapper for a single script
# Author: pwwang@pwwang.com
# Examples:
#	@see runner.unittest.py
"""
import copy

from .runner import Runner
from .helpers import LocalHelper

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
		localfile = self.job.script + '.local'
		localsrc  = ['#!/usr/bin/env bash']

		conf = {}
		if 'localRunner' in self.job.proc.props or 'localRunner' in self.job.proc.config:
			conf = copy.copy (self.job.proc.localRunner)

		if 'preScript' in conf:
			localsrc.append (conf['preScript'])

		localsrc.append ('')
		localsrc.append (self.cmd2run)
		localsrc.append ('')

		if 'postScript' in conf:
			localsrc.append (conf['postScript'])
		
		with open (localfile, 'w') as f:
			f.write ('\n'.join(localsrc) + '\n')
		
		self.helper = LocalHelper(localfile)

			
