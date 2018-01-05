import path, unittest

import sys
import tempfile
from os import path
from contextlib import contextmanager
from six import StringIO
from subprocess import Popen
from multiprocessing import Queue
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

def which(program):
	import os
	def is_exe(fpath):
		return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

	fpath, fname = os.path.split(program)
	if fpath:
		if is_exe(program):
			return program
	else:
		for path in os.environ["PATH"].split(os.pathsep):
			path = path.strip('"')
			exe_file = os.path.join(path, program)
			if is_exe(exe_file):
				return exe_file

	return None

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
		self.ncjobids = [8]

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
		self.dir     = '.'
		self.index   = 8
		self.output  = {}
		self.rcfile  = path.join(tmpdir, 'testrunnerjob.rc')
		self.pidfile = path.join(tmpdir, 'testrunnerjob.pid')
		self.script  = path.join(tmpdir, 'testrunnerjob.script')
		self.errfile = path.join(tmpdir, 'testrunnerjob.stderr')
		self.outfile = path.join(tmpdir, 'testrunnerjob.stdout')
		self.cachefile = self.script
		with open(self.script, 'w') as fs:
			fs.write('')

	def checkOutfiles(self, expect):
		pass

	def reset(self, ntry = None):
		sys.stderr.write('Job reset: ' + str(ntry) + '\n') 

	def rc(self, r = None):
		if r is None: return self._rc
		self._rc = r

	def done(self):
		sys.stderr.write('Job done\n') 

	def succeed(self):
		return self._suc

	def pid(self, val = None):
		if val is None:
			if not path.exists (self.pidfile):
				return ''
			with open(self.pidfile) as f:
				return f.read().strip()
		else:
			with open (self.pidfile, 'w') as f:
				f.write (str(val))

class TestRunner(unittest.TestCase):

	def testInit(self):
		job = Job()
		r = runners.Runner(job)
		self.assertIsInstance(r.job, Job)
		self.assertEqual(r.script, [job.script])
		self.assertEqual(r.cmd2run, job.script)
		self.assertEqual(r.ntry, 0)

	def testFlushOut(self):
		job = Job()
		job.proc.echo['type'] = ['stderr', 'stdout']
		r = runners.Runner(job)
		lastout = ''
		lasterr = ''
		end     = False
		open(job.outfile, 'w').close()
		open(job.errfile, 'w').close()
		fout = open (job.outfile)
		ferr = open (job.errfile)
		with open(job.outfile, 'w') as f1, open(job.errfile, 'w') as f2:
			f1.write("outoutout\noutoutout2")
			f2.write("errerrrerere\nererererere2")
		with captured_output() as (out, err):
			(lastout, lasterr) = r._flushOut(fout,ferr,lastout,lasterr,False)
		
		self.assertEqual('outoutout\n', out.getvalue())
		self.assertEqual('errerrrerere\n', err.getvalue())
		self.assertEqual(lastout, 'outoutout2')
		self.assertEqual(lasterr, 'ererererere2')

		with open(job.outfile, 'a') as f1, open(job.errfile, 'a') as f2:
			f1.write("outoutout3\n")
			f2.write("errerrrerere3\npyppl.log.warn: hello\npyppl.log.AAA\n444")
		with captured_output() as (out, err):
			(lastout, lasterr) = r._flushOut(fout,ferr,lastout,lasterr,False)
		self.assertEqual('outoutout2outoutout3\n', out.getvalue())
		self.assertEqual('ererererere2errerrrerere3\npyppl.log.warn: hello\n[_warn] hello\npyppl.log.AAA\n[_AAA] \n', err.getvalue())

		with open(job.outfile, 'a') as f1, open(job.errfile, 'a') as f2:
			f2.write("555")
		with captured_output() as (out, err):
			(lastout, lasterr) = r._flushOut(fout,ferr,lastout,lasterr,True)
		self.assertEqual(err.getvalue(), '444555\n')
		if fout: fout.close()
		if ferr: ferr.close()

	def testIsRunning(self):
		job = Job()
		r = runners.Runner(job)
		self.assertFalse(r.isRunning())

	def testSubmit(self):
		
		with captured_output() as (out, err):
			logger.getLogger(levels = 'all')
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
			fs.write('#!/bin/bash\nsleep 1\nls')
		#with captured_output() as (out, err):
		
		# simulate submitting
		p = Popen(['sleep', '1'])
		job.pid(p.pid)
		self.assertTrue(r.isRunning())
		self.assertEqual(p.wait(), 0)
		self.assertEqual(int(job.pid()), p.pid)
		#self.assertIn('reset', err.getvalue())
		#self.assertIn('Submitting', err.getvalue())
		#self.assertNotIn('Failed', err.getvalue())

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
			r.run(Queue())
		self.assertEqual(job._rc, 0)
		job._rc = 345
		r.status(0)
		with captured_output() as (out, err):
			r.submit()
			r.run(Queue())
		self.assertEqual(job._rc, 0)

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
			r.run(Queue(), test=True)
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
			'b': {'type': 'dir', 'data': 'abc.dir'},
			'c': {'type': 'var', 'data': '1'}
		}
		r = runners.RunnerDry(job)
		r.finish()
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
			r.run(Queue())
		self.assertIn('abcdef', err.getvalue())

	def testSge(self):
		job = Job()
		job.proc.sgeRunner = {
			'sge.N': 'pTestProc.notag.suffix.8',
			'sge.q': '1-day',
			'sge.j': 'sge.j',
			'sge.o': 'testrunnerjob.stdout',
			'sge.e': 'testrunnerjob.stderr',
			'sge.M': 'sge.M',
			'sge.m': 'sge.m',
			'sge.notify': True,
			'sge.X': 'sge.X',
			'preScript': 'preScript',
			'postScript': 'postScript',

		}
		r = runners.RunnerSge(job)
		self.assertIsInstance(r, runners.RunnerSge)
		self.assertIsInstance(r, runners.Runner)

		with open(job.script + '.sge') as f: scripts = f.read()
		self.assertIn('#$ -N pTestProc.notag.suffix.8', scripts)
		self.assertIn('testrunnerjob.stdout', scripts)
		self.assertIn('testrunnerjob.stderr', scripts)
		self.assertIn('testrunnerjob.script', scripts)
		self.assertIn('preScript', scripts)
		self.assertIn('postScript', scripts)
		self.assertIn('trap', scripts)

		self.assertEqual(r.script, ['qsub', job.script + '.sge'])

	@unittest.skipIf(not which('qstat'), 'SGE client not installed.')
	def testSgeGetPid(self):
		job = Job()
		job.pid('')
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
		job.proc.slurmRunner = {
			'sbatch': 'sbatch',
			'srun': 'srun',
			'squeue': 'squeue',
			'cmdPrefix': 'srun',
			'slurm.J': 'slurm.J',
			'slurm.o': 'slurm.o',
			'slurm.e': 'slurm.e',
			'slurm.notify': True,
			'slurm.X': 'slurm.X',
			'preScript': 'preScript',
			'postScript': 'postScript',
		}
		r = runners.RunnerSlurm(job)
		self.assertIsInstance(r, runners.RunnerSlurm)
		self.assertIsInstance(r, runners.Runner)
		self.assertEqual(r.script, ['sbatch', job.script + '.slurm'])
		with open(job.script + '.slurm') as f:
			thestr = f.read()
		self.assertIn('#!/usr/bin/env bash', thestr)
		self.assertIn('#SBATCH -J slurm.J', thestr)
		self.assertIn('#SBATCH -o slurm.o', thestr)
		self.assertIn('#SBATCH -e slurm.e', thestr)
		self.assertIn('#SBATCH -X slurm.X', thestr)
		self.assertIn('#SBATCH --notify', thestr)
		self.assertIn('preScript', thestr)
		self.assertIn('postScript', thestr)
		self.assertIn('srun', thestr)

	def testSlurmGetPid(self):
		job = Job()
		job.pid('')
		r = runners.RunnerSlurm(job)
		with open(job.outfile, 'w') as f:
			f.write('')
		r.getpid()
		self.assertEqual(job.pid(), '')

		with open(job.outfile, 'w') as f:
			f.write('Submitted batch job: 8525')
		r.getpid()
		self.assertEqual(int(job.pid()), 8525)

	def testSlurmIsRunning(self):
		job = Job()
		r = runners.RunnerSlurm(job)
		self.assertFalse(r.isRunning())

	#@skip('Skip if ssh not available.')
	def testSsh(self):
		job = Job()
		self.assertRaises(ValueError, runners.RunnerSsh, job)
		job.proc.sshRunner = {
			'servers': ['server1', 'server2', 'server3'],
			'keys':    ['k1', 'k2', 'k3'],
			'preScript': 'mkdir ~/ssh-runner',
			'postScript': 'rm -rf ~/ssh-runner',
		}
		r = runners.RunnerSsh(job)
		self.assertIsInstance(r, runners.RunnerSsh)
		self.assertIsInstance(r, runners.Runner)
		self.assertEqual(r.server, 'server1')
		r2 = runners.RunnerSsh(job)
		self.assertEqual(r2.server, 'server2')
		self.assertEqual(r2.script, [job.script + '.ssh'])

		job.proc.sshRunner = {
			'servers': ['server1', 'server2', 'server3'],
			'keys': ''
		}
		self.assertRaises(Exception, runners.RunnerSsh, job)

if __name__ == '__main__':
	unittest.main(verbosity=2)