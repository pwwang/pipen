import helpers, unittest

from os import path, getcwd
from hashlib import md5
from collections import OrderedDict
from pyppl import Job, Proc, utils
from pyppl.runners import Runner, RunnerLocal, RunnerDry, RunnerSsh, RunnerSge, RunnerSlurm
from pyppl.templates import TemplatePyPPL
from pyppl.exception import RunnerSshError

__folder__ = path.realpath(path.dirname(__file__))

def clearMockQueue():
	qsubQfile   = path.join(__folder__, 'mocks', 'qsub.queue.txt')
	sbatchQfile = path.join(__folder__, 'mocks', 'sbatch.queue.txt')
	helpers.writeFile(qsubQfile, '')
	helpers.writeFile(sbatchQfile, '')

def _generateJob(testdir, index = 0, pProps = None, jobActs = None):
	p = Proc()
	p.props['workdir'] = path.join(testdir, 'p', 'workdir')
	p.props['script']  = TemplatePyPPL('')
	p.props['ncjobids']  = list(range(40))
	if pProps:
		p.props.update(pProps)
	job = Job(index, p)
	job.init()
	if jobActs:
		jobActs(job)
	return job

class TestRunner(helpers.TestCase):
	
	def dataProvider_testInit(self, testdir):
		yield _generateJob(testdir),

	def testInit(self, job):
		r = Runner(job)
		self.assertIsInstance(r, Runner)
		self.assertIs(r.job, job)
		self.assertEqual(r.script, [job.script])
		self.assertEqual(r.cmd2run, job.script)
		self.assertEqual(r.ntry.value, 0)
		
	def dataProvider_testIsRunning(self, testdir):
		yield _generateJob(testdir), False
		yield _generateJob(testdir, index = 1, jobActs = lambda job: job.pid(0)), True
		
	def testIsRunning(self, job, ret):
		r = Runner(job)
		self.assertEqual(r.isRunning(), ret)
		
	def dataProvider_testSubmit(self, testdir):
		# job cached
		yield _generateJob(testdir, pProps = {'ncjobids': []}), True
		# job is running
		yield _generateJob(
			testdir,
			index = 1,
			jobActs = lambda job: job.pid(0)
		), True, ['SUBMIT', "[2/0] is already running, skip submission."]
		# submission failure
		yield _generateJob(
			testdir,
			index = 2,
			pProps = {'script': TemplatePyPPL('#!/usr/bin/env bash\nexit 1')}
		), False, ['ERROR', "[3/0] Submission failed with return code: 1."]
		# submission failure exception
		yield _generateJob(
			testdir,
			index = 3,
			pProps = {'script': TemplatePyPPL('exit 1')}
		), False, ['ERROR', "[4/0] Submission failed with exception: [Errno 8] Exec format error"]
		# submission success
		yield _generateJob(
			testdir,
			index = 4,
			pProps = {'script': TemplatePyPPL('#!/usr/bin/env bash\nexit 0')}
		), True
		
	def testSubmit(self, job, ret, errs = []):
		r = Runner(job)
		with helpers.log2str(levels = 'all') as (out, err):
			o = r.submit()
		stderr = err.getvalue()
		self.assertEqual(o, ret)
		for err in errs:
			self.assertIn(err, stderr)
		if not ret:
			self.assertEqual(job.rc(), Job.RC_SUBMITFAIL)
	
	def dataProvider_testFinish(self, testdir):
		yield _generateJob(testdir),
		
	def testFinish(self, job):
		r = Runner(job)
		self.assertIsNone(r.finish())
		
	def dataProvider_testGetpid(self, testdir):
		yield _generateJob(testdir),
		
	def testGetpid(self, job):
		r = Runner(job)
		self.assertIsNone(r.getpid())
	
	def dataProvider_testRetry(self, testdir):
		yield _generateJob(testdir, pProps = {'errhow': 'terminate'}), False
		yield _generateJob(testdir, index = 1, pProps = {'errhow': 'retry', 'errntry': 3}), True, [
			'RETRY',
			'[2/0] Retrying job ... 1'
		]
		yield _generateJob(testdir, index = 2, pProps = {'errhow': 'retry', 'errntry': 0}), False
		
	def testRetry(self, job, ret, errs = []):
		r = Runner(job)
		with helpers.log2str() as (out, err):
			o = r.retry()
		stderr = err.getvalue()
		self.assertEqual(o, ret)
		for err in errs:
			self.assertIn(err, stderr)
			
	def dataProvider_testFlush(self, testdir):
		job = _generateJob(testdir, pProps = {'echo': {'jobs': []}})
		yield job, {'': ('', None)}, {'': ('', None)}
		
		job1 = _generateJob(testdir, index = 1, pProps = {'echo': {'jobs': [1], 'type': {'stdout': None}}})
		yield job1, {'': ('', '')}, {}
		yield job1, {'123': ('123', '')}, {}
		yield job1, OrderedDict([
			('123\n', ('123', '')),
			('456\n78', ('456', '78')),
			('910', ('78910', ''))
		]), {}
		# filter
		job2 = _generateJob(testdir, index = 2, pProps = {'echo': {'jobs': [2], 'type': {'stdout': '^a'}}})
		yield job1, {'': ('', '')}, {}
		yield job1, {'123': ('', '')}, {}
		yield job1, OrderedDict([
			('123\n', ('', '')),
			('456\na78', ('', 'a78')),
			('910', ('a78910', ''))
		]), {}
		# stderr
		job3 = _generateJob(testdir, index = 3, pProps = {'echo': {'jobs': [3], 'type': {'stderr': None}}})
		yield job3, {}, OrderedDict([
			('pyppl.log: 123', ('[4/0]  123', ''))
		])
		yield job3, {}, OrderedDict([
			('456\n78', ('456', '78')),
			('9\npyppl.log', ('789', 'pyppl.log')),
			(': 123', ('', 'pyppl.log: 123')),
			('a\n78', ('[4/0]  123a', '78')),
			('b', ('78b', '')),
		])
		# stderr filter
		job4 = _generateJob(testdir, index = 4, pProps = {'echo': {'jobs': [4], 'type': {'stderr': '^7'}}})
		yield job4, {}, OrderedDict([
			('pyppl.log.flag ', ('[5/0] ', ''))
		])
		yield job4, {}, OrderedDict([
			('456\n78', ('', '78')),
			('9\npyppl.log', ('789', 'pyppl.log')),
			(': 123', ('', 'pyppl.log: 123')),
			('a\n78', ('[5/0]  123a', '78')),
			('b', ('78b', '')),
		])
		
			
	def testFlush(self, job, outs, errs):
		r = Runner(job)
		lastout, lasterr = '', ''
		foutr = open(job.outfile, 'r')
		ferrr = open(job.errfile, 'r')
		foutw = open(job.outfile, 'w')
		ferrw = open(job.errfile, 'w')
		for i, k in enumerate(outs.keys()):
			o, lo = outs[k] # out, lastout
			end = i == len(outs) - 1
			foutw.write(k)
			foutw.flush()
			with helpers.log2str() as (out, err):
				lastout, lasterr = r._flush(foutr, ferrr, lastout, lasterr, end)
			self.assertEqual(lastout, lo)
			self.assertIn(o, out.getvalue())
		for i, k in enumerate(errs.keys()):
			e, le = errs[k]
			end = i == len(errs) - 1
			ferrw.write(k)
			ferrw.flush()
			with helpers.log2str() as (out, err):
				lastout, lasterr = r._flush(foutr, ferrr, lastout, lasterr, end)
			self.assertEqual(lasterr, le)
			self.assertIn(e, err.getvalue())
		foutr.close()
		ferrr.close()
		foutw.close()
		ferrw.close()
			
	def dataProvider_testRun(self, testdir):
		# job cached
		yield _generateJob(testdir, pProps = {'ncjobids': []}), True
		yield _generateJob(
			testdir,
			index = 1,
			pProps = {'ncjobids': [1], 'echo': {'jobs': []}},
			jobActs = lambda job: job.rc(1)
		), False
		yield _generateJob(
			testdir,
			index = 2,
			pProps = {
				'ncjobids': [2],
				'echo': {'jobs': [2], 'type': {'stdout': None}},
				'script': TemplatePyPPL('#!/usr/bin/env bash\nprintf 1\nbash -c \'sleep .5; echo 1 > "%s"\'\nprintf 3' % path.join(testdir, 'p', 'workdir', '3', 'job.rc'))
			}
		), False, ['13']
		yield _generateJob(
			testdir,
			index = 3,
			pProps = {
				'expect': TemplatePyPPL(''),
				'ncjobids': [3],
				'echo': {'jobs': [3], 'type': {'stdout': None}},
				'script': TemplatePyPPL('#!/usr/bin/env bash\nprintf 2\nbash -c \'sleep .5; echo 0 > "%s"\'\nprintf 4' % path.join(testdir, 'p', 'workdir', '4', 'job.rc'))
			}
		), True, ['24']
		
	def testRun(self, job, ret, outs = [], errs = []):
		Runner.INTERVAL = .1
		r = Runner(job)
		with helpers.log2str() as (out, err):
			r.submit()
			o = r.run()
		self.assertEqual(o, ret)
		stdout = out.getvalue()
		stderr = err.getvalue()
		for o in outs:
			self.assertIn(o, stdout)
		for e in errs:
			self.assertIn(e, stderr)

class TestRunnerLocal(helpers.TestCase):
	
	def dataProvider_testInit(self, testdir):
		yield _generateJob(
			testdir, 
			pProps = {'localRunner': {'preScript': 'prescript', 'postScript': 'postscript'}}
		),

	def testInit(self, job):
		r = RunnerLocal(job)
		self.assertIsInstance(r, RunnerLocal)
		self.assertTrue(path.exists(job.script + '.local'))
		self.assertTrue(path.exists(job.script + '.submit'))
		self.assertTextEqual(helpers.readFile(job.script + '.local', str), '\n'.join([
			"#!/usr/bin/env bash",
			"echo $$ > '%s'",
			'trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT',
			'prescript',
			'',
			"%s 1>'%s' 2>'%s'",
			'postscript',
		]) % (job.pidfile, job.rcfile, job.script, job.outfile, job.errfile) + '\n')
		self.assertTextEqual(helpers.readFile(job.script + '.submit', str), '\n'.join([
			"#!/usr/bin/env bash",
			"exec '%s' &"
		]) % (job.script + '.local') + '\n')
		
	
	def dataProvider_testSubmitNRun(self, testdir):
		yield _generateJob(
			testdir,
			pProps = {
				'expect': TemplatePyPPL(''),
				'ncjobids': [0],
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'script': TemplatePyPPL('#!/usr/bin/env bash\nprintf 123\nsleep .5\nprintf 456')
			}
		), True, ['123456']
		yield _generateJob(
			testdir,
			index = 1,
			pProps = {
				'expect': TemplatePyPPL(''),
				'ncjobids': [1],
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'script': TemplatePyPPL('#!/usr/bin/env bash\nprintf 123 >&2\nsleep .5\nprintf 456 >&2\nexit 1')
			}
		), False, [], ['123456']
	
	def testSubmitNRun(self, job, ret, outs = [], errs = []):
		RunnerLocal.INTERVAL = .1
		r = RunnerLocal(job)
		r.submit()
		o = r.run()
		self.assertEqual(o, ret)
		stdout = helpers.readFile(job.outfile, str)
		stderr = helpers.readFile(job.errfile, str)
		for o in outs:
			self.assertIn(o, stdout)
		for e in errs:
			self.assertIn(e, stderr)

class TestRunnerDry(helpers.TestCase):
	
	def dataProvider_testInit(self, testdir):
		yield _generateJob(
			testdir
		),

	def testInit(self, job):
		r = RunnerDry(job)
		self.assertIsInstance(r, RunnerDry)
		self.assertTrue(path.exists(job.script + '.dry'))
		self.assertTrue(path.exists(job.script + '.submit'))
		self.assertTextEqual(helpers.readFile(job.script + '.dry', str), '\n'.join([
			"#!/usr/bin/env bash",
			"echo $$ > '%s'",
			'trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT',
			''
		]) % (job.pidfile, job.rcfile) + '\n')
		self.assertTextEqual(helpers.readFile(job.script + '.submit', str), '\n'.join([
			"#!/usr/bin/env bash",
			"exec '%s' &"
		]) % (job.script + '.dry') + '\n')
		
	
	def dataProvider_testSubmitNRun(self, testdir):
		yield _generateJob(
			testdir,
			pProps = {
				'expect': TemplatePyPPL(''),
				'ncjobids': [0],
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'script': TemplatePyPPL('')
			}
		), True
		
		job = _generateJob(
			testdir,
			index = 1,
			pProps = {
				'expect': TemplatePyPPL(''),
				'ncjobids': [1],
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'script': TemplatePyPPL(''),
				'output': {
					'a': ('file', TemplatePyPPL('runndry.txt')),
					'b': ('dir', TemplatePyPPL('runndry.dir')),
					'c': ('var', TemplatePyPPL('runndry.dir')),
				}
			}
		)
		yield job, True, [path.join(job.outdir, 'runndry.txt')], [path.join(job.outdir, 'runndry.dir')]
	
	def testSubmitNRun(self, job, ret, files = [], dirs = []):
		RunnerDry.INTERVAL = .1
		r = RunnerDry(job)
		r.submit()
		o = r.run()
		self.assertEqual(o, ret)
		for f in files:
			self.assertTrue(path.isfile(f))
		for d in dirs:
			self.assertTrue(path.isdir(d))
			
	def dataProvider_testFinish(self, testdir):
		yield _generateJob(
			testdir,
			pProps = {
				'expect': TemplatePyPPL(''),
			},
			jobActs = lambda job: job.rc(0) or job.cache()
		), 
			
	def testFinish(self, job):
		r = RunnerDry(job)
		r.finish()
		self.assertTrue(job.succeed())
		self.assertFalse(path.isfile(job.cachefile))

class TestRunnerSsh(helpers.TestCase):
	
	def _localSshAlive():
		return utils.dumbPopen('ps axf | grep sshd | grep -v grep', shell = True).wait() == 0
	
	def dataProvider_testIsServerAlive(self):
		if self._localSshAlive():
			yield 'localhost', None, True
		yield 'blahblah', None, False
	
	def testIsServerAlive(self, server, key, ret):
		self.assertEqual(RunnerSsh.isServerAlive(server, key), ret)
		
	def dataProvider_testInit(self, testdir):
		yield _generateJob(
			testdir
		), RunnerSshError, 'No server found for ssh runner.'
		
		servers = ['server1', 'server2', 'localhost']
		keys    = ['key1', 'key2']
		yield _generateJob(
			testdir,
			index = 1,
			pProps = {'sshRunner': {
				'servers': servers,
				'keys'   : keys,
				'checkAlive': False,
			}}
		),
		
		yield _generateJob(
			testdir,
			index = 2,
			pProps = {'sshRunner': {
				'servers': servers,
				'keys'   : keys,
				'checkAlive': False
			}}
		),
		
		yield _generateJob(
			testdir,
			index = 3,
			pProps = {'sshRunner': {
				'servers': servers,
				'keys'   : keys,
				'checkAlive': False
			}}
		),
		
		if self._localSshAlive():
			# should be localhost
			yield _generateJob(
				testdir,
				index = 4,
				pProps = {'sshRunner': {
					'servers': servers,
					'keys'   : keys,
					'checkAlive': True
				}}
			),
		else:
			yield _generateJob(
				testdir,
				index = 4,
				pProps = {'sshRunner': {
					'servers': servers,
					'keys'   : keys,
					'checkAlive': True
				}}
			), RunnerSshError, 'No server is alive.'
		
		# no server is alive
		yield _generateJob(
			testdir,
			index = 5,
			pProps = {'sshRunner': {
				'servers': ['server1', 'server2', 'server3'],
				'checkAlive': True
			}}
		), RunnerSshError, 'No server is alive.'

	def testInit(self, job, exception = None, msg = None):
		self.maxDiff = None
		if exception:
			self.assertRaisesStr(exception, msg, RunnerSsh, job)
		else:
			r = RunnerSsh(job)
			servers = job.proc.sshRunner['servers']
			keys = job.proc.sshRunner['keys']
			sid = (RunnerSsh.SERVERID.value - 1) % len(servers)
			server = servers[sid]
			key = ('-i ' + keys[sid]) if sid < len(keys) else ''
			self.assertIsInstance(r, RunnerSsh)
			self.assertTrue(path.exists(job.script + '.ssh'))
			self.assertTrue(path.exists(job.script + '.submit'))
			self.assertTextEqual(helpers.readFile(job.script + '.ssh', str), '\n'.join([
				"#!/usr/bin/env bash",
				"",
				"echo $$ > '%s'",
				'trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT',
				'ssh %s %s cd %s; %s',
			]) % (job.pidfile, job.rcfile, server, key, getcwd(), job.script) + '\n')
			self.assertTextEqual(helpers.readFile(job.script + '.submit', str), '\n'.join([
				"#!/usr/bin/env bash",
				"exec '%s' &"
			]) % (job.script + '.ssh') + '\n')
		
	
	def dataProvider_testSubmitNRun(self, testdir):
		yield _generateJob(
			testdir,
			pProps = {
				'expect': TemplatePyPPL(''),
				'ncjobids': [0],
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'sshRunner': {
					'servers': ['server1', 'server2', 'localhost'],
					'checkAlive': True,
					'preScript': 'alias ssh="%s"' % (path.join(__folder__, 'mocks', 'ssh')),
					'postScript': ''
				},
				'script': TemplatePyPPL('#!/usr/bin/env bash\nprintf 123\nsleep .5\nprintf 456')
			}
		), True, ['123456']
		yield _generateJob(
			testdir,
			index = 1,
			pProps = {
				'expect': TemplatePyPPL(''),
				'ncjobids': [1],
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'sshRunner': {
					'servers': ['server1', 'server2', 'localhost'],
					'checkAlive': True,
					'preScript': 'alias ssh="%s"' % (path.join(__folder__, 'mocks', 'ssh')),
					'postScript': ''
				},
				'script': TemplatePyPPL('#!/usr/bin/env bash\nprintf 123 >&2\nsleep .5\nprintf 456 >&2\nexit 1')
			}
		), False, [], ['123456']
	
	def testSubmitNRun(self, job, ret, outs = [], errs = []):
		RunnerSsh.INTERVAL = .1
		r = RunnerSsh(job)
		r.submit()
		o = r.run()
		self.assertEqual(o, ret)
		stdout = helpers.readFile(job.outfile, str)
		stderr = helpers.readFile(job.errfile, str)
		for o in outs:
			self.assertIn(o, stdout)
		for e in errs:
			self.assertIn(e, stderr)

class TestRunnerSge(helpers.TestCase):
	
	def dataProvider_testInit(self, testdir):
		yield _generateJob(
			testdir,
			pProps = {
				'sgeRunner': {
					'sge.N': 'SgeJobName',
					'sge.q': 'queue',
					'sge.j': 'y',
					'sge.o': path.join(testdir, 'stdout'),
					'sge.e': path.join(testdir, 'stderr'),
					'sge.M': 'xxx@abc.com',
					'sge.m': 'yes',
					'sge.mem': '4G',
					'sge.notify': True,
					'preScript': 'alias qsub="%s"' % (path.join(__folder__, 'mocks', 'qsub')),
					'postScript': ''
				}
			}
		), 'SgeJobName', path.join(testdir, 'stdout'), path.join(testdir, 'stderr')
		
		yield _generateJob(
			testdir,
			index  = 1,
			pProps = {
				'sgeRunner': {
					'sge.q': 'queue',
					'sge.j': 'y',
					'sge.M': 'xxx@abc.com',
					'sge.m': 'yes',
					'sge.mem': '4G',
					'sge.notify': True,
					'preScript': 'alias qsub="%s"' % (path.join(__folder__, 'mocks', 'qsub')),
					'postScript': ''
				}
			}
		),
		
	def testInit(self, job, jobname = None, outfile = None, errfile = None):
		self.maxDiff = None
		r = RunnerSge(job)
		self.assertIsInstance(r, RunnerSge)
		self.assertTrue(path.exists(job.script + '.sge'))
		self.assertTextEqual(helpers.readFile(job.script + '.sge', str), '\n'.join([
			"#!/usr/bin/env bash",
			'#$ -N %s' % (jobname if jobname else '.'.join([
				job.proc.id,
				job.proc.tag,
				job.proc._suffix(),
				str(job.index)
			])),
			'#$ -q queue',
			'#$ -j y',
			'#$ -o %s' % (outfile if outfile else job.outfile),
			'#$ -e %s' % (errfile if errfile else job.errfile),
			'#$ -cwd',
			'#$ -M xxx@abc.com',
			'#$ -m yes',
			'#$ -mem 4G',
			'#$ -notify',
			'',
			'trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % job.rcfile,
			'alias qsub="%s"' % (path.join(__folder__, 'mocks', 'qsub')),
			'',
			job.script,
			'',
			''
		]))
		
	def dataProvider_testGetpid(self, testdir):
		job = _generateJob(
			testdir,
			pProps = {
				'sgeRunner': {
					'qsub': path.join(__folder__, 'mocks', 'qsub'),
					'qstat': path.join(__folder__, 'mocks', 'qstat'),
					'preScript': '',
					'postScript': ''
				}
			}
		)
		helpers.writeFile(job.script, '\n'.join([
			'#!/usr/bin/env bash',
			'%s %s' % (
				# remove the pid after job id done
				path.join(__folder__, 'mocks', 'qsub_done'),
				#str(int(md5(str(job.script) + '.sge').hexdigest()[:8], 16))
				int(md5((job.script + '.sge').encode('utf-8')).hexdigest()[:8], 16)
			)
		]))
		yield job, 
		
	def testGetpid(self, job):
		r = RunnerSge(job)
		r.submit()
		self.assertIn(helpers.readFile(job.pidfile, str), helpers.readFile(job.outfile, str))
		
	def dataProvider_testIsRunning(self, testdir):
		job = _generateJob(
			testdir,
			pProps = {
				'expect': TemplatePyPPL(''),
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'sgeRunner': {
					'qsub': path.join(__folder__, 'mocks', 'qsub'),
					'qstat': path.join(__folder__, 'mocks', 'qstat'),
					'preScript': '',
					'postScript': ''
				}
			}
		)
		helpers.writeFile(job.script, '\n'.join([
			'sleep .1',
			'%s %s' % (
				path.join(__folder__, 'mocks', 'qsub_done'),
				int(md5((job.script + '.sge').encode('utf-8')).hexdigest()[:8], 16)
			)
		]))
		yield job,
		
		job1 = _generateJob(
			testdir,
			index = 1,
			pProps = {
				'expect': TemplatePyPPL(''),
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'sgeRunner': {
					'qsub': path.join(__folder__, 'mocks', 'qsub'),
					'qstat': '__command_not_exists__',
					'preScript': '',
					'postScript': ''
				}
			}
		)
		helpers.writeFile(job1.script, '\n'.join([
			'#!/usr/bin/env bash',
			'sleep .1',
			'%s %s' % (
				path.join(__folder__, 'mocks', 'qsub_done'),
				int(md5((job1.script + '.sge').encode('utf-8')).hexdigest()[:8], 16)
			)
		]))
		yield job1, False, False, False
		
	def testIsRunning(self, job, beforesub = False, aftersub = True, afterrun = False):
		RunnerSge.INTERVAL = .2
		r = RunnerSge(job)
		self.assertEqual(r.isRunning(), beforesub)
		r.submit()
		self.assertEqual(r.isRunning(), aftersub)
		with helpers.log2str():
			r.run()
		self.assertEqual(r.isRunning(), afterrun)


class TestRunnerSlurm(helpers.TestCase):
	
	def dataProvider_testInit(self, testdir):
		yield _generateJob(
			testdir,
			pProps = {
				'slurmRunner': {
					'slurm.J': 'SlurmJobName',
					'slurm.q': 'queue',
					'slurm.j': 'y',
					'slurm.o': path.join(testdir, 'stdout'),
					'slurm.e': path.join(testdir, 'stderr'),
					'slurm.M': 'xxx@abc.com',
					'slurm.m': 'yes',
					'slurm.mem': '4G',
					'slurm.notify': True,
					'cmdPrefix': 'srun prefix',
					'preScript': 'alias srun="%s"' % (path.join(__folder__, 'mocks', 'srun')),
					'postScript': ''
				}
			}
		), 'SlurmJobName', path.join(testdir, 'stdout'), path.join(testdir, 'stderr')
		
		yield _generateJob(
			testdir,
			index  = 1,
			pProps = {
				'slurmRunner': {
					'slurm.q': 'queue',
					'slurm.j': 'y',
					'slurm.M': 'xxx@abc.com',
					'slurm.m': 'yes',
					'slurm.mem': '4G',
					'slurm.notify': True,
					'cmdPrefix': 'srun prefix',
					'preScript': 'alias srun="%s"' % (path.join(__folder__, 'mocks', 'srun')),
					'postScript': ''
				}
			}
		),
		
	def testInit(self, job, jobname = None, outfile = None, errfile = None):
		self.maxDiff = None
		r = RunnerSlurm(job)
		self.assertIsInstance(r, RunnerSlurm)
		self.assertTrue(path.exists(job.script + '.slurm'))
		self.assertTextEqual(helpers.readFile(job.script + '.slurm', str), '\n'.join([
			"#!/usr/bin/env bash",
			'#SBATCH -J %s' % (jobname if jobname else '.'.join([
				job.proc.id,
				job.proc.tag,
				job.proc._suffix(),
				str(job.index)
			])),
			'#SBATCH -o %s' % (outfile if outfile else job.outfile),
			'#SBATCH -e %s' % (errfile if errfile else job.errfile),
			'#SBATCH -M xxx@abc.com',
			'#SBATCH -j y',
			'#SBATCH -m yes',
			'#SBATCH --mem 4G',
			'#SBATCH --notify',
			'#SBATCH -q queue',
			'',
			'trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % job.rcfile,
			'alias srun="%s"' % (path.join(__folder__, 'mocks', 'srun')),
			'',
			'srun prefix ' + job.script,
			'',
			''
		]))
		
	def dataProvider_testGetpid(self, testdir):
		job = _generateJob(
			testdir,
			pProps = {
				'slurmRunner': {
					'sbatch': path.join(__folder__, 'mocks', 'sbatch'),
					'squeue': path.join(__folder__, 'mocks', 'squeue'),
					'srun': path.join(__folder__, 'mocks', 'srun'),
					'preScript': 'alias srun="%s"' % (path.join(__folder__, 'mocks', 'srun')),
					'postScript': ''
				}
			}
		)
		helpers.writeFile(job.script, '\n'.join([
			'%s %s' % (
				# remove the pid after job id done
				path.join(__folder__, 'mocks', 'sbatch_done'),
				#str(int(md5(str(job.script) + '.sge').hexdigest()[:8], 16))
				int(md5((job.script + '.slurm').encode('utf-8')).hexdigest()[:8], 16)
			)
		]))
		yield job, 
		
		job1 = _generateJob(
			testdir,
			index = 1,
			pProps = {
				'slurmRunner': {
					'sbatch': path.join(__folder__, 'mocks', 'sbatch'),
					'squeue': path.join(__folder__, 'mocks', 'squeue'),
					'srun': path.join(__folder__, 'mocks', 'srun'),
					'preScript': 'alias srun="%s"' % (path.join(__folder__, 'mocks', 'srun')),
					'postScript': 'echo >\'%s\'' % (path.join(testdir, 'p', 'workdir', '2', 'job.pid'))
				}
			}
		)
		yield job1, 
		
	def testGetpid(self, job):
		r = RunnerSlurm(job)
		r.submit()
		self.assertIn(helpers.readFile(job.pidfile, str), helpers.readFile(job.outfile, str))
		
	def dataProvider_testIsRunning(self, testdir):
		job = _generateJob(
			testdir,
			pProps = {
				'expect': TemplatePyPPL(''),
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'slurmRunner': {
					'sbatch': path.join(__folder__, 'mocks', 'sbatch'),
					'squeue': path.join(__folder__, 'mocks', 'squeue'),
					'srun': path.join(__folder__, 'mocks', 'qsub'),
					'preScript': '',
					'postScript': ''
				}
			}
		)
		helpers.writeFile(job.script, '\n'.join([
			'#!/usr/bin/env bash',
			'sleep .1',
			'%s %s' % (
				path.join(__folder__, 'mocks', 'sbatch_done'),
				int(md5((job.script + '.slurm').encode('utf-8')).hexdigest()[:8], 16)
			)
		]))
		yield job,
		
		job1 = _generateJob(
			testdir,
			index = 1,
			pProps = {
				'expect': TemplatePyPPL(''),
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'slurmRunner': {
					'sbatch': path.join(__folder__, 'mocks', 'sbatch'),
					'squeue': '__command_not_exists__',
					'srun': path.join(__folder__, 'mocks', 'srun'),
					'postScript': ''
				}
			}
		)
		helpers.writeFile(job1.script, '\n'.join([
			'#!/usr/bin/env bash',
			'sleep .1',
			'%s %s' % (
				path.join(__folder__, 'mocks', 'sbatch_done'),
				int(md5((job1.script + '.slurm').encode('utf-8')).hexdigest()[:8], 16)
			)
		]))
		yield job1, False, False, False
		
		job2 = _generateJob(
			testdir,
			index = 2,
			pProps = {
				'expect': TemplatePyPPL(''),
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'slurmRunner': {
					'sbatch': '__command_not_exists__',
					'squeue': path.join(__folder__, 'mocks', 'squeue'),
					'srun': path.join(__folder__, 'mocks', 'srun'),
					'postScript': ''
				}
			}
		)
		helpers.writeFile(job2.script)
		yield job1, False, False, False
		
	def testIsRunning(self, job, beforesub = False, aftersub = True, afterrun = False):
		RunnerSlurm.INTERVAL = .2
		r = RunnerSlurm(job)
		self.assertEqual(r.isRunning(), beforesub)
		r.submit()
		self.assertEqual(r.isRunning(), aftersub)
		with helpers.log2str():
			r.run()
		self.assertEqual(r.isRunning(), afterrun)


if __name__ == '__main__':
	clearMockQueue()
	unittest.main(verbosity=2)
