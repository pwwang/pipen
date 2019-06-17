import pytest
from pathlib import Path
from pyppl import Job, Box
from pyppl.utils import fs

# use RunnerTest to pass the name check
class RunnerTest(Job):
	pass

class RunnerTest2(Job):
	@property
	def scriptParts(self):
		ret = super().scriptParts
		ret.command = 'command'
		ret.saveoe = True
		ret.pre = 'pre'
		ret.post = 'post'
		return ret

from tests.fixt_jobmgr import Proc

@pytest.fixture
def job0(tmpdir):
	tmpdir = Path(tmpdir)
	job = RunnerTest(0, Proc(
		workdir  = tmpdir,
		size     = 1,
		echo     = Box(jobs=[0], type=['stderr']),
		procvars = {
			'proc': {'errhow': 'terminate'}, 'args': {}},
		_log = Box({'shorten': 0})))
	fs.mkdir(job.dir)
	(job.dir / 'job.script').write_text('')
	return job

@pytest.fixture
def job1(tmpdir):
	tmpdir = Path(tmpdir)
	job = RunnerTest2(0, Proc(workdir = tmpdir, size=1, procvars = {
		'proc': {'errhow': 'terminate'}, 'args': {}
	}))
	fs.mkdir(job.dir)
	(job.dir / 'job.script').write_text('')
	return job

