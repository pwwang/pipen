"""
# A runner wrapper for a single script
# Version: 0.0.1
# Author: pwwang@pwwang.com
# Examples:
#	@see runner.unittest.py
"""

from .runner import Runner

class RunnerQueue (Runner):
	"""
	The queue runner
	"""

	def submit(self):
		super(RunnerQueue, self).submit(isQ = True)