"""
Custome logger for PyPPL
@variables:
	LOG_FORMAT (str): The format of loggers
	LOGTIME_FORMAT (str): The format of time for loggers
	GROUP_VALUES (dict): The values for each level group
	LEVEL_GROUPS (dict): The groups of levels
	THEMES (dict): The builtin themes
	SUBLEVELS (dict): the sub levels used to limit loggers of the same type
"""
import re
import logging
from copy import copy
from functools import partial

import colorama
# Fore/Back: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
# Style: DIM, NORMAL, BRIGHT, RESET_ALL
from .config import config as default_config
from .plugin import pluginmgr

colorama.init(autoreset = False)

LOG_FORMAT     = "[%(asctime)s%(message)s"
LOGTIME_FORMAT = "%Y-%m-%d %H:%M:%S"

GROUP_VALUES = dict(
	TITLE    = 80,
	SUBTITLE = 70,
	STATUS   = 60,
	CRITICAL = 50,
	ERROR    = 40,
	WARNING  = 30,
	INFO     = 20,
	DEBUG    = 10,
	NOTSET   = 0
)

LEVEL_GROUPS = dict(
	TITLE    = ['PROCESS'],
	SUBTITLE = ['DEPENDS', 'DONE'],
	STATUS   = ['WORKDIR', 'CACHED', 'P_DONE'],
	CRITICAL = ['INFO', 'BLDING', 'SBMTING', 'RUNNING', 'JOBDONE', 'KILLING'],
	ERROR    = ['ERROR'],
	WARNING  = ['WARNING', 'RTRYING'],
	INFO     = ['PYPPL', 'PLUGIN', 'TIPS', 'CONFIG'],
	DEBUG    = ['DEBUG'],
)

THEMES = dict(
	green_on_black = dict(
		TITLE    = '{s.BRIGHT}{f.CYAN}',
		SUBTITLE = '{f.MAGENTA}',
		STATUS   = '{f.YELLOW}',
		CRITICAL = '{f.GREEN}',
		ERROR    = '{f.RED}',
		WARNING  = '{s.BRIGHT}{f.YELLOW}',
		DEBUG    = '{s.DIM}{f.WHITE}',
		NOTSET   = ''
	),

	blue_on_black = dict(
		TITLE    = '{s.BRIGHT}{f.CYAN}',
		SUBTITLE = '{f.GREEN}',
		STATUS   = '{f.YELLOW}',
		CRITICAL = '{f.BLUE}',
		ERROR    = '{f.RED}',
		WARNING  = '{s.BRIGHT}{f.YELLOW}',
		DEBUG    = '{s.DIM}{f.WHITE}',
		NOTSET   = ''
	),

	magenta_on_black = dict(
		TITLE    = '{s.BRIGHT}{f.GREEN}',
		SUBTITLE = '{f.BLUE}',
		STATUS   = '{f.YELLOW}',
		CRITICAL = '{f.MAGENTA}',
		ERROR    = '{f.RED}',
		WARNING  = '{s.BRIGHT}{f.YELLOW}',
		DEBUG    = '{s.DIM}{f.WHITE}',
		NOTSET   = ''
	),

	green_on_white = dict(
		TITLE    = '{s.BRIGHT}{f.BLUE}',
		SUBTITLE = '{f.MAGENTA}',
		STATUS   = '{f.YELLOW}',
		CRITICAL = '{f.GREEN}',
		ERROR    = '{f.RED}',
		WARNING  = '{s.BRIGHT}{f.YELLOW}',
		DEBUG    = '{s.DIM}{f.BLACK}',
		NOTSET   = ''
	),

	blue_on_white = dict(
		TITLE    = '{s.BRIGHT}{f.GREEN}',
		SUBTITLE = '{f.MAGENTA}',
		STATUS   = '{f.YELLOW}',
		CRITICAL = '{f.BLUE}',
		ERROR    = '{f.RED}',
		WARNING  = '{s.BRIGHT}{f.YELLOW}',
		DEBUG    = '{s.DIM}{f.BLACK}',
		NOTSET   = ''
	),

	magenta_on_white = dict(
		TITLE    = '{s.BRIGHT}{f.BLUE}',
		SUBTITLE = '{f.GREEN}',
		STATUS   = '{f.YELLOW}',
		CRITICAL = '{f.MAGENTA}',
		ERROR    = '{f.RED}',
		WARNING  = '{s.BRIGHT}{f.YELLOW}',
		DEBUG    = '{s.DIM}{f.BLACK}',
		NOTSET   = ''
	)
)

SUBLEVELS = {
	'CACHE_FAILED'              : -1,
	'CACHE_INPUT_MODIFIED'      : -1,
	'CACHE_OUTPUT_MODIFIED'     : -1,
	'INFILE_RENAMING'           : -1,
	'INFILE_EMPTY'              : -1,
	'SUBMISSION_FAIL'           : -3,
	'OUTFILE_NOT_EXISTS'        : -1,
	'OUTDIR_CREATED_AFTER_RESET': -1,
	'SCRIPT_EXISTS'             : -2,
	'JOB_RESETTING'             : -1,
}

def get_group(level):
	"""@API
	Get the group name of the level
	@params:
		level (str): The level, should be UPPERCASE
	@returns:
		(str): The group name
	"""
	for group, levels in LEVEL_GROUPS.items():
		if level in levels:
			return group
	return 'NOTSET'

def get_value(level):
	"""@API
	Get the value of the level
	@params:
		level (str): The level, should be UPPERCASE
	@returns:
		(int): The value of the group where the level is in.
	"""
	if level[:1] == '_':
		return max(GROUP_VALUES.values())
	return GROUP_VALUES.get(get_group(level), 0)

class Theme: # pylint: disable=too-few-public-methods
	"""@API
	The theme for the logger
	@variables:
		COLORS (dict): Color collections used to format theme
	"""
	COLORS = dict(
		Style = colorama.Style, s = colorama.Style,
		Back  = colorama.Back,  b = colorama.Back,
		Fore  = colorama.Fore,  f = colorama.Fore,
	)

	def __init__(self, theme = 'green_on_black'):
		"""@API
		Construct for Theme
		@params:
			theme (str): the name of the theme
		"""
		if theme is True:
			theme = 'green_on_black'
		if not theme:
			self.theme = {}
		elif isinstance(theme, dict):
			self.theme = theme
		elif theme in THEMES:
			self.theme = THEMES[theme]
		else:
			raise ValueError('No such theme: %s' % theme)

	def get_color(self, level):
		"""@API
		Get the color for a given level
		@params:
			`level`: The level
		@returns:
			The color of the level by the theme.
		"""
		group = get_group(level.upper())
		return self.theme.get(group, '').format(**Theme.COLORS)

class StreamFormatter(logging.Formatter):
	"""
	Logging formatter for stream (sys.stderr)
	"""
	def __init__(self, theme):
		logging.Formatter.__init__(self, LOG_FORMAT, LOGTIME_FORMAT)
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
			COLOR     = self.theme.get_color(level),
			LEVEL     = level.rjust(7),
			RESET_ALL = colorama.Style.RESET_ALL,
			PROC      = record.proc + ': ' \
				if hasattr(record, 'proc') and record.proc else '',
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

class StreamFilter(logging.Filter): # pylint: disable=too-few-public-methods
	"""
	Logging filter for stream (sys.stderr)
	"""
	def __init__(self, name, levels):
		super(StreamFilter, self).__init__(name)
		self.levels = levels
		self.subs = {}

	def filter(self, record):
		# logging is disabled
		if not self.levels:
			return False

		level = record.mylevel
		slevel = record.slevel if hasattr(record, 'slevel') else None
		proc = record.proc if hasattr(record, 'proc') else ''

		# user logs
		if level[0] == '_':
			return True
		if level not in self.levels:
			return False
		if not slevel or slevel not in SUBLEVELS:
			return True
		if not proc:
			return False

		# the limitation is only for one process
		if proc not in self.subs:
			self.subs = {proc: dict(zip(SUBLEVELS.keys(), [0] * len(SUBLEVELS)))}

		self.subs[proc][slevel] += 1
		allowed_lines = abs(SUBLEVELS[slevel])
		print_summary = SUBLEVELS[slevel] < 0
		if self.subs[proc][slevel] > allowed_lines:
			return False
		if self.subs[proc][slevel] < allowed_lines:
			return True
		# ==
		if print_summary:
			record.msg += "\n...... max={max} ({slevel}) reached".format(
				max = allowed_lines, slevel = slevel)
			record.msg += ", further information will be ignored."
		return True

class FileFilter(StreamFilter): # pylint: disable=too-few-public-methods
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
		logging.Formatter.__init__(self, LOG_FORMAT, LOGTIME_FORMAT)
		self.ansi_regex = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

	def format(self, record):
		# record has already been formatted by StreamFormatter
		# just remove the colors
		if hasattr(record, 'formatted'):
			return self.ansi_regex.sub('', record.formatted)
		return super(FileFormatter, self).format(record)

def init_levels(group, leveldiffs):
	"""@API
	Initiate the levels, get real levels.
	@params:
		group (str): The group of levels
		leveldiffs (str|list): The diffs of levels
	@returns:
		(set): The real levels.
	"""
	value  = GROUP_VALUES.get(group, GROUP_VALUES['INFO'])
	groups = [key for key in GROUP_VALUES
		if GROUP_VALUES[key] >= value]
	ret    = set(level for group in groups
		for level in LEVEL_GROUPS.get(group, []))

	if not leveldiffs:
		return ret
	if not isinstance(leveldiffs, (tuple, list, set)):
		leveldiffs = set([leveldiffs])
	for level in leveldiffs:
		prefix = level[:1] if level[:1] in ('+', '-') else '+'
		level  = level[1:] if level[:1] in ('+', '-') else level
		level  = level.upper()
		if prefix == '-' and level in ret:
			ret.remove(level)
		elif prefix == '+':
			ret.add(level)
	return ret

class Logger:
	"""@API
	A wrapper of logger
	"""

	__slots__ = ('baked', 'name', 'ispbar', 'logger')

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

	def init(self, config = None):
		"""@API
		Initiate the logger, called by the construct,
		Just in case, we want to change the config and as default_config
		Reinitiate the logger.
		@params:
			conf (Config): The configuration used to initiate logger.
		"""
		config = config or default_config.logger
		config2 = default_config.logger.copy()
		config2.update(config)
		config = config2

		self.logger = logging.getLogger(self.name)
		self.logger.setLevel(1)
		for handler in self.logger.handlers:
			handler.close()
		del self.logger.handlers[:]
		pluginmgr.hook.logger_init(logger = self)

		theme  = Theme(config.theme)
		levels = init_levels(config.level.upper(), config.leveldiffs)

		stream_handler = StreamHandler()
		stream_handler.addFilter(StreamFilter(self.name, levels))
		stream_handler.setFormatter(StreamFormatter(theme))
		self.logger.addHandler(stream_handler)

		if config.file:
			file_handler = logging.FileHandler(config.file)
			file_handler.addFilter(FileFilter(self.name, levels))
			file_handler.setFormatter(FileFormatter())
			self.logger.addHandler(file_handler)

	def add_level(self, level, group = 'INFO'): # pylint: disable=no-self-use
		"""@API
		@params:
			level (str): The log level name
				Make sure it's less than 7 characters
			group (str): The group the level is to be added
		"""
		level = level.upper()
		group = group.upper()
		if group not in LEVEL_GROUPS:
			raise ValueError('No such level group: {}, available ones are: {}'.format(
				group, list(LEVEL_GROUPS.keys())
			))
		if level not in LEVEL_GROUPS[group]:
			LEVEL_GROUPS[group].append(level)

	def add_sublevel(self, slevel, lines = -1): # pylint: disable=no-self-use
		"""@API
		@params:
			slevel (str): The debug level
			lines (int): The number of lines allowed for the debug level
				- Negative value means a summary will be printed
		"""
		SUBLEVELS[slevel.upper()] = lines

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
			ispbar = ispbar, slevel = None))

	__getitem__ = __getattr__

# pylint: disable=invalid-name
logger = Logger()
