"""
Custome logger for PyPPL
"""
import re
import sys
import logging
from collections import OrderedDict
from functools import partial
from blessings import Terminal
from simpleconf import config

term  = Terminal()
# Available modifiers:

# reset - resets from the current point to the end
# bold - make text bold
# blink - it may blink the text or make it slighly lighten, depending on the terminal
# italic - make text italic
# underline - add underline on text
# inverse - invert colors
# strikethrough - draws a line through the text
# up - does the same than passing replace=True to the output function: carriage return and one line up
# Available colors:

# normal
# black
# red
# green
# yellow
# blue
# magenta
# cyan
# white

LOGFMT = "[%(asctime)s%(message)s"

THEMES = dict(
	greenOnBlack = OrderedDict([
		('DONE', term.bright_green),
		('DEBUG', term.bright_blue),
		('PROCESS', term.bright_cyan),
		('DEPENDS', term.magenta),
		('in:INFO,P_PROPS,OUTPUT,EXPORT,INPUT,P_ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING', term.green),
		('CMDERR', term.bright_yellow),
		('has:ERR', term.red),
		('in:WARNING,RETRY,RESUMED,SKIPPED', term.bright_yellow),
		('in:WORKDIR,CACHED,P.DONE', term.yellow),
		('', term.white),
	])
)

LEVELS = {
	'all':     ['INPUT', 'OUTPUT', 'P_ARGS', 'P_PROPS', 'DEBUG', 'WARNING'],
	'basic':   [],
	'normal':  ['INPUT', 'OUTPUT', 'P_ARGS', 'P_PROPS']
}

LEVELS_ALWAYS = [
    'PROCESS', 'WORKDIR', 'RESUMED', 'SKIPPED', 'DEPENDS', 'STDOUT', 'STDERR', 
    'ERROR', 'INFO', 'DONE', 'EXPORT', 'PYPPL', 'TIPS', 'CONFIG', 'CMDOUT', 'CMDERR', 'BLDING', 
    'SUBMIT', 'RUNNING', 'RETRY', 'JOBDONE', 'KILLING', 'P.DONE', 'CACHED'
]

DEBUG_LINES = {
	'EXPORT_CACHE_OUTFILE_EXISTS'  : -1,
	'EXPORT_CACHE_USING_SYMLINK'   : 1,
	'EXPORT_CACHE_USING_EXPARTIAL' : 1,
	'EXPORT_CACHE_EXFILE_NOTEXISTS': 1,
	'EXPORT_CACHE_EXDIR_NOTSET'    : 1,
	'CACHE_EMPTY_PREVSIG'          : -1,
	'CACHE_EMPTY_CURRSIG'          : -2,
	'CACHE_SCRIPT_NEWER'           : -1,
	'CACHE_SIGINVAR_DIFF'          : -1,
	'CACHE_SIGINFILE_DIFF'         : -1,
	'CACHE_SIGINFILE_NEWER'        : -1,
	'CACHE_SIGINFILES_DIFF'        : -1,
	'CACHE_SIGINFILES_NEWER'       : -1,
	'CACHE_SIGOUTVAR_DIFF'         : -1,
	'CACHE_SIGOUTFILE_DIFF'        : -1,
	'CACHE_SIGOUTDIR_DIFF'         : -1,
	'CACHE_SIGFILE_NOTEXISTS'      : -1,
	'EXPECT_CHECKING'              : -1,
	'INFILE_RENAMING'              : -1,
	'INFILE_EMPTY'                 : -1,
	'SUBMISSION_FAIL'              : -3,
	'OUTFILE_NOT_EXISTS'           : -1,
	'OUTDIR_CREATED_AFTER_RESET'   : -1,
	'SCRIPT_EXISTS'                : -2,
	'JOB_RESETTING'                : -1
}

class Theme(object):

	def __init__(self, theme = 'greenOnBlank'):
		if isinstance(theme, dict):
			self.theme = theme
		elif theme in THEMES:
			self.theme = THEMES[theme]
		else:
			raise ValueError('No such theme: %s', theme)
		
	def getColor(self, level):
		level = level.upper()
		for key, val in self.theme.items():
			if key == level:
				return val.format(term)
			if key.startswith('in:') and level in key[3:].split(','):
				return val.format(term)
			if key.startswith('starts:') and level.startswith(key[7:]):
				return val.format(term)
			if key.startswith('has:') and key[4:] in level:
				return val.format(term)
			if key.startswith('re:') and re.search(key[3:], level):
				return val.format(term)
		return term.normal

config.clear()
config._load(dict(default = dict(
	_log = dict(
		file  = None,
		theme = 'greenOnBlack',
	)
)), '~/.PyPPL.ini', './.PyPPL.ini', 'PYPPL.osenv')
theme = Theme(config._LOG.theme)

class LogFormatter(logging.Formatter):
	
	def __init__(self):
		logging.Formatter.__init__(self, LOGFMT, "%Y-%m-%d %H:%M:%S ")

	def format(self, record):
		record.msg = '%-7s] %s' % (record.mylevel, record.msg)
		logstr = logging.Formatter.format(self, record)
		if record.mylevel.startswith('PBAR_'):
			return '\n'+logstr
		return logstr
		

class FileFilter(logging.Filter):
	
	def filter(self, record):
		return True
	
class StreamHandler(logging.StreamHandler):
	
	def __init__(self, stream = None):
		super(StreamHandler, self).__init__(stream)
		self.terminator = "\n"

	def _emit(self, record, terminator = "\n"):
		"""
		Helper function implementing a python2,3-compatible emit.
		Allow to add "\n" or "\r" as terminator.
		"""
		#terminator = '\n'
		if sys.version_info.major > 2: # pragma: no cover
			self.terminator = terminator
			super(StreamHandler, self).emit(record)
		else:
			msg = self.format(record)
			stream = self.stream
			fs = "%s" + terminator
			#if no unicode support...
			if not logging._unicode: # pragma: no cover
				stream.write(fs % msg)
			else:
				try:
					if (isinstance(msg, unicode) and
						getattr(stream, 'encoding', None)): # pragma: no cover
						ufs = u'%s' + terminator
						try:
							stream.write(ufs % msg)
						except UnicodeEncodeError:
							#Printing to terminals sometimes fails. For example,
							#with an encoding of 'cp1251', the above write will
							#work if written to a stream opened or wrapped by
							#the codecs module, but fail when writing to a
							#terminal even when the codepage is set to cp1251.
							#An extra encoding step seems to be needed.
							stream.write((ufs % msg).encode(stream.encoding))
					else:
						stream.write(fs % msg)
				except UnicodeError: # pragma: no cover
					stream.write(fs % msg.encode("UTF-8"))
			self.flush()

	def emit(self, record):
		if record.mylevel.startswith('PBAR_'):
			with term.location(0, term.height - 1):
				self._emit(record, '')
		else:
			with term.location(0, term.height - 2):
				self._emit(record, '\n')


class StreamFilter(logging.Filter):
	pass

class StreamFormatter(logging.Formatter):

	def __init__(self, theme):
		super(StreamFormatter, self).__init__()


class Logger(object):

	def __init__(self, name = 'PyPPL'):

		self.logger = logging.getLogger(name)
		for handler in self.logger.handlers:
			handler.close()
		del self.logger.handlers[:]
		
		stream_handler = StreamHandler(sys.stdout)
		stream_handler.addFilter(StreamFilter(name = name))
		stream_handler.setFormatter(LogFormatter())
		self.logger.addHandler(stream_handler)

		if config._LOG.file:
			file_handler = logging.FileHandler(config._LOG.file)
			file_handler.addFilter(FileFilter(name = name))
			self.logger.addHandler(file_handler)

		self.ispbar = False

	@property
	def pbar(self):
		self.ispbar = True
		return self
		
	def _emit(self, msg, level):
		self.logger.info(msg, extra = {'mylevel': level})

	def __getattr__(self, name):
		if self.ispbar:
			self.ispbar = False
			name = 'pbar_' + name
		return partial(self._emit, level = name.upper())

logger = Logger()