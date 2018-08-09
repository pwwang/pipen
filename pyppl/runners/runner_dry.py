"""
# Dry runner
"""
from os import path, utime, remove
from .runner import Runner
from .helpers import LocalHelper

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
		dryfile = self.job.script + '.dry'
		drysrc  = ['#!/usr/bin/env bash']
		
		drysrc.append ('')
		for val in self.job.output.values():
			if val['type'] in self.job.proc.OUT_VARTYPE:
				continue
				
			if val['type'] in self.job.proc.OUT_FILETYPE:
				drysrc.append("touch '%s'" % val['data'])
			elif val['type'] in self.job.proc.OUT_DIRTYPE:
				drysrc.append("mkdir -p '%s'" % val['data'])

		with open (dryfile, 'w') as f:
			f.write ('\n'.join(drysrc) + '\n')
		
		self.helper = LocalHelper(dryfile)
		
	def finish (self):
		"""
		Do some cleanup work when jobs finish
		"""
		# dryrun does do cache, export
		utime (self.job.dir, None)
		if self.job.succeed():
			self.job.checkOutfiles(expect = False)
		
		if path.exists(self.job.cachefile):
			remove (self.job.cachefile)
			