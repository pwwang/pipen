import path, unittest

import sys
import tempfile
from os import path
from contextlib import contextmanager
from six import StringIO
from pyppl import runners, utils, logger

tmpdir = tempfile.gettempdir()

@contextmanager
def captured_output():
	new_out, new_err = StringIO(), StringIO()
	old_out, old_err = sys.stdout, sys.stderr
	try:
		sys.stdout, sys.stderr = new_out, new_err
		yield sys.stdout, sys.stderr
	finally:
		sys.stdout, sys.stderr = old_out, old_err

class Proc(object):
	OUT_VARTYPE  = ['var']
	OUT_FILETYPE = ['file']
	OUT_DIRTYPE  = ['dir']
	def __init__(self):
		self.errhow  = 'terminate'
		self.errntry = 3
		self.echo    = {'jobs':[8], 'type':['stderr'], 'filter': ''}
		self.id      = 'pTestProc'
		self.tag     = 'notag'
		self.sshRunner = ''

	def log(self, msg, flag):
		sys.stderr.write('[%s] %s\n' % (flag, msg)) 

	def _suffix(self):
		return 'suffix'
	
	def name(self):
		return "%s.%s" % (self.id, self.tag)

class Job(object):
	def __init__(self):
		self._rc     = 0
		self._pid    = ''
		self._suc    = True
		self.proc    = Proc()
		self.index   = 8
		self.output  = {}
		self.rcfile  = path.join(tmpdir, 'testrunnerjob.rc')
		self.script  = path.join(tmpdir, 'testrunnerjob.script')
		self.errfile = path.join(tmpdir, 'testrunnerjob.stderr')
		self.outfile = path.join(tmpdir, 'testrunnerjob.stdout')
		with open(self.script, 'w') as fs:
			fs.write('')

	def reset(self, ntry = None):
		sys.stderr.write('Job reset: ' + str(ntry) + '\n') 

	def rc(self, r = None):
		if r is None: return self._rc
		self._rc = r

	def done(self):
		sys.stderr.write('Job done\n') 

	def succeed(self):
		return self._suc

	def pid(self, _pid = None):
		if _pid is None: return self._pid
		self._pid = _pid

class TestRunner(unittest.TestCase):

	def testInit(self):
		job = Job()
		r = runners.Runner(job)
		self.assertIsInstance(r.job, Job)
		self.assertEqual(r.script, [job.script])
		self.assertEqual(r.cmd2run, job.script)
		self.assertEqual(r.ntry, 0)
		self.assertIsNone(r.p)
		self.assertIsNone(r.ferrw)
		self.assertIsNone(r.foutw)

	def testSubmit(self):
		with captured_output() as (out, err):
			logger.getLogger()
		job = Job()
		r = runners.Runner(job)
		with captured_output() as (out, err):
			r.submit()
		self.assertEqual(job._rc, 99)
		self.assertIn('Job reset: None', err.getvalue())
		self.assertIn('Submitting job #8', err.getvalue())
		self.assertIn('Failed to run job', err.getvalue())

		# normal
		with open(job.script, 'w') as fs:
			fs.write('#!/bin/bash\nls')
		with captured_output() as (out, err):
			r.submit()
		self.assertIsNotNone(r.p)
		self.assertIn('reset', err.getvalue())
		self.assertIn('Submitting', err.getvalue())
		self.assertNotIn('Failed', err.getvalue())
		r.getpid()
		self.assertEqual(r.job._pid, str(r.p.pid))
		self.assertTrue(r.isRunning())
		self.assertEqual(r.p.wait(), 0)

	def testWait(self):
		with captured_output() as (out, err):
			logger.getLogger()
		job = Job()
		with open(job.script, 'w') as fs:
			fs.write('#!/bin/bash\nls')
		job._rc = 3924
		r = runners.Runner(job)
		with captured_output() as (out, err):
			r.submit()
			r.wait()
		self.assertEqual(job._rc, 0)
		job._rc = 345
		with captured_output() as (out, err):
			r.submit()
			r.wait(rc = False)
		self.assertEqual(job._rc, 345)

	def testFinish(self):
		with captured_output() as (out, err):
			logger.getLogger()
		job = Job()
		r = runners.Runner(job)
		with captured_output() as (out, err):
			r.finish()
		self.assertIn('Job done', err.getvalue())

	def testRetry(self):
		with captured_output() as (out, err):
			logger.getLogger()
		job = Job()
		r = runners.Runner(job)
		job.proc.errhow = 'retry'
		job._suc = False
		with captured_output() as (out, err):
			r.submit()
			r.wait()
			r.finish()
		self.assertEqual(err.getvalue().count('RETRY'), 3)

	def testLocal(self):
		job = Job()
		r = runners.RunnerLocal(job)
		self.assertIsInstance(r, runners.RunnerLocal)
		self.assertIsInstance(r, runners.Runner)

	def testDry(self):
		job = Job()
		r = runners.RunnerDry(job)
		self.assertIsInstance(r, runners.RunnerDry)
		self.assertIsInstance(r, runners.Runner)
		script = path.join(tempfile.gettempdir(), 'testrunnerjob.script.dry')
		self.assertEqual(r.script, [script])

		job.output = {
			'a': {'type': 'file', 'data': 'abc.file'},
			'b': {'type': 'dir', 'data': 'abc.dir'}
		}
		r = runners.RunnerDry(job)
		with open(script) as f: scriptcontent = f.read()
		self.assertIn('touch "abc.file"', scriptcontent)
		self.assertIn('mkdir -p "abc.dir"', scriptcontent)

	def testQueue(self):
		job = Job()
		r = runners.RunnerQueue(job)
		self.assertIsInstance(r, runners.RunnerQueue)
		self.assertIsInstance(r, runners.Runner)

	def testQueueWait(self):
		with captured_output() as (out, err):
			logger.getLogger()
			job = Job()
			with open(job.script, 'w') as fs:
				fs.write('#!/bin/bash\necho pyppl.log:abcdef 1>&2')
			r = runners.RunnerQueue(job)
			r.submit()
			r.wait()
		self.assertIn('abcdef', err.getvalue())

	def testSge(self):
		job = Job()
		r = runners.RunnerSge(job)
		self.assertIsInstance(r, runners.RunnerSge)
		self.assertIsInstance(r, runners.Runner)

		with open(job.script + '.sge') as f: scripts = f.read()
		self.assertIn('#$ -N pTestProc.notag.suffix.8', scripts)
		self.assertIn('testrunnerjob.stdout', scripts)
		self.assertIn('testrunnerjob.stderr', scripts)
		self.assertIn('testrunnerjob.script', scripts)
		self.assertIn('trap', scripts)

		self.assertEqual(r.script, ['qsub', job.script + '.sge'])

	def testSgeGetPid(self):
		job = Job()
		r = runners.RunnerSge(job)
		with open(job.outfile, 'w') as f: f.write('')
		r.getpid()
		self.assertEqual(job.pid(), '')
		with open(job.outfile, 'w') as f: f.write('Your job 6556149 ("pSort.notag.3omQ6NdZ.0") has been submitted')
		r.getpid()
		self.assertEqual(job.pid(), '6556149')

		self.assertFalse(r.isRunning())

	def testSlurm(self):
		job = Job()
		r = runners.RunnerSlurm(job)
		self.assertIsInstance(r, runners.RunnerSlurm)
		self.assertIsInstance(r, runners.Runner)

	#@skip('Skip if ssh not available.')
	def testSsh(self):
		job = Job()
		self.assertRaises(ValueError, runners.RunnerSsh, job)
		job.proc.sshRunner = {
			'servers': ['server1', 'server2', 'server3']
		}
		r = runners.RunnerSsh(job)
		self.assertIsInstance(r, runners.RunnerSsh)
		self.assertIsInstance(r, runners.Runner)
		self.assertEqual(r.server, 'server1')
		r2 = runners.RunnerSsh(job)
		self.assertEqual(r2.server, 'server2')
		self.assertEqual(r2.script, [job.script + '.ssh'])

if __name__ == '__main__':
	unittest.main(verbosity=2)