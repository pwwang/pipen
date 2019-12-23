import cmdy
import pytest
from pyppl import PyPPL, Proc

@pytest.fixture
def ppldir(tmp_path):
	infile = tmp_path/'input.txt'
	infile.write_text('hello')
	pProc1 = Proc(
		input = {'infile:file': [infile]},
		output = 'outfile:file:{{i.infile|__import__("pathlib").Path|.stem}}.txt',
		script = """cat {{i.infile}} > {{o.outfile}}""")
	pProc2 = Proc(
		input = 'infile:file',
		output = 'outfile:file:{{i.infile|__import__("pathlib").Path|.stem}}.txt',
		script = """echo world >> {{o.outfile}}""",
		depends = pProc1)
	PyPPL(ppldir = tmp_path/'workdir').start(pProc1).run()
	return tmp_path/'workdir'

def test_status(ppldir):
	cmdy.pyppl.status(wdir = ppldir, proc = 'pProc1', _fg = True)