"""
# Dry runner
"""
from os import path, utime, remove
from .runner import Runner
from .. import utils

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
		# construct an ssh cmd
		dryfile      = self.job.script + '.dry'
		
		drysrc       = [
			'#!/usr/bin/env bash',
			'',
			'trap "status=\\$?; echo \\$status > %s; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.job.rcfile,
			''
		]
		
		
		for _, val in self.job.output.items():
			if val['type'] in self.job.proc.OUT_VARTYPE:
				continue
				
			if val['type'] in self.job.proc.OUT_FILETYPE: # and not path.exists(val['data']): job will be reset
				drysrc.append('touch "%s"' % val['data'])
			elif val['type'] in self.job.proc.OUT_DIRTYPE: # and not path.exists(val['data']):
				drysrc.append('mkdir -p "%s"' % val['data'])
				
		with open (dryfile, 'w') as f:
			f.write ('\n'.join(drysrc) + '\n')
		
		self.script = utils.chmodX(dryfile)
		
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
			
		self.p = None
		self.retry ()