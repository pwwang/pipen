import testly, logging, helpers, sys

from os import path, makedirs
from shutil import rmtree
from tempfile import gettempdir
from pyppl import logger
from pyppl.logger import LEVELS, LEVELS_ALWAYS, COLORS, THEMES, PyPPLLogFilter, PyPPLLogFormatter, PyPPLStreamHandler
from liquid import LiquidRenderError
from pyppl.exception import LoggerThemeError

class TestPyPPLLogFilter(testly.TestCase):

	def dataProvider_testInit(self):
		yield '', 'normal', None, LEVELS['normal'] + LEVELS_ALWAYS
		yield '', 'ALL', None, LEVELS['all'] + LEVELS_ALWAYS
		yield '', 'DEBUG', None, ['DEBUG'] + LEVELS_ALWAYS
		yield '', 'ONLY', None, ['ONLY'] + LEVELS_ALWAYS
		yield '', ['INPUT', 'OUTPUT'], None, ['INPUT', 'OUTPUT'] + LEVELS_ALWAYS
		#5
		yield '', None, None, []
		yield '', None, ['INPUT'], ['INPUT']
		yield '', None, ['+INPUT'], ['INPUT']
		yield '', [], ['INPUT'], ['INPUT'] + LEVELS_ALWAYS
		yield '', ['INPUT', 'OUTPUT'], ['-OUTPUT'], ['INPUT'] + LEVELS_ALWAYS

	def testInit(self, name, lvls, lvldiff, outlvls):
		self.maxDiff = None
		PyPPLLogFilter.LEVELS[:] = []
		pf = PyPPLLogFilter(name, lvls, lvldiff)
		self.assertIsInstance(pf, PyPPLLogFilter)
		if outlvls is None:
			self.assertListEqual(list(pf.LEVELS), [])
		else:
			self.assertCountEqual(list(pf.LEVELS),  list(set(outlvls)))

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
		yield '', False, None, r, 'INFO', False
		yield '', False, None, r, '_INFO', True
		yield '', 'ONLY', None, r, 'DEBUG2', False
		yield '', 'ONLY', None, r, 'ONLY', True
		yield '', 'ONLY', None, r, 'PROCESS', True
		yield '', [], ['ONLY'], r, 'PROCESS', True
		yield '', None, ['ONLY'], r, 'PROCESS', False
		yield '', None, ['ONLY'], r, '_a', True
		yield '', 'all', None, r, 'debug', True
		yield '', 'nodebug', None, r, 'debug', False

	def testFilter(self, name, lvls, lvldiff, record, msg, out):
		pf = PyPPLLogFilter(name, lvls, lvldiff)
		record.loglevel = msg
		self.assertEqual(pf.filter(record), out)


class TestPyPPLLogFormatter(testly.TestCase):

	def dataProvider_testInit(self):
		yield None, {}
		yield None, 'greenOnBlank'

	def testInit(self, fmt, theme):
		lf = PyPPLLogFormatter(fmt, theme)
		self.assertIsInstance(lf, PyPPLLogFormatter)
		self.assertEqual(lf.theme, theme)

	def dataProvider_testFormat(self):
		yield None, True, '[info]a', '%s   INFO%s] %s[info]a%s' % (COLORS.green, COLORS.end, COLORS.green, COLORS.end)
		yield None, 'greenOnBlack', '[info]a', '%s   INFO%s] %s[info]a%s' % (COLORS.green, COLORS.end, COLORS.green, COLORS.end)
		yield None, 'magentaOnWhite', '[info]a', '%s   INFO%s] %s[info]a%s' % (COLORS.magenta, COLORS.end, COLORS.magenta, COLORS.end)
		yield None, 'greenOnBlack', '[warning] ', '%s   INFO%s] %s[warning] %s' % (COLORS.green, COLORS.end, COLORS.green, COLORS.end)
		yield None, '', '[warning] ', '   INFO] [%swarning%s] %s%s' % ('', '', '', '')
		yield None, None, '[warning] ', '   INFO] [%swarning%s] %s%s' % ('', '', '', '')

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
		t  = lf.formatTime(r, fmt if fmt else "[%Y-%m-%d %H:%M:%S ")
		self.assertEqual(f[:21], t)
		self.assertEqual(f[21:], out)

class TestPyPPLStreamHandler(testly.TestCase):

	def testInit(self):
		handler = PyPPLStreamHandler()
		self.assertListEqual(list(handler.PREVBAR), [''])

	def dataProvider_test_emit(self):
		record  = logging.makeLogRecord(dict(
			level = logging.INFO,
			msg   = u'whatever msg1'
		))
		yield record, '\n', 'whatever msg1'

	def test_emit(self, record, terminator, outs):
		with self.assertStdOE() as (out, err):
			handler = PyPPLStreamHandler(sys.stderr)
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
			handler = PyPPLStreamHandler(sys.stderr)
			for record in records:
				handler.emit(record)
		self.assertIn(outs, err.getvalue())

class TestLogger(testly.TestCase):

	theme_done_key    = 'DONE'
	theme_debug_key   = 'DEBUG'
	theme_process_key = 'PROCESS'
	theme_depends_key = 'DEPENDS'
	theme_submit_key  = 'in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING'
	theme_error_key   = 'has:ERR'
	theme_warning_key = 'in:WARNING,RETRY,RESUMED,SKIPPED'
	theme_running_key = 'in:WORKDIR,CACHED,P.DONE'
	theme_other_key   = ''

	
	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestLogger')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def dataProvider_testGetColorFromTheme(self):
		for tname in ['greenOnBlack', 'blueOnBlack', 'magentaOnBlack', 'greenOnWhite', 'blueOnWhite', 'magentaOnWhite']:
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
			'DEPENDS' : "{{colors.magenta}}",
			'in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING': "{{colors.green}}",
			'has:ERR' : "{{colors.red}}",
			'in:WARNING,RETRY,RESUMED,SKIPPED' : "\x1b[1m{{colors.yellow}}",
			'in:WORKDIR,CACHED,P.DONE': "{{colors.yellow}}",
			''        : "{{colors.white}}"
		}, THEMES['greenOnBlack']
		yield {
			'DONE': "{{colors.whatever}}"
		}, {}, LiquidRenderError
		yield {
			'DONE': "{{a}} x"
		}, {}, LiquidRenderError

	def testFormatTheme(self, tname, theme, exception = None):
		self.maxDiff = None
		if exception:
			self.assertRaises(exception, logger._formatTheme, tname)
		else:
			if theme is False:
				self.assertFalse(logger._formatTheme(tname))
			else:
				self.assertDictEqual(logger._formatTheme(tname), logger._formatTheme(theme))

	def dataProvider_testGetLogger(self):
		yield 'normal', True, None, None, '[info]a', '%s   INFO%s] %s[info]a%s' % (COLORS.green, COLORS.end, COLORS.green, COLORS.end)
		
		yield 'normal', None, None, None, '[info]a', '   INFO] [info]a'
		
		logfile = path.join(self.testdir, 'logfile.txt')
		yield 'normal', True, logfile, None, '[info]a', '   INFO] [info]a', '   INFO] [info]a'
		
		yield 'normal', None, logfile, None, '[debug]a', '   INFO] [debug]a', '   INFO] [debug]a'

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
			self.assertIn(fileouts, helpers.readFile(logfile))

	def dataProvider_testExtra(self):
		yield 'AAA', {}, ['AAA']
		yield 'AAA', {'pbar': 'next'}, ['AAA\n']
		yield 'AAA', {'pbar': True}, ['AAA\r']
		yield 'ABC\nDEF', {'pbar': None}, ['ABC', 'DEF']
		yield 'ABC\nDEF', {'pbar': False, 'proc': 'pProc', 'jobidx': 2, 'joblen': 10}, ['ABC', 'DEF']
		yield 'ABCDEF', {'pbar': False, 'proc': 'pProc', 'jobidx': 2, 'joblen': 10}, ['ABCDEF']
		yield 'ABCDEF', {'pbar': False, 'proc': 'pProc', 'jobidx': 2, 'joblen': 10, 'level2': 'INFILE_RENAMING'}, ['ABCDEF']

	def testExtra(self, msg, extra, outs):
		PyPPLLogFilter._clearDebug()
		log = logger.getLogger('all', None, lvldiff = 'DEBUG')
		with helpers.log2str('all', None, lvldiff = 'DEBUG') as (out, err):
			log.info(msg, extra = extra)
		for out in outs:
			self.assertIn(out, err.getvalue())

	def testMulti(self):
		PyPPLLogFilter._clearDebug()
		log = logger.getLogger('all', None, lvldiff = 'DEBUG')
		with helpers.log2str('all', None, lvldiff = 'DEBUG') as (out, err):
			log.info('ABC', extra = {'level2': 'EXPECT_CHECKING', 'jobidx': 1, 'joblen': 2})
			log.info('EFG', extra = {'level2': 'EXPECT_CHECKING', 'jobidx': 1, 'joblen': 2})
		self.assertIn('...... max=1 (EXPECT_CHECKING) reached', err.getvalue())
		self.assertIn('INFO] [2/2] ABC', err.getvalue())
		self.assertNotIn('EFG', err.getvalue())

	def testMulti1(self):
		PyPPLLogFilter._clearDebug()
		log = logger.getLogger('all', None, lvldiff = 'DEBUG')
		with helpers.log2str('all', None, lvldiff = 'DEBUG') as (out, err):
			log.info('ABC', extra = {'pbar': True, 'jobidx': 1, 'joblen': 2})
			log.info('EFG', extra = {'pbar': 'next', 'proc': 'p', 'jobidx': 1, 'joblen': 2})
		self.assertIn('INFO] [2/2] ABC\r\n', err.getvalue())
		self.assertIn('EFG\n', err.getvalue())

	def testMulti2(self):
		PyPPLLogFilter._clearDebug()
		log = logger.getLogger('all', None, lvldiff = 'DEBUG')
		with helpers.log2str('all', None, lvldiff = 'DEBUG') as (out, err):
			log.info('ABC', extra = {'pbar': False, 'proc': 'p', 'jobidx': 1, 'joblen': 2})
			log.info('EFG', extra = {'pbar': 'next', 'jobidx': 1, 'joblen': 2})
		self.assertIn('INFO] [2/2] ABC\r\n', err.getvalue())
		self.assertIn('EFG\n', err.getvalue())

	def testMulti3(self):
		PyPPLLogFilter._clearDebug()
		log = logger.getLogger('all', None, lvldiff = 'DEBUG')
		with helpers.log2str('all', None, lvldiff = 'DEBUG') as (out, err):
			log.info('ABC', extra = {'pbar': True, 'proc': 'p', 'jobidx': 1, 'joblen': 2})
			log.info('EFG', extra = {'pbar': False, 'proc': 'p', 'jobidx': 1, 'joblen': 2})
		self.assertIn('INFO] p: [2/2] ABC\r', err.getvalue())
		self.assertIn('EFG  ', err.getvalue())

	def testMulti4(self):
		PyPPLLogFilter._clearDebug()
		log = logger.getLogger('all', None, lvldiff = 'DEBUG')
		with helpers.log2str('all', None, lvldiff = 'DEBUG') as (out, err):
			log.info('ABC', extra = {'pbar': True, 'proc': 'p', 'jobidx': 1, 'joblen': 2})
			log.info('EFG\n...... max=', extra = {'pbar': False, 'proc': 'p', 'jobidx': 1, 'joblen': 2})
		self.assertIn('INFO] p: [2/2] ABC\r', err.getvalue())
		self.assertIn('EFG  ', err.getvalue())
		self.assertIn('...... max=', err.getvalue())

if __name__ == '__main__':
	testly.main(verbosity=2)