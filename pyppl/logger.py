"""
A customized logger for pyppl
"""
import logging, re, sys, signal
from copy import copy as pycopy
from multiprocessing.managers import SyncManager
from .utils import Box, pickle
from .exception import LoggerThemeError
from .template import TemplateLiquid

MANAGER = SyncManager()
MANAGER.start(signal.signal, (signal.SIGINT, signal.SIG_IGN))

# the entire format
LOGFMT = "[%(asctime)s%(message)s"
# colors
COLORS = Box(
	none = '',        end       = '\033[0m',
	bold = '\033[1m', underline = '\033[4m',

	# regular colors
	black = '\033[30m', red     = '\033[31m',
	green = '\033[32m', yellow  = '\033[33m',
	blue  = '\033[34m', magenta = '\033[35m',
	cyan  = '\033[36m', white   = '\033[37m',
	# bgcolors
	bgblack = '\033[40m', bgred     = '\033[41m',
	bggreen = '\033[42m', bgyellow  = '\033[43m',
	bgblue  = '\033[44m', bgmagenta = '\033[45m',
	bgcyan  = '\033[46m', bgwhite   = '\033[47m',
)
# the themes
# keys:
# - no colon: match directory
# - in: from the the list
# - starts: startswith the string
# - re: The regular expression to match
# - has: with the string in flag
THEMES = {
	'greenOnBlack': {
		'DONE'    : COLORS.bold + COLORS.green,
		'DEBUG'   : COLORS.bold + COLORS.black,
		'PROCESS' : [COLORS.bold + COLORS.cyan, COLORS.bold + COLORS.cyan],
		'DEPENDS' : COLORS.magenta,
		'in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING': COLORS.green,
		'has:ERR' : COLORS.red,
		'in:WARNING,RETRY,RESUMED,SKIPPED' : COLORS.bold + COLORS.yellow,
		'in:WORKDIR,CACHED,P.DONE': COLORS.yellow,
		''        : COLORS.white
	},
	'blueOnBlack':  {
		'DONE'    : COLORS.bold + COLORS.blue,
		'DEBUG'   : COLORS.bold + COLORS.black,
		'PROCESS' : [COLORS.bold + COLORS.cyan, COLORS.bold  + COLORS.cyan],
		'DEPENDS' : COLORS.green,
		'in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING': COLORS.blue,
		'has:ERR' : COLORS.red,
		'in:WARNING,RETRY,RESUMED,SKIPPED' : COLORS.bold + COLORS.yellow,
		'in:WORKDIR,CACHED,P.DONE': COLORS.yellow,
		''        : COLORS.white
	},
	'magentaOnBlack':  {
		'DONE'    : COLORS.bold + COLORS.magenta,
		'DEBUG'   : COLORS.bold + COLORS.black,
		'PROCESS' : [COLORS.bold + COLORS.green, COLORS.bold + COLORS.green],
		'DEPENDS' : COLORS.blue,
		'in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING': COLORS.magenta,
		'has:ERR' : COLORS.red,
		'in:WARNING,RETRY,RESUMED,SKIPPED' : COLORS.bold + COLORS.yellow,
		'in:WORKDIR,CACHED,P.DONE': COLORS.yellow,
		''        : COLORS.white
	},
	'greenOnWhite': {
		'DONE'    : COLORS.bold + COLORS.green,
		'DEBUG'   : COLORS.bold + COLORS.black,
		'PROCESS' : [COLORS.bold + COLORS.blue, COLORS.bold + COLORS.blue],
		'DEPENDS' : COLORS.magenta,
		'in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING': COLORS.green,
		'has:ERR' : COLORS.red,
		'in:WARNING,RETRY,RESUMED,SKIPPED' : COLORS.bold + COLORS.yellow,
		'in:WORKDIR,CACHED,P.DONE': COLORS.yellow,
		''        : COLORS.black
	},
	'blueOnWhite':  {
		'DONE'    : COLORS.bold + COLORS.blue,
		'DEBUG'   : COLORS.bold + COLORS.black,
		'PROCESS' : [COLORS.bold + COLORS.green, COLORS.bold + COLORS.green],
		'DEPENDS' : COLORS.magenta,
		'in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING': COLORS.blue,
		'has:ERR' : COLORS.red,
		'in:WARNING,RETRY,RESUMED,SKIPPED' : COLORS.bold + COLORS.yellow,
		'in:WORKDIR,CACHED,P.DONE': COLORS.yellow,
		''        : COLORS.black
	},
	'magentaOnWhite':  {
		'DONE'    : COLORS.bold + COLORS.magenta,
		'DEBUG'   : COLORS.bold + COLORS.black,
		'PROCESS' : [COLORS.bold + COLORS.blue, COLORS.bold + COLORS.blue],
		'DEPENDS' : COLORS.green,
		'in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING': COLORS.magenta,
		'has:ERR' : COLORS.red,
		'in:WARNING,RETRY,RESUMED,SKIPPED' : COLORS.bold + COLORS.yellow,
		'in:WORKDIR,CACHED,P.DONE': COLORS.yellow,
		''        : COLORS.black
	}
}

LEVELS = {
	'all':     ['INPUT', 'OUTPUT', 'P.ARGS', 'P.PROPS', 'DEBUG'],
	'basic':   [],
	'normal':  ['INPUT', 'OUTPUT', 'P.ARGS', 'P.PROPS']
}

LEVELS_ALWAYS = ['PROCESS', 'WORKDIR', 'RESUMED', 'SKIPPED', 'DEPENDS', 'STDOUT', 'STDERR', 'WARNING', 'ERROR', 'INFO', 'DONE', 'EXPORT', 'PYPPL', 'TIPS', 'CONFIG', 'CMDOUT', 'CMDERR', 'BLDING', 'SUBMIT', 'RUNNING', 'RETRY', 'JOBDONE', 'KILLING', 'P.DONE', 'CACHED']

DEBUG_LINES = {
	'EXPORT_CACHE_OUTFILE_EXISTS': -1,
	'EXPORT_CACHE_USING_SYMLINK': 1,
	'EXPORT_CACHE_USING_EXPARTIAL': 1,
	'EXPORT_CACHE_EXFILE_NOTEXISTS': 1,
	'EXPORT_CACHE_EXDIR_NOTSET': 1,
	'CACHE_EMPTY_PREVSIG': -1,
	'CACHE_EMPTY_CURRSIG': -2,
	'CACHE_SCRIPT_NEWER': -1,
	'CACHE_SIGINVAR_DIFF': -1,
	'CACHE_SIGINFILE_DIFF': -1,
	'CACHE_SIGINFILE_NEWER': -1,
	'CACHE_SIGINFILES_DIFF': -1,
	'CACHE_SIGINFILES_NEWER': -1,
	'CACHE_SIGOUTVAR_DIFF': -1,
	'CACHE_SIGOUTFILE_DIFF': -1,
	'CACHE_SIGOUTDIR_DIFF': -1,
	'CACHE_SIGFILE_NOTEXISTS': -1,
	'EXPECT_CHECKING': -1,
	'INFILE_RENAMING': -1,
	'SUBMISSION_FAIL': -3,
	#'BRINGFILE_NOTFOUND': -3,
	'OUTFILE_NOT_EXISTS': -1,
	'OUTDIR_CREATED_AFTER_RESET': -1,
	'SCRIPT_EXISTS': -2,
	'JOB_RESETTING': -1
}

def _getColorFromTheme (level, theme):
	"""
	Get colors from a them
	@params:
		`level`: Our own log record level
		`theme`: The theme
	@returns:
		The colors
	"""
	ret = theme[''] if isinstance(theme[''], list) else [theme['']] * 2
	level = level.upper()
	
	for key, val in theme.items():
		if not isinstance(val, list):
			val = [val] * 2
		if key == level or \
		   key.startswith('in:') and level in key[3:].split(',') or \
		   key.startswith('starts:') and level.startswith(key[7:]) or \
		   key.startswith('has:') and key[4:] in level or \
		   key.startswith('re:') and re.search(key[3:], level):
			ret = val
			break
	return tuple(ret)
	
def _formatTheme(theme):
	"""
	Make them in the standard form with bgcolor and fgcolor in raw terminal color strings
	If the theme is read from file, try to translate "COLORS.xxx" to terminal color strings
	@params:
		`theme`: The theme
	@returns:
		The formatted colors
	"""
	if theme is True:
		theme = THEMES['greenOnBlack']
	if not theme:
		return False
	if not isinstance(theme, dict):
		raise LoggerThemeError(theme, 'No such theme')
	
	ret = {'': [COLORS.white, COLORS.white]}
	for key, val in theme.items():
		if not isinstance(val, list):
			val = [val]
		if len(val) == 1:
			val = val * 2

		for i, v in enumerate(val):
			t = TemplateLiquid(v, colors = COLORS)
			val[i] = t.render()

		ret[key] = val
	return ret
	
class PyPPLLogFilter (logging.Filter):
	"""
	logging filter by levels (flags)
	"""

	DEBUGS = MANAGER.dict()
	LEVELS = []

	@staticmethod
	def _clearDebug():
		for key in DEBUG_LINES.keys():
			PyPPLLogFilter.DEBUGS[key] = 0
	
	def __init__(self, name='', lvls='normal', lvldiff=None):
		"""
		Constructor
		@params:
			`name`: The name of the logger
			`lvls`: The levels of records to keep
			`lvldiff`: The adjustments to `lvls`
		"""

		logging.Filter.__init__(self, name)
		PyPPLLogFilter.LEVELS[:] = []
		
		if lvls is not None:
			if not isinstance(lvls, list):
				if lvls in LEVELS:
					PyPPLLogFilter.LEVELS += LEVELS[lvls]
				elif lvls == 'ALL':
					PyPPLLogFilter.LEVELS += LEVELS['all']
				elif lvls:
					PyPPLLogFilter.LEVELS += [lvls]
				elif lvls is False:
					return
			else:
				PyPPLLogFilter.LEVELS += lvls

			PyPPLLogFilter.LEVELS += LEVELS_ALWAYS
			
		lvldiff = lvldiff or []
		if not isinstance(lvldiff, list):
			lvldiff = [lvldiff]
		for ld in lvldiff:
			if ld.startswith('-'):
				ld = ld[1:].upper()
				if ld in PyPPLLogFilter.LEVELS: 
					del PyPPLLogFilter.LEVELS[PyPPLLogFilter.LEVELS.index(ld)]
			elif ld.startswith('+'):
				ld = ld[1:].upper()
				if ld not in PyPPLLogFilter.LEVELS:
					PyPPLLogFilter.LEVELS.append(ld)
			else:
				ld = ld.upper()
				if ld not in PyPPLLogFilter.LEVELS:
					PyPPLLogFilter.LEVELS.append(ld)
	
	def filter (self, record):
		"""
		Filter the record
		@params:
			`record`: The record to be filtered
		@return:
			`True` if the record to be kept else `False`
		"""
		level = record.loglevel.upper() if hasattr(record, 'loglevel') else record.levelname
		if level.startswith('_'):
			return True
		if not PyPPLLogFilter.LEVELS:
			return False
		if level in PyPPLLogFilter.LEVELS:
			level2 = record.level2 if hasattr(record, 'level2') else None
			if not level2 or level2 not in DEBUG_LINES:
				return True
			PyPPLLogFilter.DEBUGS[level2] += 1
			if PyPPLLogFilter.DEBUGS[level2] <= abs(DEBUG_LINES[level2]):
				if DEBUG_LINES[level2] < 0 and PyPPLLogFilter.DEBUGS[level2] == abs(DEBUG_LINES[level2]):
					record.msg += "\n...... max={max} ({key}) reached, further information will be ignored.".format(max = abs(DEBUG_LINES[level2]), key = level2)
				return True
		return False

class PyPPLLogFormatter (logging.Formatter):
	"""
	logging formatter for pyppl
	"""
	def __init__(self, fmt=None, theme='greenOnBlack', secondary = False):
		"""
		Constructor
		@params:
			`fmt`      : The format
			`theme`    : The theme
			`secondary`: Whether this is a secondary formatter or not (another formatter applied before this).
		"""
		fmt = LOGFMT if fmt is None else fmt
		logging.Formatter.__init__(self, fmt, "%Y-%m-%d %H:%M:%S")
		self.theme     = theme
		# whether it's a secondary formatter (for fileHandler)
		self.secondary = secondary
		
	def format(self, record):
		"""
		Format the record
		@params:
			`record`: The log record
		@returns:
			The formatted record
		"""
		formatted = record.formatted if hasattr(record, 'formatted') else False
		if not formatted:
			level = record.loglevel.upper() if hasattr(record, 'loglevel') else record.levelname
			theme = 'greenOnBlack' if self.theme is True else self.theme
			theme = THEMES[theme] if not isinstance(theme, dict) and theme in THEMES else theme
			theme = _formatTheme(theme)

			if not theme:
				colorLevelStart = COLORS.none
				colorLevelEnd   = COLORS.none
				colorMsgStart   = COLORS.none
				colorMsgEnd     = COLORS.none
			else:
				(colorLevelStart, colorMsgStart) = _getColorFromTheme(level, theme)
				colorLevelEnd   = COLORS.end
				colorMsgEnd     = COLORS.end
			
			if self.secondary:
				# keep _ for file handler
				level = level[1:] if level.startswith('_') else level
			level = level[:7]
			record.msg = " {lstart_c}{level}{lend_c}] {mstart_c}{proc}{jobindex}{msg}{mend_c}".format(
				lstart_c = colorLevelStart,
				level    = level.rjust(7),
				lend_c   = colorLevelEnd,
				mstart_c = colorMsgStart,
				proc     = '{}: '.format(record.proc) if hasattr(record, 'proc') else '',
				jobindex = '[{ji}/{jt}] '.format(ji = str(record.jobidx + 1).zfill(len(str(record.joblen))), jt = record.joblen) if hasattr(record, 'jobidx') else '',
				msg      = record.msg,
				mend_c   = colorMsgEnd)
			setattr(record, 'formatted', True)
		return logging.Formatter.format(self, record)

class PyPPLStreamHandler(logging.StreamHandler):
	"""
	PyPPL stream log handler.
	To implement the progress bar for JOBONE and SUBMIT logs.
	"""

	PREVBAR = MANAGER.list([''])

	def __init__(self, stream = None):
		"""
		Constructor
		@params:
			`stream`: The stream
		"""
		super(PyPPLStreamHandler, self).__init__(stream)

	def _emit(self, record, terminator = "\n"):
		"""
		Helper function implementing a python2,3-compatible emit.
		Allow to add "\n" or "\r" as terminator.
		"""
		if sys.version_info.major > 2: # pragma: no cover
			self.terminator = terminator
			super(PyPPLStreamHandler, self).emit(record)
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
		"""
		Emit the record.
		"""
		from .jobmgr import Jobmgr
		try:
			pbar = record.pbar if hasattr(record, 'pbar') else None
			if pbar == 'next':
				if PyPPLStreamHandler.PREVBAR[0]:
					self.stream.write("\n")
				self._emit(record, "\n")
			elif pbar is None:
				# break pbars
				if not "\n" in record.msg:
					self._emit(record, "\n")
				else:
					msgs = record.msg.splitlines()
					for i, m in enumerate(msgs):
						rec = pycopy(record)
						rec.msg = m
						if i == len(msgs) - 1 and m.startswith('...... max='):
							delattr(rec, 'jobidx')
						self._emit(rec, "\n")
				PyPPLStreamHandler.PREVBAR[0] = ''
			elif pbar is True:
				# pbar, replace previous pbar
				PyPPLStreamHandler.PREVBAR[0] = pickle.dumps(record)
				self._emit(record, "\r")
			elif not PyPPLStreamHandler.PREVBAR[0]:
				# not pbar and not prev pbar
				justlen = Jobmgr.PBAR_SIZE + 32
				if hasattr(record, 'proc'):
					justlen += len(record.proc) + 2
				if hasattr(record, 'jobidx'):
					justlen += len(str(record.joblen)) * 3
				justlen = max(justlen, Jobmgr.PBAR_SIZE + 32)
				if not "\n" in record.msg:
					record.msg = record.msg.ljust(justlen)
					self._emit(record, "\n")
				else:
					msgs = record.msg.splitlines()
					for i, m in enumerate(msgs):
						rec = pycopy(record)
						if i == len(msgs) - 1 and m.startswith('...... max='):
							rec.msg = m.ljust(justlen)
							delattr(rec, 'jobidx')
						else:
							rec.msg = m.ljust(justlen)
						self._emit(rec, "\n")
			else:
				# not pbar but prev pbar
				prevbar = pickle.loads(PyPPLStreamHandler.PREVBAR[0])
				justlen = Jobmgr.PBAR_SIZE + 32
				if hasattr(prevbar, 'proc'):
					justlen += len(prevbar.proc) + 2
				if hasattr(prevbar, 'jobidx'):
					justlen += len(str(prevbar.joblen)) * 3
				justlen = max(justlen, Jobmgr.PBAR_SIZE + 32)
				if not "\n" in record.msg:
					record.msg = record.msg.ljust(justlen)
					self._emit(record, "\n")
				else:
					msgs = record.msg.splitlines()
					for i, m in enumerate(msgs):
						rec = pycopy(record)
						if i == len(msgs) - 1 and m.startswith('...... max='):
							rec.msg = m.ljust(justlen)
							#delattr(rec, 'jobidx')
						else:
							rec.msg = m.ljust(justlen)
						self._emit(rec, "\n")
				self._emit(prevbar, "\r")
		except (KeyboardInterrupt, SystemExit, IOError, EOFError): # pragma: no cover
			raise
		except Exception: # pragma: no cover
			self.handleError(record)


def getLogger (levels='normal', theme=True, logfile=None, lvldiff=None, name='PyPPL'):
	"""
	Get the default logger
	@params:
		`levels`: The log levels(tags), default: basic
		`theme`:  The theme of the logs on terminal. Default: True (default theme will be used)
			- False to disable theme
		`logfile`:The log file. Default: None (don't white to log file)
		`lvldiff`:The diff levels for log
			- ["-depends", "jobdone", "+debug"]: show jobdone, hide depends and debug
		`name`:   The name of the logger, default: PyPPL
	@returns:
		The logger
	"""
	logger    = logging.getLogger (name)
	for handler in logger.handlers:
		handler.close()
	del logger.handlers[:]
	
	if logfile:
		fileCh = logging.FileHandler(logfile)
		fileCh.setFormatter(PyPPLLogFormatter(theme = None))
		logger.addHandler (fileCh)
		
	streamCh  = PyPPLStreamHandler()
	formatter = PyPPLLogFormatter(theme = theme, secondary = True)
	filter    = PyPPLLogFilter(name = name, lvls = levels, lvldiff = lvldiff)
	streamCh.addFilter(filter)
	streamCh.setFormatter(formatter)
	logger.addHandler (streamCh)
	
	logger.setLevel(1)
	# Output all logs
	return logger
	
logger = getLogger()