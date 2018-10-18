from multiprocessing import Value
from .logger import logger

class Job(object):
	
	# 0b
	# 1 (0: Job needs running, 1: Job done)
	# 1 (0: Non-killing step, 1: Killing step)
	# 1 (0: Non-building step, 1: Building step) 
	# 1 (0: Non-submitting step, 1: Submitting step)
	# 1 (0: Non-running step, 1: Running step) 
	# 1 (0: Non-ing, 1: -ing)
	# 1 (0: Sucessded, 1: Failed)

	STATUS_INITIATED    = 0b0000000
	STATUS_BUILDING     = 0b0010010
	STATUS_BUILT        = 0b0010001
	STATUS_BUILTFAILED  = 0b1010000
	STATUS_SUBMITTING   = 0b0001011
	STATUS_SUBMITTED    = 0b0001000
	STATUS_SUBMITFAILED = 0b1001001
	STATUS_RUNNING      = 0b0000110
	STATUS_RETRYING     = 0b0000111
	STATUS_DONE         = 0b1000100
	STATUS_DONECACHED   = 0b1000000
	STATUS_DONEFAILED   = 0b0000101
	STATUS_ENDFAILED    = 0b1000101
	STATUS_KILLING      = 0b1100010
	STATUS_KILLED       = 0b1100001

	def __init__(self, index):
		self.index  = index
		self.status = Value('i', Job.STATUS_INITIATED)

	def build(self):
		logger.info('Building job %s' % self.index)
		self.status.value = Job.STATUS_BUILDING
		from time import sleep
		sleep(.5)
		self.status.value = Job.STATUS_BUILT

	def submit(self):
		logger.info('Submitting job %s' % self.index)
		self.status.value = Job.STATUS_SUBMITTING
		from time import sleep
		sleep(.2)
		self.status.value = Job.STATUS_SUBMITTED

	def run(self):
		#logger.info('Running job %s' % self.index)
		self.status.value = Job.STATUS_RUNNING
		from time import sleep
		sleep(5)
		self.status.value = Job.STATUS_DONE

	def kill(self):
		logger.info('Killing job %s' % self.index)
		self.status.value = Job.STATUS_KILLING
		from time import sleep
		sleep(2)
		self.status.value = Job.STATUS_KILLED
