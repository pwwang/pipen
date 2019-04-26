import testly, logging, helpers, sys

from os import path, makedirs
from shutil import rmtree
from tempfile import gettempdir
from pyppl.logger import logger, LEVELS, LEVELS_ALWAYS, colorama, THEMES, StreamFormatter, StreamHandler, StreamFilter, FileFilter, FileFormatter, Logger, Theme
from pyppl.exception import LoggerThemeError
Fore, Back, Style = colorama.Fore, colorama.Back, colorama.Style

class TestFilter(testly.TestCase):

	def dataProvider_testStreamFilter(self):
		r = logging.LogRecord(
			name     = 'noname',
			pathname = __file__,
			args     = None,
			exc_info = None,
			level    = logging.INFO,
			lineno   = 10,
			msg      = '',
		)
		yield '', False, None, r, 'INFO', False
		yield '', [], None, r, '_INFO', True
		yield '', 'ONLY', None, r, 'DEBUG2', False
		yield '', 'ONLY', None, r, 'ONLY', True
		yield '', 'ONLY', None, r, 'ONLY', False, FileFilter, True
		#5
		yield '', 'ONLY', None, r, 'ONLY', True, FileFilter, True, True
		yield '', 'ONLY', None, r, 'PROCESS', True
		yield '', [], ['ONLY'], r, 'PROCESS', True
		yield '', None, ['ONLY'], r, 'PROCESS', False
		yield '', None, ['ONLY'], r, '_a', True
		yield '', 'all', None, r, 'DEBUG', True


	def testStreamFilter(self, name, levels, leveldiffs, record, msg, out, logfilter = StreamFilter, ispbar = False, done = False):
		pf = logfilter(name, Logger.initLevels(levels, leveldiffs))
		record.mylevel = msg
		record.ispbar = ispbar
		record.done = done
		self.assertEqual(pf.filter(record), out)

class TestFormatter(testly.TestCase):

	def dataProvider_testInit(self):
		yield None, {}
		yield None, 'greenOnBlack'

	def testInit(self, fmt, theme):
		lf = StreamFormatter(Theme(theme))
		self.assertIsInstance(lf, StreamFormatter)
		self.assertEqual(lf.theme.theme, THEMES[theme] if str(theme) in THEMES else theme)

	def dataProvider_testFormat(self):
		yield None, True, 'INFO', '[info]a', '%s   INFO%s] %s[info]a%s' % (Fore.GREEN, Style.RESET_ALL, Fore.GREEN, Style.RESET_ALL)
		yield None, 'greenOnBlack', 'INFO', '[info]a', '%s   INFO%s] %s[info]a%s' % (Fore.GREEN, Style.RESET_ALL, Fore.GREEN, Style.RESET_ALL)
		yield None, 'magentaOnWhite', 'INFO', '[info]a', '%s   INFO%s] %s[info]a%s' % (Fore.MAGENTA, Style.RESET_ALL, Fore.MAGENTA, Style.RESET_ALL)
		yield None, 'greenOnBlack', 'INFO', '[warning] ', '%s   INFO%s] %s[warning] %s' % (Fore.GREEN, Style.RESET_ALL, Fore.GREEN, Style.RESET_ALL)
		yield None, '', 'INFO', '[warning] ', '   INFO%s] [warning] %s' % ((Style.RESET_ALL, ) * 2)
		yield None, None, 'INFO', '[warning] ', '   INFO%s] [warning] %s' % ((Style.RESET_ALL, ) * 2)

		yield None, True, 'INFO', '[info]a', '   INFO] [info]a', True
		yield None, 'greenOnBlack', 'INFO', '[info]a', '   INFO] [info]a', True
		yield None, 'magentaOnWhite', 'INFO', '[info]a', '   INFO] [info]a', True
		yield None, 'greenOnBlack', 'INFO', '[warning] ', '   INFO] [warning] ', True
		yield None, '', 'INFO', '[warning] ', '   INFO] [warning] ', True
		yield None, None, 'INFO', '[warning] ', '   INFO] [warning] ', True

	def testFormat(self, fmt, theme, level, msg, out, fileformatter = False):
		r = logging.LogRecord(
			name     = 'noname',
			pathname = __file__,
			args     = None,
			exc_info = None,
			level    = logging.INFO,
			lineno   = 10,
			msg      = '',
		)
		r.jobidx  = None
		r.proc    = ''
		r.mylevel = level
		r.msg     = msg
		lf        = StreamFormatter(Theme(theme))
		f         = lf.format(r)
		if fileformatter:
			ff = FileFormatter()
			f  = ff.format(r)
		self.assertEqual(f[21:], out)

class TestStreamHandler(testly.TestCase):

	def dataProvider_test_emit(self):
		record  = logging.makeLogRecord(dict(
			level = logging.INFO,
			msg   = u'whatever msg1'
		))
		yield record, '\n', 'whatever msg1'

	def test_emit(self, record, terminator, outs):
		with self.assertStdOE() as (out, err):
			handler = StreamHandler(sys.stderr)
			handler._emit(record, terminator)
		self.assertIn(outs, err.getvalue())

	def dataProvider_testEmit(self):
		
		yield logging.makeLogRecord(dict(
			level = logging.INFO,
			msg   = 'whatever msg1'
		)), 'whatever msg1'

		yield logging.makeLogRecord(dict(
			level = logging.INFO,
			msg   = '[ SUBMIT] job1 submitted'
		)), 'job1 submitted'

		yield logging.makeLogRecord(dict(
			level = logging.INFO,
			msg   = '[JOBDONE] job1 done'
		)), 'job1 done'

		yield [
			logging.makeLogRecord(dict(
				level = logging.INFO,
				msg   = '[JOBDONE] job1 done'
			)), 
			logging.makeLogRecord(dict(
				level = logging.INFO,
				msg   = 'job2 done'
			)), 
		], 'job2 done'
	
	def testEmit(self, records, outs):
		if not isinstance(records, list):
			records = [records]
		with self.assertStdOE() as (out, err):
			handler = StreamHandler(sys.stderr)
			for record in records:
				record.ispbar = False
				handler.emit(record)
		self.assertIn(outs, err.getvalue())

class TestLogger(testly.TestCase):

	theme_done_key    = 'DONE'
	theme_debug_key   = 'DEBUG'
	theme_process_key = 'PROCESS'
	theme_depends_key = 'DEPENDS'
	theme_submit_key  = 'in:INFO,P_PROPS,OUTPUT,EXPORT,INPUT,P_ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING'
	theme_error_key   = 'has:ERR'
	theme_warning_key = 'in:WARNING,RETRY,RESUMED,SKIPPED'
	theme_running_key = 'in:WORKDIR,CACHED,P_DONE'
	theme_other_key   = ''
	
	def dataProvider_testInitLevels(self):
		yield None, None, set()
		yield 'normal', None, LEVELS['normal'] | LEVELS_ALWAYS
		yield 'ALL', None, LEVELS['all'] | LEVELS_ALWAYS
		yield 'DEBUG', None, set(['DEBUG']) | LEVELS_ALWAYS
		yield 'ONLY', None, set(['ONLY']) | LEVELS_ALWAYS
		#5
		yield ['INPUT', 'OUTPUT'], None, {'INPUT', 'OUTPUT'} | LEVELS_ALWAYS
		yield None, ['INPUT'], set(['INPUT'])
		yield None, ['+INPUT'], set(['INPUT'])
		yield [], ['INPUT'], set(['INPUT']) | LEVELS_ALWAYS
		yield ['INPUT', 'OUTPUT'], ['-OUTPUT'], set(['INPUT']) | LEVELS_ALWAYS
	
	def testInitLevels(self, levels, leveldiffs, retlevels):
		self.assertSetEqual(Logger.initLevels(levels, leveldiffs), retlevels)
	
	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestLogger')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def dataProvider_testGetColorFromTheme(self):
		for tname in ['greenOnBlack', 'blueOnBlack', 'magentaOnBlack', 'greenOnWhite', 'blueOnWhite', 'magentaOnWhite']:
			# 0, 9, 18, 27, 36
			yield tname, 'DONE', self.theme_done_key
			yield tname, 'DEBUG', self.theme_debug_key
			yield tname, 'PROCESS', self.theme_process_key
			yield tname, 'INFO', self.theme_submit_key
			yield tname, 'DEPENDS', self.theme_depends_key
			yield tname, 'ERRRRR', self.theme_error_key
			yield tname, 'WARNING', self.theme_warning_key
			yield tname, 'CACHED', self.theme_running_key
			yield tname, '123', self.theme_other_key
		
	def testGetColorFromTheme (self, tname, level, key):
		theme = Theme(tname)
		ret = theme.getColor(level)
		excolor = THEMES[tname][key].format(**theme.colors)
		self.assertEqual(ret, excolor, msg = tname + ', ' + level + ', color different, got %r, expect %r' % (ret, excolor))

if __name__ == '__main__':
	testly.main(verbosity=2)