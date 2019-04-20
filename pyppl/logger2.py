"""
Custome logger for PyPPL
"""
import logging
from functools import partial
from simpleconf import config

config.clear()
config._load(dict(default = dict(
	_log = dict(
		file  = None,
		theme = 'default',
	)
)), '~/.PyPPL.ini', './.PyPPL.ini', 'PYPPL.osenv')

class FileFormatter(logging.Formatter):
	
	def __init__(self):
		super(FileFormatter, self).__init__()
	
class StreamHandler(logging.StreamHandler):
	pass

class StreamFilter(logging.Filter):
	pass

class StreamFormatter(logging.Formatter):

	def __init__(self, theme):
		super(StreamFormatter, self).__init__()

class Logger(object):

	def __init__(self, name = 'PyPPL'):
		self.logger = logging.getLogger(name)

		if config._LOG.file:
			file_handler = logging.FileHandler(config._LOG.file)
			file_handler.setFormatter(FileFormatter())
			self.logger.addHandler(file_handler)
		
		stream_handler = StreamHandler()
		stream_handler.addFilter(StreamFilter(name = name))
		stream_handler.setFormatter(StreamFormatter(theme = config._LOG.theme))
		self.logger.addHandler(stream_handler)


	def _emit(self, msg, level):
		self.logger.info(msg)

	def __getattr__(self, name):
		return partial(self._emit, level = name.upper())

logger = Logger()