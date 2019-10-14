import pytest

from os import environ, utime
environ['PYPPL_default__log'] = "py:{'levels': 'all'}"
from pyppl.job import Job, JobInputParseError, JobOutputParseError, RC_NO_RCFILE
from pyppl.utils import fs, Box, OBox, filesig
from pyppl.template import TemplateLiquid
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
	caplog.clear()
	job0.logger('PBAR!', level = 'info', pbar = True)
	assert 'PBAR!' in caplog.text

def test_wrapScript(job0, job1):
	job0.wrapScript()
	assert job0.script.read_text() == """#!/usr/bin/env bash
#
# Collect return code on exit
trap "status=\\$?; echo \\$status > '{jobdir}/job.rc'; if [ ! -e '{jobdir}/job.stdout' ]; then touch '{jobdir}/job.stdout'; fi; if [ ! -e '{jobdir}/job.stderr' ]; then touch '{jobdir}/job.stderr'; fi; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
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
trap "status=\\$?; echo \\$status > '{jobdir}/job.rc'; if [ ! -e '{jobdir}/job.stdout' ]; then touch '{jobdir}/job.stdout'; fi; if [ ! -e '{jobdir}/job.stderr' ]; then touch '{jobdir}/job.stderr'; fi; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
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
	job0._reportItem(key = 'key', maxlen = 5, data = 'abc', loglevel = 'input')
	assert 'INPUT' in caplog.text
	assert 'pProc: [1/1] key   => abc' in caplog.text
	job0._reportItem(key = 'key', maxlen = 5, data = [], loglevel = 'input')
	assert 'pProc: [1/1] key   => [  ]' in caplog.text
	job0._reportItem(key = 'key', maxlen = 5, data = ['abc'], loglevel = 'input')
	assert 'pProc: [1/1] key   => [ abc ]' in caplog.text
	job0._reportItem(key = 'key', maxlen = 5, data = ['abc', 'def'], loglevel = 'input')
	assert 'pProc: [1/1] key   => [ abc,' in caplog.text
	assert 'pProc: [1/1]            def ]' in caplog.text
	job0._reportItem(key = 'key', maxlen = 5, data = ['abc', 'def', 'ghi'], loglevel = 'input')
	assert 'pProc: [1/1] key   => [ abc,' in caplog.text
	assert 'pProc: [1/1]            def,' in caplog.text
	assert 'pProc: [1/1]            ghi ]' in caplog.text
	job0._reportItem(key = 'key', maxlen = 5,
		data = ['abc', 'def', 'ghi', 'lmn'], loglevel = 'input')
	assert 'pProc: [1/1] key   => [ abc,' in caplog.text
	assert 'pProc: [1/1]            def,' in caplog.text
	assert 'pProc: [1/1]            ... (1),' in caplog.text
	assert 'pProc: [1/1]            lmn ]' in caplog.text

def test_report(job0, caplog):
	job0.proc._log.shorten = 10
	job0.input = Box(
		a = ('var', 'abcdefghijkmnopq'),
		bc = ('files', ['/long/path/to/file1']),
		de = ('file', '/long/path/to/file2'),
	)
	job0.output = Box(
		outfile = ('file', '/path/to/output/file1'),
		outfiles = ('files', ['/path/to/output/file2'])
	)
	job0.report()
	assert 'pProc: [1/1] a        => ab ... pq' in caplog.text
	assert 'pProc: [1/1] bc       => [ /l/p/t/file1 ]' in caplog.text
	assert 'pProc: [1/1] de       => /l/p/t/file2' in caplog.text
	assert 'pProc: [1/1] outfile  => /p/t/o/file1' in caplog.text
	assert 'pProc: [1/1] outfiles => [ /p/t/o/file2 ]' in caplog.text

# test_build

def test_linkinfile(job0, tmpdir):
	# clear up the input directory
	fs.mkdir(job0.dir / 'input', overwrite = True)
	infile1 = tmpdir / 'indir1' / 'test_linkinfile.infile.txt'
	infile1.parent.mkdir()
	infile1.write_text('')
	assert job0._linkInfile(infile1) == job0.dir / 'input' / 'test_linkinfile.infile.txt'

	# rename existing file with same name
	infile2 = tmpdir / 'indir2' / 'test_linkinfile.infile.txt'
	infile2.parent.mkdir()
	infile2.write_text('')
	assert job0._linkInfile(infile2) == job0.dir / 'input' / '[1]test_linkinfile.infile.txt'
	# do it again and it will detect infile2 and [1]... are the same file
	assert job0._linkInfile(infile2) == job0.dir / 'input' / '[1]test_linkinfile.infile.txt'

	# if a malformat file exists
	(job0.dir / 'input' / '[a]test_linkinfile.infile.txt').write_text('')
	infile3 = tmpdir / 'indir3' / 'test_linkinfile.infile.txt'
	infile3.parent.mkdir()
	infile3.write_text('')
	assert job0._linkInfile(infile3) == job0.dir / 'input' / '[2]test_linkinfile.infile.txt'

def test_prepinput(job0, tmpdir, caplog):
	infile1 = tmpdir / 'test_prepinput.txt'
	infile1.write_text('')
	infile2 = tmpdir / 'renaming' / 'test_prepinput.txt'
	infile2.parent.mkdir()
	infile2.write_text('')
	job0.proc.input = Box(
		invar = ('var', ['abc']),
		infile = ('file', [infile1]),
		infiles = ('files', [[infile1]]),
		emptyfile = ('file', ['']),
		emptyfiles = ('files', [['']]),
		renamed = ('file', [infile2]),
		nodatafiles = ('files', [[]]),
		renamedfiles = ('files', [[infile2]]),
	)
	job0._prepInput()
	assert len(job0.input) == 8
	assert job0.input['invar'] == ('var', 'abc')
	assert job0.input['infile'] == ('file', str(job0.dir / 'input' / 'test_prepinput.txt'))
	assert job0.input['infiles'] == ('files', [str(job0.dir / 'input' / 'test_prepinput.txt')])
	assert job0.input['emptyfile'] == ('file', '')
	assert job0.input['emptyfiles'] == ('files', [''])
	assert job0.input['renamed'] == ('file', str(job0.dir / 'input' / '[1]test_prepinput.txt'))
	assert job0.input['nodatafiles'] == ('files', [])
	assert job0.input['renamedfiles'] == ('files', [str(job0.dir / 'input' / '[1]test_prepinput.txt')])
	assert 'pProc: [1/1] Input file renamed: test_prepinput.txt -> [1]test_prepinput.txt' in caplog.text
	assert 'No data provided for [nodatafiles:files], use empty list instead.' in caplog.text

def test_prepinput_exc(job0, tmpdir):
	infile1 = tmpdir / 'test_prepinput_not_exists.txt'
	job0.proc.input = Box(
		infile = ('file', [[]]), # no a strin gor path or input [infile:file]
	)
	with pytest.raises(JobInputParseError):
		job0._prepInput()

	job0.proc.input = Box(
		nefile = ('file', [infile1]), # not exists
	)
	with pytest.raises(JobInputParseError):
		job0._prepInput()

	job0.proc.input = Box(
		nlfiles = ('files', [1]), # not a list
	)
	with pytest.raises(JobInputParseError):
		job0._prepInput()

	job0.proc.input = Box(
		npfiles = ('files', [[None]]), # not a path
	)
	with pytest.raises(JobInputParseError):
		job0._prepInput()

	job0.proc.input = Box(
		nefiles = ('files', [[infile1]])
	)
	with pytest.raises(JobInputParseError):
		job0._prepInput()

def test_prepoutput(job0, tmpdir):
	job0.proc.output = OBox()
	job0._prepOutput()
	assert len(job0.output) == 0

	job0.proc.output.out = ('var', TemplateLiquid('abc'))
	job0.proc.output.outfile = ('file', TemplateLiquid('outfile{{job.index}}.txt'))
	job0._prepOutput()
	assert len(job0.output) == 2
	assert job0.output.out == ('var', 'abc')
	assert job0.output.outfile == ('file', job0.dir / 'output' / 'outfile0.txt')

	job0.proc.output.clear()
	job0.proc.output.abs = ('file', TemplateLiquid('/a/b/c'))
	with pytest.raises(JobOutputParseError):
		job0._prepOutput()

def test_prepscript(job0, tmpdir):
	job0.proc.script = TemplateLiquid(str("# python script"))
	job0._prepScript()
	assert (job0.dir / 'job.script').read_text() == "# python script"
	job0.proc.script = TemplateLiquid(str("# python script2"))
	job0._prepScript()
	assert (job0.dir / 'job.script').read_text() == "# python script2"
	assert fs.exists(job0.dir / 'job.script._bak')

def test_rc(job0):
	assert job0.rc == RC_NO_RCFILE
	job0._rc = 1
	assert job0.rc == 1
	job0.rc = None
	assert job0.rc == RC_NO_RCFILE
	job0.rc = 2
	job0._rc = None # force reading from rcfile
	assert job0.rc == 2

def test_pid(job0):
	assert job0.pid is ''
	job0.pid = 'Job123'
	assert job0.pid == 'Job123'
	job0.pid = '123'
	job0._pid = None # force reading from pidfile
	assert job0.pid == '123'

def test_signature(job0, tmpdir, caplog):
	fs.remove(job0.dir / 'job.script')
	assert job0.signature() == ''
	(job0.dir / 'job.script').write_text('')
	assert job0.signature() == Box(
		script = filesig(job0.dir / 'job.script'),
		i = {'var': {}, 'file': {}, 'files': {}},
		o = {'var': {}, 'file': {}, 'dir':{}})
	infile = tmpdir / 'test_signature_input.txt'
	infile.write_text('')
	infile1 = tmpdir / 'test_signature_input_not_exists.txt'
	job0.input = Box(
		invar = ('var', 'abc'),
		infile = ('file', infile),
		infiles = ('files', [infile])
	)
	assert job0.signature().i == {
		'var': {'invar': 'abc'},
		'file': {'infile': filesig(infile)},
		'files': {'infiles': [filesig(infile)]},
	}

	job0.input = Box(
		invar = ('var', 'abc'),
		infile = ('file', infile1)
	)
	assert job0.signature() == ''
	assert 'Empty signature because of input file' in caplog.text

	job0.input = Box(
		invar = ('var', 'abc'),
		infiles = ('files', [infile1])
	)
	assert job0.signature() == ''
	assert 'Empty signature because of one of input files' in caplog.text

	job0.input = {}
	outfile = tmpdir / 'test_signature_outfile.txt'
	outfile.write_text('')
	outfile1 = tmpdir / 'test_signature_outfile_not_exists.txt'
	outdir = tmpdir / 'test_signature_outdir'
	outdir.mkdir()
	outdir1 = tmpdir / 'test_signature_outdir_not_exists'
	job0.output = OBox(
		out = ('var', 'abc'),
		outfile = ('file', outfile),
		outdir = ('dir', outdir)
	)
	assert job0.signature().o == {
		'var': {'out': 'abc'},
		'file': {'outfile': filesig(outfile)},
		'dir': {'outdir': filesig(outdir, dirsig = job0.proc.dirsig)}
	}

	job0.output = OBox(
		outfile = ('file', outfile1)
	)
	assert job0.signature() == ''
	assert 'Empty signature because of output file:' in caplog.text

	job0.output = OBox(
		outdir = ('dir', outdir1)
	)
	assert job0.signature() == ''
	assert 'Empty signature because of output dir:' in caplog.text

def test_comparevar(job0, caplog):
	assert job0._compareVar(
		{'key': 'val'},
		{'key': 'val'},
		'key', 'unlimited')
	assert 'Not cached' not in caplog.text

	assert not job0._compareVar(
		{'key': 'val'},
		{'key': 'val1'},
		'key', 'unlimited')
	assert 'Not cached' in caplog.text

def test_comparefile(job0, caplog):
	assert job0._compareFile(
		{'key': ('val', 1)},
		{'key': ('val', 1)},
		'key', 'unlimited')
	assert 'Not cached' not in caplog.text

	assert not job0._compareFile(
		{'key': ('val', 1)},
		{'key': ('val1', 1)},
		'key', 'unlimited')
	assert 'Not cached because key file(key) is different:' in caplog.text

	assert not job0._compareFile(
		{'key': ('val', 1)},
		{'key': ('val', 2)},
		'key', '', 'unlimited')
	assert 'Not cached because key file(key) is newer: val' in caplog.text

def test_comparefiles(job0, caplog):
	assert job0._compareFiles(
		{'key': [('val', 1)]},
		{'key': [('val', 1)]},
		'key', 'unlimited')
	assert 'Not cached' not in caplog.text

	assert not job0._compareFiles(
		{'key': [('val', 1), ()]},
		{'key': [('val', 1)]},
		'key', 'unlimited')
	assert 'Not cached because lengths are different for key [files:key]:' in caplog.text

	assert not job0._compareFiles(
		{'key': [('val', 1)]},
		{'key': [('val1', 1)]},
		'key', 'unlimited')
	assert 'Not cached because file 1 is different for key [files:key]:' in caplog.text

	assert not job0._compareFiles(
		{'key': [('val', 1)]},
		{'key': [('val', 2)]},
		'key', '', 'unlimited')
	assert 'Not cached because file 1 is newer for key [files:key]: val' in caplog.text

def test_istrulycached(job0, tmpdir, caplog):
	scriptfile = job0.dir / 'job.script'
	cachefile  = job0.dir / 'job.cache'

	job0.proc.cache = False
	job0.cache()
	assert not job0.isTrulyCached()

	job0.proc.cache = True
	assert not job0.isTrulyCached()
	assert 'Not cached as cache file not exists.' in caplog.text

	cachefile.write_text('')
	assert not job0.isTrulyCached()
	assert 'Not cached because previous signature is empty.' in caplog.text

	job0.input = {}
	job0.output = {}
	fs.remove(scriptfile)
	cachefile.write_text('a=1')
	assert not job0.isTrulyCached()
	assert 'Not cached because current signature is empty.' in caplog.text

	# CACHE_SCRIPT_NEWER
	scriptfile.write_text('')
	mtime = scriptfile.stat().st_mtime
	utime(scriptfile, (mtime - 10, mtime - 10))
	job0.cache()
	utime(scriptfile, (mtime, mtime))
	caplog.clear()
	assert not job0.isTrulyCached()
	assert 'Not cached because script file(script) is newer' in caplog.text

	# CACHE_SIGINVAR_DIFF
	job0.input = {'in': ('var', 'abc')}
	job0.cache()
	job0.input = {'in': ('var', 'abc1')}
	caplog.clear()
	assert not job0.isTrulyCached()
	assert 'Not cached because input variable(in) is different' in caplog.text

	# CACHE_SIGINFILE_DIFF
	infile1 = tmpdir / 'test_istrulycached1.txt'
	infile2 = tmpdir / 'test_istrulycached2.txt'
	infile1.write_text('')
	infile2.write_text('')
	job0.input = {'infile': ('file', infile1)}
	job0.cache()
	job0.input = {'infile': ('file', infile2)}
	caplog.clear()
	assert not job0.isTrulyCached()
	assert 'Not cached because input file(infile) is different:' in caplog.text

	# CACHE_SIGINFILE_NEWER
	job0.cache()
	utime(infile2, (mtime+100, mtime+100))
	caplog.clear()
	assert not job0.isTrulyCached()
	assert 'Not cached because input file(infile) is newer: ' in caplog.text

	# CACHE_SIGINFILES_DIFF
	job0.input = {'infiles': ('files', [infile1])}
	job0.cache()
	job0.input = {'infiles': ('files', [infile1, infile2])}
	caplog.clear()
	assert not job0.isTrulyCached()
	assert 'Not cached because lengths are different for input [files:infiles]:' in caplog.text

	# CACHE_SIGINFILES_NEWER
	job0.cache()
	utime(infile2, (mtime+200, mtime+200))
	caplog.clear()
	assert not job0.isTrulyCached()
	assert 'Not cached because file 2 is newer for input [files:infiles]:' in caplog.text

	# CACHE_SIGOUTVAR_DIFF
	job0.input = {}
	job0.output = {'out': ('var', 'abc')}
	job0.cache()
	job0.output = {'out': ('var', 'abc1')}
	caplog.clear()
	assert not job0.isTrulyCached()
	assert 'Not cached because output variable(out) is different' in caplog.text

	# CACHE_SIGOUTFILE_DIFF
	outfile1 = tmpdir / 'test_istrulycached_out1.txt'
	outfile2 = tmpdir / 'test_istrulycached_out2.txt'
	outfile1.write_text('')
	outfile2.write_text('')
	job0.output = {'outfile': ('file', outfile1)}
	job0.cache()
	job0.output = {'outfile': ('file', outfile2)}
	caplog.clear()
	assert not job0.isTrulyCached()
	assert 'Not cached because output file(outfile) is different:' in caplog.text

	# CACHE_SIGOUTDIR_DIFF
	outdir1 = tmpdir / 'test_istrulycached_dir1.txt'
	outdir2 = tmpdir / 'test_istrulycached_dir2.txt'
	outdir1.mkdir()
	outdir2.mkdir()
	job0.output = {'outdir': ('dir', outdir1)}
	job0.cache()
	job0.output = {'outdir': ('dir', outdir2)}
	caplog.clear()
	assert not job0.isTrulyCached()
	assert 'Not cached because output dir(outdir) is different:' in caplog.text

	job0.cache()
	assert job0.isTrulyCached()

def test_isexptcached(job0, tmpdir, caplog):
	job0.proc.cache = False
	assert not job0.isExptCached()

	job0.proc.cache = 'export'
	job0.proc.exhow = 'link'
	assert not job0.isExptCached()
	assert 'Job is not export-cached using symlink export.' in caplog.text
	caplog.clear()

	job0.proc.exhow = 'copy'
	job0.proc.expart = [TemplateLiquid('outfile')]
	assert not job0.isExptCached()
	assert 'Job is not export-cached using partial export.' in caplog.text
	caplog.clear()

	job0.proc.expart = None
	job0.proc.exdir = ''
	assert not job0.isExptCached()
	assert 'Job is not export-cached since export directory is not set.' in caplog.text
	caplog.clear()

	job0.proc.exdir = tmpdir / 'test_isexptcached_exdir'
	job0.proc.exdir.mkdir()
	outfile1 = tmpdir / 'test_isexptcached_outfile1.txt'
	outfile1.write_text('')
	outfile2 = tmpdir / 'test_isexptcached_outfile_not_exists.txt'
	outdir1 = tmpdir / 'test_isexptcached_outdir1'
	outdir1.mkdir()
	fs.gzip(outfile1, job0.proc.exdir / (outfile1.name + '.gz'))
	fs.gzip(outdir1, job0.proc.exdir / (outdir1.name + '.tgz'))
	job0.output = OBox(
		outfile = ('file', outfile1),
		outdir = ('dir', outdir1),
		out = ('var', 'abc')
	)
	# overwriting existing
	(job0.dir / 'output').mkdir()
	(job0.dir / 'output' / outfile1.name).write_text('')
	job0.proc.exhow = 'gzip'
	assert job0.isExptCached()
	assert 'Overwrite file for export-caching:' in caplog.text
	assert job0.isTrulyCached()
	caplog.clear()

	fs.remove(job0.proc.exdir / (outfile1.name + '.gz'))
	assert not job0.isExptCached()
	assert 'Job is not export-cached since exported file not exists:' in caplog.text
	caplog.clear()

	job0.output = OBox(
		outfile = ('file', outfile1)
	)
	job0.proc.exhow = 'move'
	assert not job0.isExptCached()
	assert 'Job is not export-cached since exported file not exists:' in caplog.text

	fs.link(outfile1, job0.proc.exdir / outfile1.name)
	assert job0.isExptCached()
	caplog.clear()

	# overwriting existing
	fs.remove(job0.proc.exdir / outfile1.name)
	(job0.proc.exdir / outfile1.name).write_text('')
	assert job0.isExptCached()
	assert 'Overwrite file for export-caching: ' in caplog.text

def test_isforcecached(job0, tmpdir):
	job0.proc.cache = False
	assert not job0.isForceCached()

	job0.proc.cache = 'force'
	outfile1 = tmpdir / 'test_isforcecached_outfile1.txt'
	outfile1.write_text('forcecached')
	outfile2 = tmpdir / 'test_isforcecached_outfile_not_exists.txt'
	outdir1 = tmpdir / 'test_isforcecached_outdir1'
	outdir1.mkdir()
	outdir1file = tmpdir / 'test_isforcecached_outdir1' / 'odfile.txt'
	outdir1file.write_text('odfile')
	outdir2 = tmpdir / 'test_isforcecached_outdir_not_exists'
	job0.output = OBox(
		outfile1 = ('file', outfile1),
		outfile2 = ('file', outfile2),
		outdir1 = ('dir', outdir1),
		outdir2 = ('dir', outdir2),
		out = ('var', 'abc')
	)

	assert job0.isForceCached()
	assert outfile1.is_file()
	assert outfile1.read_text() == 'forcecached'
	assert outfile2.is_file()
	assert outdir1.is_dir()
	assert outdir1file.is_file()
	assert outdir1file.read_text() == 'odfile'
	assert outdir2.is_dir()


def test_build(job0, tmpdir, caplog):
	job0.proc.input = {}
	job0.proc.output = {}
	job0.proc.cache = True
	job0.proc.script = TemplateLiquid('# script')
	fs.remove(job0.dir)
	assert job0.build()
	assert fs.isdir(job0.dir)
	assert not fs.exists(job0.dir / 'job.stdout.bak')
	assert not fs.exists(job0.dir / 'job.stderr.bak')

	(job0.dir / 'job.stdout').write_text('')
	(job0.dir / 'job.stderr').write_text('')
	assert job0.build()
	assert fs.exists(job0.dir / 'job.stdout.bak')
	assert fs.exists(job0.dir / 'job.stderr.bak')

	job0.cache()
	assert job0.build() == 'cached'

	# raise exception while building
	del job0.proc.input
	assert not job0.build()
	assert 'KeyError' in (job0.dir / 'job.stderr').read_text()

def test_reest(job0):
	job0.ntry = 0
	(job0.dir / 'output').mkdir()
	(job0.dir / 'output' / 'outfile.txt').write_text('')
	(job0.dir / 'output' / '.jobcache').mkdir()
	(job0.dir / 'job.rc').write_text('')
	(job0.dir / 'job.stdout').write_text('out')
	(job0.dir / 'job.stderr').write_text('err')
	(job0.dir / 'job.pid').write_text('')
	(job0.dir / 'retry.1').mkdir()
	job0.reset()
	assert not fs.exists(job0.dir / 'retry.1')
	assert not fs.exists(job0.dir / 'job.rc')
	# recreated
	assert (job0.dir / 'job.stdout').read_text() == ''
	assert (job0.dir / 'job.stderr').read_text() == ''
	assert not fs.exists(job0.dir / 'job.pid')
	assert fs.exists(job0.dir / 'output')
	# recreated
	assert not fs.exists(job0.dir / 'output' / 'outfile.txt')

	job0.ntry = 1
	(job0.dir / 'output' / 'outfile.txt').write_text('')
	(job0.dir / 'output' / '.jobcache' / 'cached.txt').write_text('')
	job0.reset()
	assert fs.exists(job0.dir / 'retry.1')
	assert not fs.exists(job0.dir / 'retry.1' / '.jobcache')
	assert fs.exists(job0.dir / 'output' / '.jobcache' / 'cached.txt')

	# remove whole output directory
	job0.ntry = 0
	fs.remove(job0.dir / 'output' / '.jobcache')
	(job0.dir / 'output' / 'outfile.txt').write_text('')
	job0.reset()
	assert not fs.exists(job0.dir / 'output' / 'outfile.txt')
	# move whole output directory
	job0.ntry = 1
	fs.remove(job0.dir / 'output' / '.jobcache')
	(job0.dir / 'output' / 'outfile.txt').write_text('')
	job0.reset()
	assert not fs.exists(job0.dir / 'output' / 'outfile.txt')

	# restore output directory and stdout, stderr
	job0.output = OBox(
		outdir = ('dir', job0.dir / 'output' / 'outdir'),
		outfile = ('stdout', job0.dir / 'output' / 'outfile'),
		errfile = ('stderr', job0.dir / 'output' / 'errfile'),
	)
	job0.ntry = 0
	job0.reset()
	assert fs.isdir(job0.dir / 'output' / 'outdir')
	assert fs.islink(job0.dir / 'output' / 'outfile')
	assert fs.islink(job0.dir / 'output' / 'errfile')
	assert fs.samefile(job0.dir / 'job.stdout', job0.dir / 'output' / 'outfile')
	assert fs.samefile(job0.dir / 'job.stderr', job0.dir / 'output' / 'errfile')

	# what if outdir exists
	job0.reset()

def test_export(job0, tmpdir, caplog):
	job0.proc.exdir = ''
	job0.export()
	assert 'Exported' not in caplog.text

	job0.proc.exdir = '/path/not/exists'
	with pytest.raises(AssertionError):
		job0.export()

	job0.proc.exdir = tmpdir / 'test_export'
	job0.proc.exdir.mkdir()

	job0.proc.expart = None
	with pytest.raises(AssertionError):
		job0.export()

	job0.proc.expart = []
	job0.export()
	assert 'Exported' not in caplog.text

	# export everything
	outfile1 = job0.dir / 'output' / 'test_export_outfile.txt'
	outfile1.parent.mkdir()
	outfile1.write_text('')
	job0.output = OBox(
		outfile = ('file', outfile1)
	)
	job0.proc.exhow = 'copy'
	job0.proc.exow = True
	job0.proc._log.shorten = 0
	job0.export()
	assert fs.exists(job0.proc.exdir / outfile1.name)
	assert not fs.islink(outfile1)
	assert not fs.samefile(outfile1, job0.proc.exdir / outfile1.name)
	assert ('Exported: %s' % (job0.proc.exdir / outfile1.name)) in caplog.text

	job0.proc.exhow = 'move'
	job0.export()
	assert fs.exists(job0.proc.exdir / outfile1.name)
	assert fs.islink(outfile1)
	assert fs.samefile(outfile1, job0.proc.exdir / outfile1.name)
	assert ('Exported: %s' % (job0.proc.exdir / outfile1.name)) in caplog.text

	# outfile is a link, then copy the file
	job0.export()
	assert fs.exists(job0.proc.exdir / outfile1.name)
	assert not fs.islink(job0.proc.exdir / outfile1.name)
	assert fs.islink(outfile1)
	assert fs.samefile(outfile1, job0.proc.exdir / outfile1.name)

	job0.proc.exhow = 'link'
	job0.export()
	assert fs.exists(job0.proc.exdir / outfile1.name)
	assert fs.islink(job0.proc.exdir / outfile1.name)
	assert not fs.islink(outfile1)
	assert fs.samefile(outfile1, job0.proc.exdir / outfile1.name)

	job0.proc.exhow = 'gzip'
	job0.export()
	assert fs.exists(job0.proc.exdir / (outfile1.name + '.gz'))

	job0.proc.expart = [TemplateLiquid('outfile')]
	fs.remove(job0.proc.exdir / (outfile1.name + '.gz'))
	job0.export()
	assert fs.exists(job0.proc.exdir / (outfile1.name + '.gz'))

	job0.proc.expart = [TemplateLiquid('*.txt')]
	fs.remove(job0.proc.exdir / (outfile1.name + '.gz'))
	job0.export()
	assert fs.exists(job0.proc.exdir / (outfile1.name + '.gz'))

def test_succeed(job0, caplog):
	job0.rc = 1
	job0.proc.rc = [0]
	assert not job0.succeed()

	job0.proc.rc = [0, 1]
	(job0.dir / 'output').mkdir()
	job0.proc.expect = TemplateLiquid('')
	assert job0.succeed()

	job0.output = OBox(
		outfile = ('file', job0.dir / 'output' / 'notexists')
	)
	job0.rc = 1
	caplog.clear()
	assert not job0.succeed()
	assert 'Outfile not generated' in caplog.text
	assert job0.rc == 1 + (1<<9)

	(job0.dir / 'output' / 'notexists').write_text('')
	job0.proc.expect = TemplateLiquid('grep abc {{o.outfile}}')
	job0.rc = 1
	caplog.clear()
	assert not job0.succeed()
	assert 'Check expectation' in caplog.text
	assert job0.rc == 1 + (1<<10)

def test_done(job0, tmpdir, caplog):
	job0.proc.exdir = tmpdir / 'test_done_exdir'
	job0.proc.exdir.mkdir()
	job0.proc.expart = []
	job0.proc.cache = True
	job0.done()
	assert 'Finishing up the job' in caplog.text

def test_impl_notimplerror(job0):
	with pytest.raises(NotImplementedError):
		job0.isRunningImpl()
	with pytest.raises(NotImplementedError):
		job0.submitImpl()
	with pytest.raises(NotImplementedError):
		job0.killImpl()

def test_submit(job0, caplog):
	job0.isRunningImpl = lambda: True
	assert job0.submit()
	assert 'is already running at' in caplog.text

	job0.isRunningImpl = lambda: False
	job0.submitImpl = lambda: Box(rc = 0)
	assert job0.submit()

	job0.submitImpl = lambda: Box(rc = 1, cmd = '', stderr = '')
	caplog.clear()
	assert not job0.submit()
	assert 'Submission failed' in caplog.text

def test_poll(job0, caplog):
	fs.remove(job0.dir / 'job.stderr')
	fs.remove(job0.dir / 'job.stdout')
	assert job0.poll() == 'running'

	(job0.dir / 'output').mkdir()
	(job0.dir / 'job.stderr').write_text('')
	(job0.dir / 'job.stdout').write_text('')
	job0.rc = 0
	job0.proc.rc = [0]
	job0.proc.expect = TemplateLiquid('')
	job0.proc.echo = {'jobs': [0], 'type': {'stdout':'', 'stderr':''}}
	assert job0.poll()

	job0._rc = None
	fs.remove(job0.dir / 'job.rc')
	assert job0.poll() == 'running'

def test_flush(job0, caplog):
	job0.proc.echo = {'jobs': [1]}
	job0._flush()
	assert '' == caplog.text
	assert job0.lastout == ''
	assert job0.lasterr == ''

	job0.proc.echo = {'jobs': [0], 'type': {'stdout': '', 'stderr': r'^[^&].+$'}}
	(job0.dir / 'job.stdout').write_text('out: line1\nout: line2')
	(job0.dir / 'job.stderr').write_text('err: line1\nerr: line2')
	caplog.clear()
	job0._flush()
	assert 'out: line1' in caplog.text
	assert 'err: line1' in caplog.text
	assert 'line2' not in caplog.text
	assert job0.lastout == 'out: line2'
	assert job0.lasterr == 'err: line2'

	(job0.dir / 'job.stderr').write_text(
		'err: line1\nerr: line23\n& ignored\npyppl.log.abc\npyppl.log.msg: hello world!')
	caplog.clear()
	job0._flush(end = True)
	assert 'err: line23' in caplog.text
	assert '_MSG' in caplog.text
	assert '_ABC' in caplog.text
	assert 'hello world' in caplog.text
	assert 'ignored' not in caplog.text
	assert job0.lastout == ''
	assert job0.lasterr == ''

def test_retry(job0, caplog):
	job0.proc.errhow = 'ignore'
	assert job0.retry() == 'ignored'

	job0.proc.errhow = 'terminate'
	assert job0.retry() == False

	job0.proc.errhow = 'retry'
	job0.proc.errntry = 1
	caplog.clear()
	assert job0.retry()
	assert job0.ntry == 1
	assert 'Retrying 1 out of 1 time(s) ...' in caplog.text

	assert job0.retry() == False

def test_kill(job0):
	job0.killImpl = lambda: None
	assert job0.kill()

	job0.killImpl = lambda: 1/0
	assert not job0.kill()
	assert job0.pid == ''
