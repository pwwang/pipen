import cmdy
import pytest
from pathlib import Path
from pyppl import PyPPL, Proc, proc

pyppl = cmdy.pyppl.bake(_exe = Path(__file__).parent.joinpath('pyppl'))

def get_ppldir(tmp_path, tag = 'notag'):
	infile = tmp_path/'input.txt'
	infile.write_text('hello')
	pConsoleProc1 = Proc(
		tag = tag,
		input = {'infile:file': [infile] * 5},
		output = 'outfile:file:{{i.infile|__import__("pathlib").Path|.stem}}.txt',
		script = """cat {{i.infile}} > {{o.outfile}}""")
	#assert pConsoleProc1.tag == tag
	pConsoleProc2 = Proc(
		tag = tag,
		input = 'infile:file',
		output = 'outfile:file:{{i.infile|__import__("pathlib").Path|.stem}}.txt',
		script = """echo world >> {{o.outfile}}""",
		depends = pConsoleProc1)
	#assert pConsoleProc2.tag == tag
	PyPPL(ppldir = tmp_path/'workdir', logger_level = 'debug', forks = 5).start(pConsoleProc1).run()
	return tmp_path/'workdir'

def test_status(tmp_path):
	wdir = get_ppldir(tmp_path, tag = 'status')
	cmd = pyppl.status(wdir = wdir, proc = 'pConsoleProc1')
	assert '#1: Done     [0]    #2: Done     [0]    #3: Done     [0]    #4: Done     [0]' in cmd.stderr
	assert 'Done    : 5' in cmd.stderr

	cmd = pyppl.status(proc = next(wdir.glob('PyPPL.pConsoleProc1.*')))
	assert '#1: Done     [0]    #2: Done     [0]    #3: Done     [0]    #4: Done     [0]' in cmd.stderr
	assert 'Done    : 5' in cmd.stderr

	wdir.joinpath('PyPPL.pConsoleProc1.a').mkdir()
	cmd = pyppl.status(wdir = wdir, proc = 'pConsoleProc1')
	assert 'There are more than 1 processes named with "pConsoleProc1", first one used.' in cmd.stderr

	wdir.joinpath('PyPPL.pConsoleProc1.a').rmdir()
	next(wdir.glob('PyPPL.pConsoleProc1.*/1/job.pid')).unlink()
	cmd = pyppl.status(wdir = wdir, proc = 'pConsoleProc1')
	assert '#1: Pending  [-]' in cmd.stderr
	assert 'Pending : 1' in cmd.stderr

	next(wdir.glob('PyPPL.pConsoleProc2.*/1/job.rc')).unlink()
	cmd = pyppl.status(wdir = wdir, proc = 'pConsoleProc2')
	assert '#1: Running  [-]' in cmd.stderr
	assert 'Running : 1' in cmd.stderr

def test_profile():
	cmd = pyppl.profile()

	assert '>>> default' in cmd.stderr

def test_list(tmp_path):
	wdir = get_ppldir(tmp_path, tag = 'list')
	cmd = pyppl.list(wdir = wdir)
	assert 'v PyPPL.pConsoleProc1.list' in cmd.stderr
	assert 'v PyPPL.pConsoleProc2.list' in cmd.stderr

	next(wdir.glob('PyPPL.pConsoleProc1.*/proc.settings.toml')).unlink()
	cmd = pyppl.list(wdir = wdir)
	assert '00:00' in cmd.stderr

	next(wdir.glob('PyPPL.pConsoleProc1.*/1/job.rc')).unlink()
	cmd = pyppl.list(wdir = wdir, error = True)
	assert 'x PyPPL.pConsoleProc1.list' in cmd.stderr
	assert 'PyPPL.pConsoleProc2.list' not in cmd.stderr

	next(wdir.glob('PyPPL.pConsoleProc2.*/1/job.rc')).write_text('1')
	cmd = pyppl.list(wdir = wdir, proc = 'pConsoleProc2')
	assert 'x PyPPL.pConsoleProc2.list' in cmd.stderr

	cmd = pyppl.list(wdir = wdir, proc = 'pProc3', _raise = False)
	assert 'No query processes found in workdir' in cmd.stderr

	cmd = pyppl.list(wdir = wdir, ago = 100, nocheck = True)
	assert 'v PyPPL.pConsoleProc1.list' in cmd.stderr
	assert 'PyPPL.pConsoleProc2.list' not in cmd.stderr

	cmd = pyppl.list(wdir = wdir, before = '1/1/2000')
	assert 'x PyPPL.pConsoleProc1.list' in cmd.stderr
	assert 'PyPPL.pConsoleProc2.list' not in cmd.stderr

	cmd = pyppl.list(wdir = wdir, before = '1/1')
	assert 'x PyPPL.pConsoleProc1.list' in cmd.stderr
	assert 'PyPPL.pConsoleProc2.list' not in cmd.stderr

	cmd = pyppl.list(wdir = wdir, before = '2000-1-1')
	assert 'x PyPPL.pConsoleProc1.list' in cmd.stderr
	assert 'PyPPL.pConsoleProc2.list' not in cmd.stderr

	cmd = pyppl.list(wdir = wdir, before = '1-1')
	assert 'x PyPPL.pConsoleProc1.list' in cmd.stderr
	assert 'PyPPL.pConsoleProc2.list' not in cmd.stderr

def test_clean(tmp_path):
	wdir = get_ppldir(tmp_path, tag = 'clean1')
	cmd = pyppl.clean(wdir = wdir, error = True, force = True)
	assert str(wdir) in cmd.stderr
	assert 'PyPPL.pConsoleProc1.clean1' not in cmd.stderr
	assert 'PyPPL.pConsoleProc2.clean1' not in cmd.stderr

	next(wdir.glob('PyPPL.pConsoleProc1.*/1/job.rc')).write_text('1')
	cmd = pyppl.clean(wdir = wdir, error = True, force = True)
	assert 'PyPPL.pConsoleProc1.clean1' in cmd.stderr
	assert 'PyPPL.pConsoleProc2.clean1' not in cmd.stderr

	# interactive remove
	cmd = pyppl.clean(wdir = wdir, error = False, force = False, _hold = True)
	cmd = cmdy.printf('x\nx\nY\n', _pipe = True) | cmdy.bash(c = cmd)
	assert 'PyPPL.pConsoleProc1.clean1' not in cmd.stderr
	assert 'PyPPL.pConsoleProc2.clean1' in cmd.stderr

	wdir = get_ppldir(tmp_path, tag = 'clean2')
	wdir.joinpath('PyPPL.pConsoleProc1.clean2.suffix').mkdir()
	cmd = pyppl.clean(wdir = wdir, one = True, error = False, force = True)
	assert cmd.stderr.count('Removed!') == 1 # only one for each remained

def test_logo():
	assert 'Loaded plugin: pyppl.console.logo' in pyppl.logo().stderr

def test_plugins():
	assert 'Plugin pyppl.console.clean' in pyppl.plugins().stderr
