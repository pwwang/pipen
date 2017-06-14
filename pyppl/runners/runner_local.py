# A runner wrapper for a single script
# Version: 0.0.1
# Author: pwwang@pwwang.com
# Examples: 
#	@see runner.unittest.py
#
import os, stat, sys
from subprocess import Popen, check_output, list2cmdline, PIPE
from time import sleep
from getpass import getuser
from ..helpers import utils
from random import randint
from runner import runner

class runner_local (runner):
	"""
	The local runner
	"""
	
	def isRunning (self, suppose):
		"""
		Try to tell whether the job is still running.
		@returns:
			`True` if yes, otherwise `False`
		"""
		if not self.job.proc.checkrun:
			return suppose
		# rcfile already generated
		if self.job.rc() != self.job.EMPTY_RC:
			return False
		
		uname = getuser()
		psout = check_output (['ps', '-u%s' % uname, '-o', 'args'])
		return self.cmd2run in psout

