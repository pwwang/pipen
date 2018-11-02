"""
Dry runner for PyPPL
"""
from .runner import Runner
from ..proc import Proc

class RunnerDry (Runner):
	"""
	The dry runner
	"""
	
	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
		"""
		super(RunnerDry, self).__init__(job)

		# construct an dry script
		self.script = self.job.script + '.dry'
		drysrc  = ['#!/usr/bin/env bash']
		
		drysrc.append ('')
		for val in job.output.values():
			if val['type'] in Proc.OUT_VARTYPE:
				continue
				
			if val['type'] in Proc.OUT_FILETYPE:
				drysrc.append("touch '{}'".format(val['data']))
			elif val['type'] in Proc.OUT_DIRTYPE:
				drysrc.append("mkdir -p '{}'".format(val['data']))

		with open (self.script, 'w') as f:
			f.write ('\n'.join(drysrc) + '\n')
		
