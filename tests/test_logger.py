import sys
import logging
import pytest
from pyppl.logger import Theme, THEMES, StreamFormatter, StreamHandler, StreamFilter, \
	FileFilter, FileFormatter, Logger, LEVEL_GROUPS, default_config, get_group, init_levels, get_value

def test_theme_init():
	theme = Theme(True)
	assert theme.theme == THEMES['green_on_black']

	theme = Theme(False)
	assert theme.theme == {}

	theme = Theme({'a': 1})
	assert theme.theme == {'a': 1}

	with pytest.raises(ValueError):
		Theme('nosuchtheme')

def test_get_value():
	assert get_value('_123') == 80
	assert get_value('PROCESS') == 80

def test_theme_get_color():
	THEMES['test'] = THEMES['green_on_black'].copy()
	theme = Theme('test')
	assert theme.get_color('DONE') == THEMES['test'][get_group('DONE')].format(**Theme.COLORS)
	assert theme.get_color('INFO') == THEMES['test']['CRITICAL'].format(**Theme.COLORS)
	assert theme.get_color('ABCDEF') == ''
	assert theme.get_color('ERROR') == THEMES['green_on_black']['ERROR'].format(**Theme.COLORS)
	assert theme.get_color('NOTEXIST') == ''

def test_stream_formatter():
	sfmt = StreamFormatter(Theme())
	record = logging.makeLogRecord(dict())
	record.formatted = 'This is a logging record.'
	assert sfmt.format(record) == record.formatted

	record = logging.makeLogRecord(dict(
		msg     = "This is logging record.",
		mylevel = "INFO",
		proc    = '',
		jobidx  = None
	))
	assert sfmt.format(record).endswith('\x1b[32m   INFO\x1b[0m] \x1b[32mThis is logging record.\x1b[0m')

	record = logging.makeLogRecord(dict(
		msg     = "This is logging record1.\nThis is logging record2.",
		mylevel = "INFO",
		proc    = 'pProc',
		jobidx  = 0,
		joblen  = 10,
	))
	assert sfmt.format(record).endswith('\x1b[32m   INFO\x1b[0m] \x1b[32mpProc: [01/10] This is logging record1.\x1b[0m')
	assert len(record.tails) == 1
	assert record.tails[0].formatted.endswith('\x1b[32m   INFO\x1b[0m] \x1b[32mpProc: [01/10] This is logging record2.\x1b[0m')

def test_stream_handler(capsys):
	StreamHandler.DATA = {'prevbar': None, 'done': {}}
	shandler = StreamHandler()
	record1 = logging.makeLogRecord(dict(
		msg     = "This is logging record1.",
		mylevel = "INFO",
		proc    = '',
		ispbar  = False,
		jobidx  = None
	))
	shandler.emit(record1)
	assert 'This is logging record1.' in capsys.readouterr().err

	record2 = logging.makeLogRecord(dict(
		msg     = "This is logging record2.",
		mylevel = "INFO",
		proc    = 'pProc',
		ispbar  = True,
		done    = True,
		jobidx  = None
	))

	shandler.emit(record2)
	assert 'This is logging record2.\n' in capsys.readouterr().err
	assert StreamHandler.DATA['prevbar'] is None
	assert StreamHandler.DATA['done']['pProc']

	record3 = logging.makeLogRecord(dict(
		msg       = "This is logging record3.",
		formatted = "This is logging record3 formatted.",
		mylevel   = "INFO",
		proc      = 'pProc',
		ispbar    = True,
		done      = False,
		jobidx    = None
	))
	shandler.emit(record3)
	assert 'This is logging record3.\r' in capsys.readouterr().err
	assert StreamHandler.DATA['prevbar'] is record3

	record4 = logging.makeLogRecord(dict(
		msg     = "This is logging record4.",
		mylevel = "INFO",
		proc    = 'pProc',
		ispbar  = False,
		tails   = [record3]
	))
	shandler.emit(record4)
	err = capsys.readouterr().err
	assert 'This is logging record4.\n' in err
	assert 'This is logging record3.\r' in err

def test_stream_filter():
	sfilter = StreamFilter('pyppl', [])
	record = logging.makeLogRecord(dict(
		msg     = "This is logging record1.",
		mylevel = "INFO",
	))
	assert not sfilter.filter(record)

	sfilter = StreamFilter('pyppl', ['INFO'])
	assert sfilter.filter(record)

	record = logging.makeLogRecord(dict(
		msg     = "This is logging record1.",
		mylevel = "LOG",
	))
	assert not sfilter.filter(record)

	record = logging.makeLogRecord(dict(
		msg     = "This is logging record1.",
		mylevel = "_LOG",
	))
	assert sfilter.filter(record)

	record = logging.makeLogRecord(dict(
		msg     = "This is logging record1.",
		mylevel = "INFO",
		proc    = 'pProc',
		slevel  = 'CACHE_FAILED'
	))
	assert sfilter.filter(record)
	assert sfilter.subs['pProc']['CACHE_FAILED'] == 1
	assert not sfilter.filter(record)

	record = logging.makeLogRecord(dict(
		msg     = "This is logging record1.",
		mylevel = "INFO",
		proc    = 'pProc',
		slevel  = 'SCRIPT_UPDATED'
	))
	assert sfilter.filter(record)
	assert sfilter.filter(record)
	assert not sfilter.filter(record)
	assert 'further information will be ignored.' in record.msg

	record = logging.makeLogRecord(dict(
		msg     = "This is logging record1.",
		mylevel = "INFO",
		slevel  = 'SCRIPT_UPDATED'
	))
	assert not sfilter.filter(record)

	# sub sublevel
	record = logging.makeLogRecord(dict(
		msg     = "This is logging record1.",
		mylevel = "INFO",
		proc    = 'SomeProc',
		slevel  = 'NEW_SUBLEVEL'
	))
	assert sfilter.filter(record)
	assert sfilter.filter(record)
	logger = Logger()
	logger.add_sublevel('NEW_SUBLEVEL', 1)
	assert sfilter.filter(record)
	assert not sfilter.filter(record)

def test_file_filter():
	ffilter = FileFilter('pyppl', ['INFO'])
	record = logging.makeLogRecord(dict(
		msg     = "This is logging record1.",
		mylevel = "INFO",
		ispbar  = False,
	))
	assert not ffilter.filter(record)

	record = logging.makeLogRecord(dict(
		msg       = "This is logging record1.",
		formatted = "This is logging record1.",
		mylevel   = "INFO",
		ispbar    = False,
	))
	assert ffilter.filter(record)

def test_file_formatter():
	ffmt = FileFormatter()
	record = logging.makeLogRecord(dict(
		msg       = "This is logging record1.",
		#formatted = "\x1b[31mThis is logging record2.\x1b[0m",
		mylevel   = "INFO",
		ispbar    = False,
	))
	assert 'This is logging record1.' in ffmt.format(record)

	record = logging.makeLogRecord(dict(
		msg       = "This is logging record1.",
		formatted = "\x1b[31mThis is logging record2.\x1b[0m",
		mylevel   = "INFO",
		ispbar    = False,
	))
	assert ffmt.format(record) == 'This is logging record2.'

def test_logger_init_levels():
	# using issuperset instead of ==, because plugins can add levels
	assert init_levels('TITLE', []).issuperset({'PROCESS'})
	assert init_levels(True, []).issuperset({'PROCESS', 'DONE', 'DEPENDS', 'WORKDIR', 'CACHED', 'P_DONE', 'INFO', 'CONFIG', 'PLUGIN', 'PYPPL', 'TIPS',
		'BLDING', 'SBMTING', 'RUNNING', 'JOBDONE', 'KILLING', 'RTRYING', 'ERROR', 'WARNING'})
	assert init_levels('DEBUG', []).issuperset({'BLDING', 'CACHED', 'DEBUG', 'DEPENDS', 'ERROR', 'INFO', 'JOBDONE', 'KILLING', 'PROCESS', 'P_DONE', 'RTRYING', 'RUNNING', 'SBMTING', 'WARNING', 'WORKDIR', 'DONE', 'CONFIG', 'PLUGIN', 'PYPPL', 'TIPS'})
	assert init_levels('CRITICAL', ['+DEBUG', '-WORKDIR']).issuperset({'BLDING', 'CACHED', 'DEBUG', 'DEPENDS', 'INFO', 'JOBDONE', 'KILLING', 'PROCESS', 'P_DONE', 'RUNNING', 'SBMTING', 'DONE'})
	assert init_levels('TITLE', 'DEBUG').issuperset({'PROCESS', 'DEBUG'})

def test_logger_init(tmpdir):
	logger = Logger(bake = True)
	default_config.logger.file = tmpdir / 'logger.txt'
	logger.init()
	assert len(logger.logger.handlers) == 2

	logger.init({'file': False})
	assert len(logger.logger.handlers) == 1

def test_logger_bake():
	logger = Logger()
	logger2 = logger.bake(a = 1, b = 2)
	assert logger2.baked == {'a': 1, 'b': 2}

def test_logger_pbar():
	logger = Logger()
	assert logger.pbar is logger
	assert logger.ispbar

def test_logger_emit(caplog):
	logger = Logger()
	logger._emit('This is a message.', _level = 'INFO', _extra = {'ispbar': False})
	assert 'This is a message.' in caplog.text

def test_logger_getattr(caplog):
	logger = Logger()
	logger.info('Hello world!')
	assert 'Hello world!' in caplog.text
	caplog.clear()
	logger['info']('Hello world2!')
	assert 'Hello world2!' in caplog.text

def test_logger_add_level():
	logger = Logger()
	assert init_levels('TITLE', []) == {'PROCESS', 'DONE'}
	logger.add_level('NOLEVEL', 'TITLE')
	assert init_levels('TITLE', []) == {'PROCESS', 'DONE', 'NOLEVEL'}

	with pytest.raises(ValueError):
		logger.add_level('NOLEVEL', 'nosuchgroup')

