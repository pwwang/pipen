import pytest

from os import environ
environ['PYPPL_default__log'] = "py:{'file': None, 'theme': 'greenOnBlack', 'levels': 'all', 'leveldiffs': [], 'pbar': 50, 'shorten': 0}"
from pyppl import Job
from pyppl.exceptions import RunnerClassNameError
pytest_plugins = ["tests.fixt_job"]

def test_init(job0):
	assert job0.index == 0
	assert job0.dir.name == '1'
	assert job0.fout is None
	assert job0.ferr is None
	assert job0.lastout == ''
	assert job0.lasterr == ''
	assert job0.ntry == 0
	assert job0.input == {}
	assert job0.output == {}
	assert job0.config == {}
	assert job0.script.name == 'job.script.test'
	assert job0._rc is None
	assert job0._pid is None

def test_scriptParts(job0):
	assert job0.scriptParts.header == ''
	assert job0.scriptParts.pre == ''
	assert job0.scriptParts.post == ''
	assert job0.scriptParts.saveoe is True
	assert job0.scriptParts.command == [str(job0.dir / 'job.script')]

def test_data(job0):
	assert job0.data.job.index == 0
	assert job0.data.job.indir == str(job0.dir / 'input')
	assert job0.data.job.outdir == str(job0.dir / 'output')
	assert job0.data.job.dir == str(job0.dir)
	assert job0.data.job.outfile == str(job0.dir / 'job.stdout')
	assert job0.data.job.errfile == str(job0.dir / 'job.stderr')
	assert job0.data.job.pidfile == str(job0.dir / 'job.pid')
	assert job0.data.job.cachedir == str(job0.dir / 'output' / '.jobcache')
	job0.input = {'infile': ('file', 'indata')}
	job0.output = {'outfile': ('file', 'outdata')}
	assert job0.data.i == {'infile': 'indata'}
	assert job0.data.o == {'outfile': 'outdata'}
	assert job0.data.proc.errhow == 'terminate'

def test_logger(job0, caplog):
	job0.logger('hello world!', level = 'info')
	assert 'pProc: [1/1] hello world!' in caplog.text

def test_checkClassName():
	with pytest.raises(RunnerClassNameError):
		Job(None, None)

def test_wrapScript(job0, job1):
	job0.wrapScript()
	assert job0.script.read_text() == """#!/usr/bin/env bash
#
# Collect return code on exit
trap "status = \\$?; echo \\$status > '{jobdir}/job.rc'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
#
# Run pre-script
#
# Run the real script
{jobdir}/job.script 1> {jobdir}/job.stdout 2> {jobdir}/job.stderr
#
# Run post-script
#""".format(jobdir = job0.dir)

	job1.wrapScript()
	assert job1.script.read_text() == """#!/usr/bin/env bash
#
# Collect return code on exit
trap "status = \\$?; echo \\$status > '{jobdir}/job.rc'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
#
# Run pre-script
pre
#
# Run the real script
command 1> {jobdir}/job.stdout 2> {jobdir}/job.stderr
#
# Run post-script
post
#""".format(jobdir = job1.dir)

def test_showError(job0, caplog):
	job0.showError(10)
	assert 'Failed (totally 10).' in caplog.text
	assert 'Rcfile not generated' in caplog.text
	assert '/1/job.script' in caplog.text
	assert '/1/job.stdout' in caplog.text
	assert '/1/job.stderr' in caplog.text
	job0.rc = 10
	job0.showError(10)
	assert 'Return code: 10.' in caplog.text
	job0.rc = (1 << 9) + 10
	job0.showError(10)
	assert '10 [Outfile not generated]' in caplog.text
	job0.rc = (1 << 9) + (1 << 10) + 10
	job0.showError(10)
	assert '10 [Outfile not generated; Expectation not met]' in caplog.text
	job0.rc = 510
	job0.showError(10)
	assert 'Submission failed' in caplog.text
	# stderr
	job0.proc.echo.jobs = []
	job0.showError(10)
	assert 'Check STDERR below:' in caplog.text
	assert '<EMPTY STDERR>' in caplog.text

	(job0.dir / 'job.stderr').write_text('\n'.join([
		'STDERR %s.' % (i+1) for i in range(21)
	]))
	job0.showError(10)
	assert 'Check STDERR below:' in caplog.text
	assert 'STDERR 2.' in caplog.text
	assert 'STDERR 1.' not in caplog.text
	assert 'Top 1 line(s) ignored' in caplog.text
	# ignore
	job0.proc.errhow = 'ignore'
	job0.showError(10)
	assert 'Failed but ignored' in caplog.text

def test_reportitem(job0, caplog):
	job0._reportItem('key', 5, 'abc', 'report')
