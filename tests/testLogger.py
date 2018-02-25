import helpers, unittest, logging

from os import path
from pyppl import logger
from pyppl.logger import LEVELS, LEVELS_ALWAYS, COLORS, THEMES, PyPPLLogFilter, PyPPLLogFormatter
from pyppl.exception import TemplatePyPPLRenderError, LoggerThemeError

class TestPyPPLLogFilter(helpers.TestCase):

	def dataProvider_testInit(self):
		yield '', 'normal', None, LEVELS['normal'] + LEVELS_ALWAYS
		yield '', 'ALL', None, LEVELS['all'] + LEVELS_ALWAYS
		yield '', 'DEBUG', None, ['DEBUG'] + LEVELS_ALWAYS
		yield '', 'ONLY', None, ['ONLY'] + LEVELS_ALWAYS
		yield '', ['INPUT', 'OUTPUT'], None, ['INPUT', 'OUTPUT'] + LEVELS_ALWAYS
		yield '', None, None, []
		yield '', None, ['INPUT'], ['INPUT']
		yield '', None, ['+INPUT'], ['INPUT']
		yield '', [], ['INPUT'], ['INPUT'] + LEVELS_ALWAYS
		yield '', ['INPUT', 'OUTPUT'], ['-OUTPUT'], ['INPUT'] + LEVELS_ALWAYS

	def testInit(self, name, lvls, lvldiff, outlvls):
		pf = PyPPLLogFilter(name, lvls, lvldiff)
		self.assertIsInstance(pf, PyPPLLogFilter)
		if outlvls is None:
			self.assertIsNone(pf.levels)
		else:
			self.assertItemEqual(pf.levels,  list(set(outlvls)))

	def dataProvider_testFilter(self):
		r = logging.LogRecord(
			name     = 'noname',
			pathname = __file__,
			args     = None,
			exc_info = None,
			level    = logging.INFO,
			lineno   = 10,
			msg      = '',
		)
		yield '', False, None, r, '[INFO]', False
		yield '', False, None, r, '[_INFO]', False
		yield '', 'ONLY', None, r, '[DEBUG2]', False
		yield '', 'ONLY', None, r, '[ONLY]', True
		yield '', 'ONLY', None, r, '[PROCESS]', True
		yield '', [], ['ONLY'], r, '[PROCESS]', True
		yield '', None, ['ONLY'], r, '[PROCESS]', False
		yield '', None, ['ONLY'], r, '[_a]', True
		yield '', 'all', None, r, '[debug]', True
		yield '', 'nodebug', None, r, '[debug]', False

	def testFilter(self, name, lvls, lvldiff, record, msg, out):
		pf = PyPPLLogFilter(name, lvls, lvldiff)
		record.msg = msg
		self.assertEqual(pf.filter(record), out)


class TestPyPPLLogFormatter(helpers.TestCase):

	def dataProvider_testInit(self):
		yield None, {}
		yield None, 'greenOnBlank'

	def testInit(self, fmt, theme):
		lf = PyPPLLogFormatter(fmt, theme)
		self.assertIsInstance(lf, PyPPLLogFormatter)
		self.assertEqual(lf.theme, theme)

	def dataProvider_testFormat(self):
		yield None, True, '[info]a', '[%s   INFO%s] %sa%s' % (COLORS.green, COLORS.end, COLORS.green, COLORS.end)
		yield None, 'greenOnBlack', '[info]a', '[%s   INFO%s] %sa%s' % (COLORS.green, COLORS.end, COLORS.green, COLORS.end)
		yield None, 'magentaOnWhite', '[info]a', '[%s   INFO%s] %sa%s' % (COLORS.magenta, COLORS.end, COLORS.magenta, COLORS.end)
		yield None, 'greenOnBlack', '[warning] ', '[%sWARNING%s] %s%s' % (COLORS.bold + COLORS.yellow, COLORS.end, COLORS.bold + COLORS.yellow, COLORS.end)
		yield None, 'greenOnBlack', '[warning] ', '[%sWARNING%s] %s%s' % (COLORS.bold + COLORS.yellow, COLORS.end, COLORS.bold + COLORS.yellow, COLORS.end)
		yield None, '', '[warning] ', '[%sWARNING%s] %s%s' % ('', '', '', '')
		yield None, None, '[warning] ', '[%sWARNING%s] %s%s' % ('', '', '', '')

	def testFormat(self, fmt, theme, msg, out):
		r = logging.LogRecord(
			name     = 'noname',
			pathname = __file__,
			args     = None,
			exc_info = None,
			level    = logging.INFO,
			lineno   = 10,
			msg      = '',
		)
		r.msg = msg
		lf = PyPPLLogFormatter(fmt, theme)
		f  = lf.format(r)
		t  = lf.formatTime(r, fmt if fmt else "[%Y-%m-%d %H:%M:%S]")
		self.assertEqual(f[:21], t)
		self.assertEqual(f[21:], out)


class TestLogger(helpers.TestCase):

	theme_done_key    = 'DONE'
	theme_debug_key   = 'DEBUG'
	theme_process_key = 'PROCESS'
	theme_submit_key  = 'in:SUBMIT,JOBDONE,INFO,P.PROPS,DEPENDS,OUTPUT,EXPORT,INPUT,P.ARGS,BRINGS'
	theme_error_key   = 'has:ERR'
	theme_warning_key = 'in:WARNING,RETRY'
	theme_running_key = 'in:CACHED,RUNNING,SKIPPED,RESUMED'
	theme_other_key   = ''

	def dataProvider_testGetLevel(self):
		r = logging.LogRecord(
			name     = 'noname',
			pathname = __file__,
			args     = None,
			exc_info = None,
			level    = logging.DEBUG,
			lineno   = 10,
			msg      = '',
		)
		yield r, '[debug]hi', ('DEBUG', 'hi'),
		yield r, '[le>.l] hi', ('LE>.L', 'hi'),
		yield r, '[123456789] hi', ('123456789', 'hi'),

	def testGetLevel(self, record, msg, out):
		record.msg   = msg
		self.assertTupleEqual(logger._getLevel(record), out)

	def dataProvider_testGetColorFromTheme(self):
		for tname in ['greenOnBlack', 'blueOnBlack', 'magentaOnBlack', 'greenOnWhite', 'blueOnWhite', 'magentaOnWhite']:
			yield tname, 'DONE', self.theme_done_key
			yield tname, 'DEBUG', self.theme_debug_key
			yield tname, 'PROCESS', self.theme_process_key
			yield tname, 'INFO', self.theme_submit_key
			yield tname, 'DEPENDS', self.theme_submit_key
			yield tname, 'ERRRRR', self.theme_error_key
			yield tname, 'WARNING', self.theme_warning_key
			yield tname, 'CACHED', self.theme_running_key
			yield tname, '123', self.theme_other_key
		
	def testGetColorFromTheme (self, tname, level, key):
		theme = THEMES[tname]
		c = theme[key] if key in theme else theme[self.theme_other_key]
		c = tuple(c) if isinstance(c, list) else (c, )
		c = c * 2 if len(c) == 1 else c
		ret = logger._getColorFromTheme(level, theme)
		ret = (tname, level) + ret # just indicate when test fails
		c   = (tname, level) + c
		self.assertTupleEqual(ret, c)

	def dataProvider_testFormatTheme(self):
		yield True, THEMES['greenOnBlack']
		yield False, False
		yield 1, None, LoggerThemeError
		yield {
			'DONE'    : "{{colors.bold}}{{colors.green}}",
			'DEBUG'   : "{{colors.bold}}{{colors.black}}",
			'PROCESS' : ["{{colors.bold}}{{colors.cyan}}", "{{colors.bold}}{{colors.cyan}}"],
			'in:SUBMIT,JOBDONE,INFO,P.PROPS,DEPENDS,OUTPUT,EXPORT,INPUT,P.ARGS,BRINGS': "{{colors.green}}",
			'has:ERR' : "{{colors.red}}",
			'in:WARNING,RETRY' : "\x1b[1m{{colors.yellow}}",
			'in:CACHED,RUNNING,SKIPPED,RESUMED': "{{colors.yellow}}",
			''        : "{{colors.white}}"
		}, THEMES['greenOnBlack']
		yield {
			'DONE': "{{colors.whatever}}"
		}, {}, TemplatePyPPLRenderError
		yield {
			'DONE': "{{a}} x"
		}, {}, TemplatePyPPLRenderError

	def testFormatTheme(self, tname, theme, exception = None):
		self.maxDiff = None
		if exception:
			self.assertRaises(exception, logger._formatTheme, tname)
		else:
			if theme is False:
				self.assertFalse(logger._formatTheme(tname))
			else:
				self.assertDictEqual(logger._formatTheme(tname), logger._formatTheme(theme))

	def dataProvider_testGetLogger(self, testdir):
		yield 'normal', True, None, None, '[info]a', '[%s   INFO%s] %sa%s' % (COLORS.green, COLORS.end, COLORS.green, COLORS.end)
		yield 'normal', None, None, None, '[info]a', '[   INFO] a'
		logfile = path.join(testdir, 'logfile.txt')
		yield 'normal', True, logfile, None, '[info]a', '[%s   INFO%s] %sa%s' % (COLORS.green, COLORS.end, COLORS.green, COLORS.end), '[   INFO] a'
		yield 'normal', None, logfile, None, '[info]a', '[   INFO] a', '[   INFO] a'

	def testGetLogger(self, levels, theme, logfile, lvldiff, msg, outs, fileouts = None):
		log2 = logger.getLogger()
		log = logger.getLogger(levels, theme, logfile, lvldiff)
		self.assertIs(log, log2)
		self.assertIsInstance(log, logging.Logger)
		self.assertEqual(len(log.handlers), int(bool(logfile)) + 1)
		with helpers.log2str(levels, theme, logfile, lvldiff) as (out, err):
			log.info(msg)
		self.assertEqual(err.getvalue().strip()[21:], outs)
		if logfile:
			self.assertInFile(fileouts, logfile)


if __name__ == '__main__':
	unittest.main(verbosity=2)