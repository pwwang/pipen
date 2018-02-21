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

		# construct an dry script
		dryfile = self.job.script + '.dry'
		drysrc  = ['#!/usr/bin/env bash']

		drysrc.append ("echo $$ > '%s'" % self.job.pidfile)
		drysrc.append ('trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.job.rcfile)
		
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
		
		utils.chmodX(dryfile)
		submitfile = self.job.script + '.submit'
		with open(submitfile, 'w') as f:
			f.write('#!/usr/bin/env bash\n')
			f.write("exec '%s' &\n" % dryfile)
		self.script = utils.chmodX(submitfile)
		
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
			