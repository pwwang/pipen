"""
Custome logger for PyPPL
"""
import re
import logging
from collections import OrderedDict
from copy import copy
from functools import partial

import colorama
# Fore/Back: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
# Style: DIM, NORMAL, BRIGHT, RESET_ALL
from .utils import config

colorama.init(autoreset = False)

LOGFMT     = "[%(asctime)s%(message)s"
LOGTIMEFMT = "%Y-%m-%d %H:%M:%S"

THEMES = dict(
	greenOnBlack = OrderedDict([
		('DONE', '{s.BRIGHT}{f.GREEN}'),
		('DEBUG', '{s.DIM}{f.WHITE}'),
		('PROCESS', '{s.BRIGHT}{f.CYAN}'),
		('DEPENDS', '{f.MAGENTA}'),
		('in:INFO,P_PROPS,OUTPUT,EXPORT,INPUT,P_ARGS,BLDING,SBMTING,RUNNING,JOBDONE,KILLING',
		 '{f.GREEN}'),
		('CMDERR', '{s.BRIGHT}{f.YELLOW}'),
		('has:ERR', '{f.RED}'),
		('in:WARNING,RTRYING,RESUMED,SKIPPED', '{s.BRIGHT}{f.YELLOW}'),
		('in:WORKDIR,CACHED,P_DONE', '{f.YELLOW}'),
		('', ''),
	]),

	blueOnBlack = OrderedDict([
		('DONE', '{s.BRIGHT}{f.BLUE}'),
		('DEBUG', '{s.DIM}{f.WHITE}'),
		('PROCESS', '{s.BRIGHT}{f.CYAN}'),
		('DEPENDS', '{f.GREEN}'),
		('in:INFO,P_PROPS,OUTPUT,EXPORT,INPUT,P_ARGS,BLDING,SBMTING,RUNNING,JOBDONE,KILLING',
		 '{f.BLUE}'),
		('CMDERR', '{s.BRIGHT}{f.YELLOW}'),
		('has:ERR', '{f.RED}'),
		('in:WARNING,RTRYING,RESUMED,SKIPPED', '{s.BRIGHT}{f.YELLOW}'),
		('in:WORKDIR,CACHED,P_DONE', '{f.YELLOW}'),
		('', ''),
	]),

	magentaOnBlack = OrderedDict([
		('DONE', '{s.BRIGHT}{f.MAGENTA}'),
		('DEBUG', '{s.DIM}{f.WHITE}'),
		('PROCESS', '{s.BRIGHT}{f.GREEN}'),
		('DEPENDS', '{f.BLUE}'),
		('in:INFO,P_PROPS,OUTPUT,EXPORT,INPUT,P_ARGS,BLDING,SBMTING,RUNNING,JOBDONE,KILLING',
		 '{f.MAGENTA}'),
		('CMDERR', '{s.BRIGHT}{f.YELLOW}'),
		('has:ERR', '{f.RED}'),
		('in:WARNING,RTRYING,RESUMED,SKIPPED', '{s.BRIGHT}{f.YELLOW}'),
		('in:WORKDIR,CACHED,P_DONE', '{f.YELLOW}'),
		('', ''),
	]),

	greenOnWhite = OrderedDict([
		('DONE', '{s.BRIGHT}{f.GREEN}'),
		('DEBUG', '{s.DIM}{f.BLACK}'),
		('PROCESS', '{s.BRIGHT}{f.BLUE}'),
		('DEPENDS', '{f.MAGENTA}'),
		('in:INFO,P_PROPS,OUTPUT,EXPORT,INPUT,P_ARGS,BLDING,SBMTING,RUNNING,JOBDONE,KILLING',
		 '{f.GREEN}'),
		('CMDERR', '{s.BRIGHT}{f.YELLOW}'),
		('has:ERR', '{f.RED}'),
		('in:WARNING,RTRYING,RESUMED,SKIPPED', '{s.BRIGHT}{f.YELLOW}'),
		('in:WORKDIR,CACHED,P_DONE', '{f.YELLOW}'),
		('', ''),
	]),

	blueOnWhite = OrderedDict([
		('DONE', '{s.BRIGHT}{f.BLUE}'),
		('DEBUG', '{s.DIM}{f.BLACK}'),
		('PROCESS', '{s.BRIGHT}{f.GREEN}'),
		('DEPENDS', '{f.MAGENTA}'),
		('in:INFO,P_PROPS,OUTPUT,EXPORT,INPUT,P_ARGS,BLDING,SBMTING,RUNNING,JOBDONE,KILLING',
		 '{f.BLUE}'),
		('CMDERR', '{s.BRIGHT}{f.YELLOW}'),
		('has:ERR', '{f.RED}'),
		('in:WARNING,RTRYING,RESUMED,SKIPPED', '{s.BRIGHT}{f.YELLOW}'),
		('in:WORKDIR,CACHED,P_DONE', '{f.YELLOW}'),
		('', ''),
	]),

	magentaOnWhite = OrderedDict([
		('DONE', '{s.BRIGHT}{f.MAGENTA}'),
		('DEBUG', '{s.DIM}{f.BLACK}'),
		('PROCESS', '{s.BRIGHT}{f.BLUE}'),
		('DEPENDS', '{f.GREEN}'),
		('in:INFO,P_PROPS,OUTPUT,EXPORT,INPUT,P_ARGS,BLDING,SBMTING,RUNNING,JOBDONE,KILLING',
		 '{f.MAGENTA}'),
		('CMDERR', '{s.BRIGHT}{f.YELLOW}'),
		('has:ERR', '{f.RED}'),
		('in:WARNING,RTRYING,RESUMED,SKIPPED', '{s.BRIGHT}{f.YELLOW}'),
		('in:WORKDIR,CACHED,P_DONE', '{f.YELLOW}'),
		('', ''),
	]),
)

LEVELS = {
	'all'   : set(['INPUT', 'OUTPUT', 'P_ARGS', 'P_PROPS', 'DEBUG', 'WARNING']),
	'basic' : set(),
	'normal': set(['INPUT', 'OUTPUT', 'P_ARGS', 'P_PROPS', 'WARNING'])
}

LEVELS_ALWAYS = set([
	'PROCESS', 'WORKDIR', 'RESUMED', 'SKIPPED', 'DEPENDS', 'STDOUT', 'STDERR', 'ERROR', 'PLUGIN',
	'INFO', 'DONE', 'EXPORT', 'PYPPL', 'TIPS', 'CONFIG', 'CMDOUT', 'CMDERR', 'BLDING',
	'SBMTING', 'RUNNING', 'RTRYING', 'JOBDONE', 'KILLING', 'P_DONE', 'CACHED'
])

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
	"""
	The theme for the logger
	"""
	def __init__(self, theme = 'greenOnBlack'):
		if theme is True:
			theme = 'greenOnBlack'
		if not theme:
			self.theme = {}
		elif isinstance(theme, dict):
			self.theme = theme
		elif theme in THEMES:
			self.theme = THEMES[theme]
		else:
			raise ValueError('No such theme: %s' % theme)

		self.colors = dict(
			Style = colorama.Style, s = colorama.Style,
			Back  = colorama.Back,  b = colorama.Back,
			Fore  = colorama.Fore,  f = colorama.Fore,
		)

	def getColor(self, level):
		"""
		Get the color for a given level
		@params:
			`level`: The level
		@returns:
			The color of the level by the theme.
		"""
		level = level.upper()
		for key, val in self.theme.items():
			if key == level:
				return val.format(**self.colors)
			if key.startswith('in:') and level in key[3:].split(','):
				return val.format(**self.colors)
			if key.startswith('starts:') and level.startswith(key[7:]):
				return val.format(**self.colors)
			if key.startswith('has:') and key[4:] in level:
				return val.format(**self.colors)
			if key.startswith('re:') and re.search(key[3:], level):
				return val.format(**self.colors)
		return ''

class StreamFormatter(logging.Formatter):
	"""
	Logging formatter for stream (sys.stderr)
	"""
	def __init__(self, theme):
		logging.Formatter.__init__(self, LOGFMT, LOGTIMEFMT)
		self.theme = theme

	def format(self, record):
		if hasattr(record, 'formatted') and record.formatted:
			return record.formatted

		# save the formatted, for all handlers
		level = record.mylevel
		record.msg = str(record.msg)
		if '\n' in record.msg:
			record.tails = []
			msgs = record.msg.splitlines()
			record.msg = msgs[0]
			for msg in msgs[1:]:
				rec     = copy(record)
				rec.msg = msg
				self.format(rec)
				record.tails.append(rec)

		record.msg = ' {COLOR}{LEVEL}{RESET_ALL}] {COLOR}{PROC}{JOBS}{MSG}{RESET_ALL}'.format(
			COLOR     = self.theme.getColor(level),
			LEVEL     = level.rjust(7),
			RESET_ALL = colorama.Style.RESET_ALL,
			PROC      = record.proc + ': ' if record.proc else '',
			MSG       = record.msg,
			JOBS      = '' if record.jobidx is None else '[{ji}/{jt}] '.format(
				ji = str(record.jobidx + 1).zfill(len(str(record.joblen))),
				jt = record.joblen)
		)
		setattr(record, 'formatted', logging.Formatter.format(self, record))
		return record.formatted

class StreamHandler(logging.StreamHandler):
	"""
	Logging handler for stream (sys.stderr)
	"""
	DATA = {'prevbar': None, 'done': {}}

	def _emit(self, record, terminator = "\n"):
		prevterm = self.terminator
		self.terminator = terminator
		super(StreamHandler, self).emit(record)
		self.terminator = prevterm

	def emit(self, record):
		if record.ispbar:
			if record.done:
				proc = record.proc if hasattr(record, 'proc') else ''
				with self.lock:
					# make sure done pbar is only shown once.
					if not StreamHandler.DATA['done'].get(proc):
						self._emit(record, '\n')
						# clear previous pbars if any
						StreamHandler.DATA['prevbar'] = None
						StreamHandler.DATA['done'][proc] = True
			else:
				self._emit(record, '\r')
				StreamHandler.DATA['prevbar'] = record
		else:
			pbarlog = StreamHandler.DATA['prevbar']
			if pbarlog:
				self.stream.write(' ' * len(pbarlog.formatted) + '\r')

			self._emit(record, '\n')
			if hasattr(record, 'tails'):
				for tail in record.tails:
					self._emit(tail, '\n')

			if pbarlog:
				self._emit(pbarlog, '\r')

class StreamFilter(logging.Filter):
	"""
	Logging filter for stream (sys.stderr)
	"""
	def __init__(self, name, levels):
		super(StreamFilter, self).__init__(name)
		self.levels = levels
		self.debugs = {}

	def filter(self, record):
		# logging is disabled
		if not self.levels:
			return False

		level = record.mylevel
		dlevel = record.dlevel if hasattr(record, 'dlevel') else None
		# user logs
		if level.startswith('_') or \
			(level in self.levels and \
			(not dlevel or dlevel not in DEBUG_LINES)): # debug
			return True

		if level not in self.levels or \
			not hasattr(record, 'proc') or not record.proc: # independent
			return False

		# the limitation is only for one process
		if record.proc not in self.debugs:
			self.debugs = {record.proc: dict(zip(DEBUG_LINES.keys(), [0] * len(DEBUG_LINES)))}

		self.debugs[record.proc][dlevel] += 1
		allowed_lines = abs(DEBUG_LINES[dlevel])
		print_summary = DEBUG_LINES[dlevel] < 0
		if self.debugs[record.proc][dlevel] > allowed_lines:
			return False
		if self.debugs[record.proc][dlevel] < allowed_lines:
			return True
		# ==
		if print_summary:
			record.msg += "\n...... max={max} ({dlevel}) reached".format(
				max = allowed_lines, dlevel = dlevel)
			record.msg += ", further information will be ignored."
		return True

class FileFilter(StreamFilter):
	"""
	Logging filter for file
	"""
	def filter(self, record):
		if (record.ispbar and not record.done) or not hasattr(record, 'formatted'):
			return False
		return super(FileFilter, self).filter(record)

class FileFormatter(logging.Formatter):
	"""
	Logging formatter for file,
	Extends StreamFormatter, removes the terminal colors
	"""
	def __init__(self):
		logging.Formatter.__init__(self, LOGFMT, LOGTIMEFMT)
		self.ansiRegex = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

	def format(self, record):
		# record has already been formatted by StreamFormatter
		# just remove the colors
		if hasattr(record, 'formatted'):
			return self.ansiRegex.sub('', record.formatted)
		return super(FileFormatter, self).format(record)

class Logger(object):
	"""@API
	A wrapper of logger
	"""
	@staticmethod
	def initLevels(levels, leveldiffs):
		"""@API
		Initiate the levels, get real levels.
		@params:
			levels (str|list): The levels or level names
			leveldiffs (str|list): The diffs of levels
		@returns:
			(set): The real levels.
		"""
		ret = set()
		if isinstance(levels, (tuple, list, set)):
			ret |= set(levels)
			ret |= LEVELS_ALWAYS
		elif levels not in (None, False):
			if levels is True:
				levels = 'normal'
			if levels.lower() in LEVELS:
				ret |= LEVELS[levels.lower()]
			elif levels:
				ret.add(levels)
			ret |= LEVELS_ALWAYS

		if not leveldiffs:
			return ret
		if not isinstance(leveldiffs, (tuple, list, set)):
			leveldiffs = set([leveldiffs])
		for level in leveldiffs:
			level = level.upper()
			if level.startswith('-'):
				level = level[1:]
				if level in ret:
					ret.remove(level)
			else:
				if level.startswith('+'):
					level = level[1:]
				ret.add(level)
		return ret

	def __init__(self, name = 'PyPPL', bake = False):
		"""@API
		The logger wrapper construct
		@params:
			name (str): The logger name. Default: `PyPPL`
			bake (dict): The arguments to bake a new logger.
		"""
		self.baked  = bake or {}
		self.name   = name
		self.ispbar = False
		if bake:
			self.logger = logging.getLogger(self.name)
		else:
			self.init()

	def init(self, conf = None):
		"""@API
		Initiate the logger, called by the construct,
		Just in case, we want to change the config and
		Reinitiate the logger.
		@params:
			conf (Config): The configuration used to initiate logger.
		"""
		if not conf:
			conf = config
		else:
			conf2 = config.copy()
			conf2.update(conf)
			conf = conf2

		self.logger = logging.getLogger(self.name)
		self.logger.setLevel(1)
		for handler in self.logger.handlers:
			handler.close()
		del self.logger.handlers[:]

		theme = Theme(conf._log.theme)
		levels = Logger.initLevels(conf._log.levels, conf._log.leveldiffs)

		stream_handler = StreamHandler()
		stream_handler.addFilter(StreamFilter(self.name, levels))
		stream_handler.setFormatter(StreamFormatter(theme))
		self.logger.addHandler(stream_handler)

		if conf._log.file:
			file_handler = logging.FileHandler(conf._log.file)
			file_handler.addFilter(FileFilter(self.name, levels))
			file_handler.setFormatter(FileFormatter())
			self.logger.addHandler(file_handler)

	def bake(self, **kwargs):
		"""@API
		Bake the logger with certain arguments
		@params
			*kwargs: arguments used to bake a new logger
		@returns:
			(Logger): The new logger.
		"""
		return self.__class__(self.name, bake = kwargs)

	@property
	def pbar(self):
		"""@API
		Mark the record as a progress record.
		Allow `logger.pbar.info` access
		@returns:
			(Logger): The Logger object itself
		"""
		self.ispbar = True
		return self

	def _emit(self, *args, **kwargs):
		extra = {'jobidx': None, 'proc': '', 'done': False}
		extra.update(self.baked)
		extra.update({'mylevel': kwargs.pop('_level')})
		extra.update(kwargs.pop('_extra'))
		extra.update(kwargs.pop('extra', {}))
		extra.update(kwargs)
		self.logger.info(*args, extra = extra)

	def __getitem__(self, name):
		"""@API
		Alias of `__getattr__`"""
		return self.__getattr__(name)

	def __getattr__(self, name):
		"""@API
		Allows logger.info way to specify the level
		@params:
			name (str): The level name.
		@returns:
			(callable): The logger with the level
		"""
		ispbar = self.ispbar
		self.ispbar = False
		return partial(self._emit, _level = name.upper(), _extra = dict(
			ispbar = ispbar, dlevel = None))

# pylint: disable=invalid-name
logger = Logger()
