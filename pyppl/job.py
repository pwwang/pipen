from multiprocessing import Value

class Job(object):
	
	STATUS_INITIATED  = 0b000
	STATUS_DONE       = 0b100
	STATUS_DONEFAILED = 0b101

	def __init__(self, index):
		self.index  = index
		self.status = Value('i', STATUS_INITIATED)