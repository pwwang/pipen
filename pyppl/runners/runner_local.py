"""
# A runner wrapper for a single script
# Version: 0.0.1
# Author: pwwang@pwwang.com
# Examples:
#	@see runner.unittest.py
"""
import copy
from os import kill
from subprocess import check_output, CalledProcessError

from .runner import Runner
from .. import utils

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

		localsrc.append ("echo $$ > '%s'" % self.job.pidfile)
		localsrc.append ('trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.job.rcfile)
		
		if 'preScript' in conf:
			localsrc.append (conf['preScript'])

		localsrc.append ('')
		localsrc.append (self.cmd2run + " 1>'%s' 2>'%s'" % (self.job.outfile, self.job.errfile))

		if 'postScript' in conf:
			localsrc.append (conf['postScript'])
		
		with open (localfile, 'w') as f:
			f.write ('\n'.join(localsrc) + '\n')
		
		utils.chmodX(localfile)
		submitfile = self.job.script + '.submit'
		with open(submitfile, 'w') as f:
			f.write('#!/usr/bin/env bash\n')
			f.write("exec '%s' &\n" % localfile)
		self.script = utils.chmodX(submitfile)

	def __del__(self):
		pid = self.job.pid()
		if not pid: return
		
		if pid: 
			# get all children
			# even though there are some other solutions (ps --forest, pstree),
			# this one is more compatible (linux, osx)
			def getDirectChildren(procid):
				try:
					return [p.strip() for p in check_output(['ps', '-o', 'pid', '--ppid', str(procid), '--no-heading']).splitlines()]
				except CalledProcessError:
					return []

			pids = [pid]
			children = getDirectChildren(pid)
			pids.extend(children)
			while children:
				children2 = sum([getDirectChildren(child) for child in children], [])
				pids.extend(children2)
				children = children2
			
			for p in reversed(pids):
				try:
					kill(int(p), 9)
				except OSError:
					pass				
			
