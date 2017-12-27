"""
A customized logger for pyppl
"""
import logging, re, sys
from box import Box

# the entire format
logfmt = "[%(asctime)s]%(message)s"
# colors
colors = Box({
	'none'      : '',
	'end'       : '\033[0m',
	'bold'      : '\033[1m',
	'underline' : '\033[4m',

	# regular colors
	'black'     : '\033[30m',   'red'       : '\033[31m',	'green'     : '\033[32m',	'yellow'    : '\033[33m',
	'blue'      : '\033[34m',   'magenta'   : '\033[35m',   'cyan'      : '\033[36m',   'white'     : '\033[37m',
	# bgcolors
	'bgblack'   : '\033[40m',   'bgred'     : '\033[41m',   'bggreen'   : '\033[42m',   'bgyellow'  : '\033[43m',
	'bgblue'    : '\033[44m',   'bgmagenta' : '\033[45m',   'bgcyan'    : '\033[46m',   'bgwhite'   : '\033[47m',
})
# the themes
# keys:
# - no colon: match directory
# - in: from the the list
# - starts: startswith the string
# - re: The regular expression to match
# - has: with the string in flag
themes = {
	'greenOnBlack': {
		'DONE'    : colors.bold + colors.green,
		'DEBUG'   : colors.bold + colors.black,
		'PROCESS' : [colors.bold + colors.cyan, colors.bold + colors.underline + colors.cyan],
		'in:SUBMIT,JOBDONE,INFO,P.PROPS,DEPENDS,OUTPUT,EXPORT,INPUT,P.ARGS,BRINGS': colors.green,
		'has:ERR' : colors.red,
		'in:WARNING,RETRY' : colors.bold + colors.yellow,
		'in:CACHED,RUNNING,SKIPPED,RESUMED': colors.yellow,
		''        : colors.white
	},
	'blueOnBlack':  {
		'DONE'    : colors.bold + colors.blue,
		'DEBUG'   : colors.bold + colors.black,
		'PROCESS' : [colors.bold + colors.cyan, colors.bold + colors.underline + colors.cyan],
		'in:SUBMIT,JOBDONE,INFO,P.PROPS,DEPENDS,OUTPUT,EXPORT,INPUT,P.ARGS,BRINGS': colors.blue,
		'has:ERR' : colors.red,
		'in:WARNING,RETRY' : colors.bold + colors.yellow,
		'in:CACHED,RUNNING,SKIPPED,RESUMED': colors.yellow,
		''        : colors.white
	},
	'magentaOnBlack':  {
		'DONE'    : colors.bold + colors.magenta,
		'DEBUG'   : colors.bold + colors.black,
		'PROCESS' : [colors.bold + colors.blue, colors.bold + colors.underline + colors.blue],
		'in:SUBMIT,JOBDONE,INFO,P.PROPS,DEPENDS,OUTPUT,EXPORT,INPUT,P.ARGS,BRINGS': colors.magenta,
		'has:ERR' : colors.red,
		'WARNING' : colors.bold + colors.yellow,
		'in:CACHED,RUNNING,SKIPPED,RESUMED': colors.yellow,
		''        : colors.white
	},
	'greenOnWhite': {
		'DONE'    : colors.bold + colors.green,
		'DEBUG'   : colors.bold + colors.black,
		'PROCESS' : [colors.bold + colors.blue, colors.bold + colors.underline + colors.blue],
		'in:SUBMIT,JOBDONE,INFO,P.PROPS,DEPENDS,OUTPUT,EXPORT,INPUT,P.ARGS,BRINGS': colors.green,
		'has:ERR' : colors.red,
		'in:WARNING,RETRY' : colors.bold + colors.yellow,
		'in:CACHED,RUNNING,SKIPPED,RESUMED': colors.yellow,
		''        : colors.black
	},
	'blueOnWhite':  {
		'DONE'    : colors.bold + colors.blue,
		'DEBUG'   : colors.bold + colors.black,
		'PROCESS' : [colors.bold + colors.magenta, colors.bold + colors.underline + colors.magenta],
		'in:SUBMIT,JOBDONE,INFO,P.PROPS,DEPENDS,OUTPUT,EXPORT,INPUT,P.ARGS,BRINGS': colors.blue,
		'has:ERR' : colors.red,
		'in:WARNING,RETRY' : colors.bold + colors.yellow,
		'in:CACHED,RUNNING,SKIPPED,RESUMED': colors.yellow,
		''        : colors.black
	},
	'magentaOnWhite':  {
		'DONE'    : colors.bold + colors.magenta,
		'DEBUG'   : colors.bold + colors.black,
		'PROCESS' : [colors.bold + colors.blue, colors.bold + colors.underline + colors.blue],
		'in:SUBMIT,JOBDONE,INFO,P.PROPS,DEPENDS,OUTPUT,EXPORT,INPUT,P.ARGS,BRINGS': colors.magenta,
		'has:ERR' : colors.red,
		'in:WARNING,RETRY' : colors.bold + colors.yellow,
		'in:CACHED,RUNNING,SKIPPED,RESUMED': colors.yellow,
		''        : colors.black
	}
}

levels = {
	'all':     'ALL',
	'basic':   [],
	'normal':  ['INPUT', 'OUTPUT', 'BRINGS', 'SUBMIT', 'P.PROPS'],
	'nodebug': ['INPUT', 'OUTPUT', 'BRINGS', 'SUBMIT', 'P.ARGS', 'P.PROPS', 'JOBDONE']
}

levels_always = ['PROCESS', 'SKIPPED', 'RESUMED', 'DEPENDS', 'STDOUT', 'STDERR', 'WARNING', 'ERROR', 'INFO', 'DONE', 'RUNNING', 'CACHED', 'EXPORT', 'PYPPL', 'TIPS', 'CONFIG', 'CMDOUT', 'CMDERR', 'RETRY']

def _getLevel (record):
	"""
	Get the flags of a record
	@params:
		`record`:  The logging record
	"""
	level = record.levelname
	msg   = record.msg.lstrip()
	m     = re.match(r'\[\s*([\w>.]+)\s*\](.*)', record.msg)
	if m:
		level = m.group(1).upper()
		msg   = m.group(2).lstrip()
	return (level, msg)

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
	If the theme is read from file, try to translate "colors.xxx" to terminal color strings
	@params:
		`theme`: The theme
	@returns:
		The formatted colors
	"""
	if theme is True:
		theme = themes['greenOnBlack']
	if not theme:
		return False
	if not isinstance(theme, dict):
		raise ValueError('Log theme not found: %s' % theme)
		
	replacements = {}
	for key, val in colors.items():
		replacements['colors.' + key] = val
	
	ret = {'': [colors.white, colors.white]}
	for key, val in theme.items():
		if not isinstance(val, list):
			val = [val]
		if len(val) == 1:
			val = val * 2
		# it's not a color, try to find colors.xxx keywords
		for i, v in enumerate(val):
			if v and not re.escape(v).startswith('\\'):
				for ck, cv in colors.items():
					exprStr = v.replace('colors.' + ck, '"' + cv + '"')
					try:
						val[i] = eval(exprStr)
					except (SyntaxError, AttributeError):
						sys.stderr.write('Cannot get colors in %s (%s)\n' % (exprStr, v))
						raise
			else:
				val[i] = v
		ret[key] = val
	return ret
	
class pFilter (logging.Filter):
	"""
	logging filter by levels (flags)
	"""
	
	def __init__(self, name='', lvls='normal', lvldiff=None):
		logging.Filter.__init__(self, name)
		if not isinstance(lvls, list) and lvls in levels:
			self.levels = levels[lvls]
		elif not isinstance(lvls, list) and not lvls is None:
			self.levels = [lvls]
		else:
			self.levels = lvls
		
		self.lvlhide = []
		self.lvlshow = []
		if not lvldiff: lvldiff = []
		for ld in lvldiff:
			if ld.startswith('-'):
				self.lvlhide.append(ld[1:].upper())
			elif ld.startswith('+'):
				self.lvlshow.append(ld[1:].upper())
			else:
				self.lvlshow.append(ld.upper())
	
	def filter (self, record):
		level   = _getLevel(record)[0]
		# disable logging
		if self.levels is None or level in self.lvlhide:
			return False
		if level in self.lvlshow  or \
		   self.levels == 'ALL'   or \
		   level.startswith('_')  or \
		   level in levels_always or \
		   level in self.levels:
			return True

class pFormatter (logging.Formatter):
	"""
	logging formatter for pyppl
	"""
	def __init__(self, fmt=None, theme='greenOnBlack'):
		fmt = logfmt if fmt is None else fmt
		logging.Formatter.__init__(self, fmt, "%Y-%m-%d %H:%M:%S")
		self.theme  = theme
		
	
	def format(self, record):
		(level, msg) = _getLevel(record)
		theme = 'greenOnBlack' if self.theme is True else self.theme
		theme = themes[theme] if not isinstance(theme, dict) and theme in themes else theme
		theme = _formatTheme(theme)
		
		if not theme:
			colorLevelStart = colors.none
			colorLevelEnd   = colors.none
			colorMsgStart   = colors.none
			colorMsgEnd     = colors.none
		else:
			(colorLevelStart, colorMsgStart) = _getColorFromTheme(level, theme)
			colorLevelEnd   = colors.end
			colorMsgEnd     = colors.end
		
		level = level[1:] if level.startswith('_') else level
		level = level[:7]
		record.msg = "[%s%7s%s] %s%s%s" % (colorLevelStart, level, colorLevelEnd, colorMsgStart, msg, colorMsgEnd)

		return logging.Formatter.format(self, record)


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
	logger.handlers = []
	streamCh  = logging.StreamHandler()
	streamCh.setFormatter (pFormatter(theme = theme))
	streamCh.addFilter(pFilter(name = name, lvls = levels, lvldiff = lvldiff))
	
	if logfile:
		fileCh = logging.FileHandler(logfile)
		fileCh.setFormatter(pFormatter(theme = None))
		logger.addHandler (fileCh)
	
	logger.addHandler (streamCh)
	logger.setLevel(1)
	# Output all logs
	return logger
	
logger = getLogger()