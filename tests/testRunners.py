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
	def __init__(self):
		self.errhow  = 'terminate'
		self.errntry = 3
		self.echo    = {'jobs':[8], 'type':['stderr']}

	def log(self, msg, flag):
		sys.stderr.write('[%s] %s\n' % (flag, msg)) 

class Job(object):
	def __init__(self):
		self._rc     = 0
		self._pid    = ''
		self._suc    = True
		self.proc    = Proc()
		self.index   = 8
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


if __name__ == '__main__':
	unittest.main(verbosity=2)