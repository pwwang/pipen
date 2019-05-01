import helpers, testly, unittest, sys

from os import path, getcwd, makedirs, remove
from shutil import rmtree
from tempfile import gettempdir
from hashlib import md5
from collections import OrderedDict
from subprocess import list2cmdline
from pyppl import Job, utils, runners
from pyppl.runners import Runner, RunnerLocal, RunnerDry, RunnerSsh, RunnerSge, RunnerSlurm, RunnerSshError
from pyppl.template import TemplateLiquid
#from pyppl.runners.helpers import Helper, LocalHelper, SgeHelper, SlurmHelper, SshHelper

__here__ = path.realpath(path.dirname(__file__))

def clearMockQueue():
	qsubQfile   = path.join(__here__, 'mocks', 'qsub.queue.txt')
	sbatchQfile = path.join(__here__, 'mocks', 'sbatch.queue.txt')
	helpers.writeFile(qsubQfile, '')
	helpers.writeFile(sbatchQfile, '')

def createJob(testdir, index = 0, config = None):
	config = config or {}
	config['workdir']  = testdir
	config['procsize'] = config.get('procsize', 1)
	config['proc']     = config.get('proc', 'pTestRunner')
	config['tag']      = config.get('tag', 'notag')
	config['suffix']   = config.get('suffix', 'suffix')
	jobdir = path.join(testdir, str(index+1))
	if not path.exists(jobdir):
		makedirs(jobdir)
	with open(path.join(jobdir, 'job.script'), 'w') as f:
		f.write('#!/usr/bin/env bash\n')
		f.write(config.get('_script', ''))
	open(path.join(jobdir, 'job.stdout'), 'w').close()
	open(path.join(jobdir, 'job.stderr'), 'w').close()
	return Job(index, config)

class TestRunner(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestRunner')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)
	
	def dataProvider_testInit(self):
		yield createJob(path.join(self.testdir, 'pTestInit')),

	def testInit(self, job):
		r = Runner(job)
		self.assertIsInstance(r, Runner)
		self.assertIs(r.job, job)
	
	def dataProvider_testIsRunning(self):
		yield createJob(path.join(self.testdir, 'pTestIsRunning'), 0), False

		job1 = createJob(path.join(self.testdir, 'pTestIsRunning'), 1)
		r = utils.cmdy.bash(c = 'sleep 10', bg = True)
		job1.pid = r.pid
		yield job1, True

	def testIsRunning(self, job, ret):
		r = Runner(job)
		self.assertEqual(r.isRunning(), ret)
		if ret:
			r.kill()
			self.assertEqual(r.isRunning(), False)
	
	def dataProvider_testSubmit(self):
		job = createJob(path.join(self.testdir, 'pTestSubmit'))
		yield job, utils.cmdy.bash(job.script, _hold = True).cmd

	def testSubmit(self, job, cmd):
		r = Runner(job)
		r.wrapScript()
		self.assertEqual(r.script, job.script + '.') # Runner doesn't have a name
		self.assertEqual(r.submit().cmd, cmd + '.')

	# Covered by job.run
	# def dataProvider_testRun(self):
	# 	job = createJob(path.join(self.testdir, 'pTestRun'), config = {
	# 		'echo': {'jobs': [0], 'type': {'stderr': None, 'stdout': None}}
	# 	})
	# 	yield job, 

	# def testRun(self, job, stdout = '', stderr = ''):
	# 	r = Runner(job)
	# 	r.submit()
	# 	r.run()
	# 	with open(job.outfile, 'r') as f:
	# 		self.assertEqual(f.read().strip(), stdout)
	# 	with open(job.errfile, 'r') as f:
	# 		self.assertEqual(f.read().strip(), stderr)
	# 	with open(job.rcfile, 'r') as f:
	# 		self.assertEqual(f.read().strip(), '0')
	
class TestRunnerLocal(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestRunnerLocal')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)
	
	def dataProvider_testInit(self):
		job = createJob(
			self.testdir, 
			config = {
				'runnerOpts': {
					'localRunner': {'preScript': 'prescript', 'postScript': 'postscript'}
				}
			}
		)
		yield job, """#!/usr/bin/env bash
#
# Collect return code on exit
trap "status=\$?; echo \$status > {jobdir}/job.rc; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
#
# Run pre-script
prescript
#
# Run the real script
{jobdir}/job.script 1> {jobdir}/job.stdout 2> {jobdir}/job.stderr
#
# Run post-script
postscript
#""".format(jobdir = path.dirname(job.rcfile))

	def testInit(self, job, content):
		r = RunnerLocal(job)
		self.assertIsInstance(r, RunnerLocal)
		self.assertEqual(r.script, job.script + '.local')
		self.assertTrue(path.exists(r.script))
		with open(r.script, 'r') as f:
			self.assertEqual(f.read().strip(), content)

class TestRunnerDry(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestRunnerDry')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def dataProvider_testInit(self):
		job = createJob(self.testdir)
		job.output = {
			'a' : {'type': 'file', 'data': 'a.txt'},
			'b' : {'type': 'dir' , 'data': 'b.dir'},
			'c' : {'type': 'var' , 'data': 'c'}
		}
		yield job, """#!/usr/bin/env bash
#
# Collect return code on exit
trap "status=\$?; echo \$status > {jobdir}/job.rc; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
#
# Run pre-script
#
# Run the real script
touch a.txt
mkdir -p b.dir 1> {jobdir}/job.stdout 2> {jobdir}/job.stderr
#
# Run post-script
#""".format(jobdir = path.dirname(job.rcfile))

	def testInit(self, job, content):
		r = RunnerDry(job)
		self.assertIsInstance(r, RunnerDry)
		self.assertEqual(r.script, job.script + '.dry')
		self.assertTrue(path.exists(r.script))
		with open(r.script, 'r') as f:
			self.assertEqual(f.read().strip(), content)

class TestRunnerSsh(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestRunnerSsh')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)		
	
	def dataProvider_testIsServerAlive(self):
		yield 'noalive', None, False
		yield 'blahblah', None, False
	
	def testIsServerAlive(self, server, key, ret):
		self.assertEqual(RunnerSsh.isServerAlive(server, key), ret)
		
	def dataProvider_testInit(self):
		yield createJob(
			self.testdir
		), RunnerSshError, 'No server found for ssh runner.'
		
		servers = ['server1', 'server2', 'localhost']
		keys    = ['key1', 'key2', None]
		yield createJob(
			self.testdir,
			index = 1,
			config = {'runnerOpts': {'sshRunner': {
				'servers': servers,
				'keys'   : keys,
				'checkAlive': False,
			}}}
		),
		
		yield createJob(
			self.testdir,
			index = 2,
			config = {'runnerOpts': {'sshRunner': {
				'servers': servers,
				'keys'   : keys,
				'checkAlive': False
			}}}
		),
		
		yield createJob(
			self.testdir,
			index = 3,
			config = {'runnerOpts': {'sshRunner': {
				'servers': servers,
				'keys'   : keys,
				'checkAlive': False,
				'preScript': 'ls',
				'postScript': 'ls',
			}}}
		),
		# 4
		if RunnerSsh.isServerAlive('localhost', None, 1):
			# should be localhost'
			yield createJob(
				self.testdir,
				index = 4,
				config = {'runnerOpts': {'sshRunner': {
					'servers': servers,
					'keys'   : keys,
					'checkAlive': 1
				}}}
			),
		else:
			yield createJob(
				self.testdir,
				index = 4,
				config = {'runnerOpts': {'sshRunner': {
					'servers': servers,
					'keys'   : keys,
					'checkAlive': 1
				}}}
			), RunnerSshError, 'No server is alive.'
		
		# no server is alive
		yield createJob(
			self.testdir,
			index = 5,
			config = {'runnerOpts': {'sshRunner': {
				'servers': ['server1', 'server2', 'server3'],
				'checkAlive': True,
			}}}
		), RunnerSshError, 'No server is alive.'

	def testInit(self, job, exception = None, msg = None):
		self.maxDiff = None
		RunnerSsh.LIVE_SERVERS = None
		if exception:
			self.assertRaisesRegex(exception, msg, RunnerSsh, job)
		else:
			r = RunnerSsh(job)
			servers = job.config['runnerOpts']['sshRunner']['servers']
			keys = job.config['runnerOpts']['sshRunner']['keys']

			sid = RunnerSsh.LIVE_SERVERS[job.index % len(RunnerSsh.LIVE_SERVERS)]
			server = servers[sid]
			key = ('-i ' + keys[sid]) if keys[sid] else ''
			self.assertIsInstance(r, RunnerSsh)
			self.assertTrue(path.exists(job.script + '.ssh'))
			#self.assertTrue(path.exists(job.script + '.submit'))
			preScript  = job.config['runnerOpts']['sshRunner'].get('preScript', '')
			preScript  = preScript and preScript + '\n'
			postScript = job.config['runnerOpts']['sshRunner'].get('postScript', '')
			postScript = postScript and postScript + '\n'
			helpers.assertTextEqual(self, helpers.readFile(job.script + '.ssh', str), """#!/usr/bin/env bash
# run on server: {server}
#
# Collect return code on exit
trap "status=\$?; echo \$status > {jobdir}/job.rc; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
#
# Run pre-script
{preScript}#
# Run the real script
cd {cwd}
{jobdir}/job.script 1> {jobdir}/job.stdout 2> {jobdir}/job.stderr
#
# Run post-script
{postScript}#""".format(server = server, jobdir = path.dirname(job.script), cwd = getcwd(), preScript = preScript, postScript = postScript))
		
	def dataProvider_testSubmit(self):
		job0 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			config = {
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'runnerOpts': {'sshRunner': {
					'servers': ['server1', 'server2', 'localhost'],
					'checkAlive': False,
					'ssh': path.join(__here__, 'mocks', 'ssh')
				}},
			}
		)

		yield job0, ' '.join([
			path.join(__here__, 'mocks', 'ssh'), 
			'-t',
			'server1',
			"'bash " + job0.script + ".ssh'"
		])
		job1 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			index = 1,
			config = {
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'runnerOpts': {'sshRunner': {
					'servers': ['server1', 'server2', 'localhost'],
					'checkAlive': 1,
				}},
			}
		)
		if RunnerSsh.isServerAlive('localhost', None, 1):
			yield job1, ' '.join([
				'ssh', 
				'-t',
				'localhost',
				"'bash " + job1.script + ".ssh'"
			])

		job2 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			index = 2,
			config = {
				'echo': {'jobs': [2], 'type': {'stdout': None}},
				'runnerOpts': {'sshRunner': {
					'servers': ['server1', 'server2', 'localhost'],
					'checkAlive': False,
				}},
			}
		)
		if RunnerSsh.isServerAlive('localhost', None, 1):
			yield job2, ' '.join([
				'ssh', 
				'-t',
				'localhost',
				"'bash " + job2.script + ".ssh'"
			]), 0
	
	def testSubmit(self, job, cmd, rc = 0):
		RunnerSsh.INTERVAL = .1
		RunnerSsh.LIVE_SERVERS = None
		if job.config['runnerOpts']['sshRunner']['checkAlive'] and not RunnerSsh.isServerAlive('localhost', timeout = 1):
			self.assertRaises(RunnerSshError, RunnerSsh, job)
		else:
			r = RunnerSsh(job)
			if rc == 1:
				remove(r.script)
			c = r.submit()
			self.assertEqual(c.rc, rc)
			self.assertEqual(c.cmd, cmd)

	def dataProvider_testKill(self):
		job0 = createJob(
			path.join(self.testdir, 'pTestKill'),
			index  = 9,
			config = {
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'runnerOpts': {'sshRunner': {
					'servers': ['server1', 'server2', 'localhost'],
					'checkAlive': False,
					'ssh': path.join(__here__, 'mocks', 'ssh')
				}},
				'_script': 'sleep 3; sleep 3 &'
			}
		)
		yield job0, 
	
	def testKill(self, job):
		RunnerSsh.INTERVAL = .1
		RunnerSsh.LIVE_SERVERS = None
		r = RunnerSsh(job)
		self.assertFalse(r.isRunning())
		r.job.pid = r.submit().pid
		self.assertTrue(r.isRunning())
		r.kill()
		self.assertFalse(r.isRunning())


class TestRunnerSge(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestRunnerSge')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)
	
	def dataProvider_testInit(self):
		yield createJob(
			self.testdir,
			config = {
				'runnerOpts': {'sgeRunner': {
					'sge.N': 'SgeJobName',
					'sge.q': 'queue',
					'sge.j': 'y',
					'sge.M': 'xxx@abc.com',
					'sge.m': 'yes',
					'sge.mem': '4G',
					'sge.notify': True,
					'preScript': 'alias qsub="%s"' % (path.join(__here__, 'mocks', 'qsub')),
					'postScript': '',
					'qsub': 'qsub',
					'qstat': 'qstat',
					'qdel': 'qdel',
				}}
			}
		), 'SgeJobName', path.join(self.testdir, 'stdout'), path.join(self.testdir, 'stderr')
		
		yield createJob(
			self.testdir,
			index  = 1,
			config = {
				'runnerOpts': {'sgeRunner': {
					'sge.q': 'queue',
					'sge.j': 'y',
					'sge.M': 'xxx@abc.com',
					'sge.m': 'yes',
					'sge.mem': '4G',
					'sge.notify': True,
					'preScript': 'alias qsub="%s"' % (path.join(__here__, 'mocks', 'qsub')),
					'postScript': ''
				}}
			}
		),
		
	def testInit(self, job, jobname = None, outfile = None, errfile = None):
		self.maxDiff = 10000
		r = RunnerSge(job)
		self.assertIsInstance(r, RunnerSge)
		self.assertEqual(r.script, job.script + '.sge')
		self.assertTrue(r.script)
		helpers.assertTextEqual(self, helpers.readFile(job.script + '.sge', str), """#!/usr/bin/env bash
#$ -N {name}
#$ -q queue
#$ -j y
#$ -cwd
#$ -M xxx@abc.com
#$ -m yes
#$ -o {jobdir}/job.stdout
#$ -e {jobdir}/job.stderr
#$ -mem 4G
#$ -notify
#
# Collect return code on exit
trap "status=\$?; echo \$status > {jobdir}/job.rc; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
#
# Run pre-script
alias qsub="{qsub}"
#
# Run the real script
{jobdir}/job.script
#
# Run post-script
#""".format(
		jobdir = path.dirname(r.script), 
		name   = jobname or '{config[proc]}.{config[tag]}.{config[suffix]}.{index}'.format(
			config = r.job.config,
			index  = r.job.index + 1
		),
		qsub = (path.join(__here__, 'mocks', 'qsub'))
	))
	
	def dataProvider_testSubmit(self):
		job0 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			config = {
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'runnerOpts': {'sgeRunner': {
					'preScript' : '',
					'postScript': '',
					'qsub'      : path.join(__here__, 'mocks', 'qsub'),
					'qstat'     : path.join(__here__, 'mocks', 'qstat'),
					'qdel'      : path.join(__here__, 'mocks', 'qdel'),
				}},
			}
		)
		yield job0, [
			path.join(__here__, 'mocks', 'qsub'), 
			job0.script + '.sge'
		]

		job1 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			index = 1,
			config = {
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'runnerOpts': {'sgeRunner': {
					'preScript' : '',
					'postScript': '',
					'qsub'      : path.join(__here__, 'mocks', 'sbatch'),
					'qstat'     : path.join(__here__, 'mocks', 'qstat'),
					'qdel'      : path.join(__here__, 'mocks', 'qdel'),
				}},
			}
		)
		yield job1, [
			path.join(__here__, 'mocks', 'sbatch'), 
			job1.script + '.sge'
		], job1.RC_SUBMITFAILED

		job2 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			index = 2,
			config = {
				'echo': {'jobs': [2], 'type': {'stdout': None}},
				'runnerOpts': {'sgeRunner': {
					'preScript' : '',
					'postScript': '',
					'qsub'      : path.join(__here__, 'mocks', '_notexist_'),
					'qstat'     : path.join(__here__, 'mocks', 'qstat'),
					'qdel'      : path.join(__here__, 'mocks', 'qdel'),
				}},
			}
		)
		yield job2, [
			path.join(__here__, 'mocks', '_notexist_'), 
			job2.script + '.sge'
		], 127 # command not found
	
	def testSubmit(self, job, cmd, rc = 0):
		RunnerSge.INTERVAL = .1
		r = RunnerSge(job)
		c = r.submit()
		self.assertEqual(c.rc, rc)
		self.assertEqual(c.cmd, list2cmdline(cmd))

	def dataProvider_testKill(self):
		job0 = createJob(
			path.join(self.testdir, 'pTestKill'),
			config = {
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'runnerOpts': {'sgeRunner': {
					'preScript' : '',
					'postScript': '',
					'qsub'      : path.join(__here__, 'mocks', 'qsub'),
					'qstat'     : path.join(__here__, 'mocks', 'qstat'),
					'qdel'      : path.join(__here__, 'mocks', 'qdel'),
				}},
				'_script': 'sleep 3'
			}
		)
		yield job0, 

		job1 = createJob(
			path.join(self.testdir, 'pTestKill'),
			config = {
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'runnerOpts': {'sgeRunner': {
					'preScript' : '',
					'postScript': '',
					'qsub'      : path.join(__here__, 'mocks', 'qsub'),
					'qstat'     : path.join(__here__, 'mocks', '_notexist_'),
					'qdel'      : path.join(__here__, 'mocks', 'qdel'),
				}},
				'_script': 'sleep 3'
			}
		)
		yield job1, False
	
	def testKill(self, job, beforekill = True):
		RunnerSge.INTERVAL = .1
		r = RunnerSge(job)
		self.assertFalse(r.isRunning())
		r.submit()
		self.assertEqual(r.isRunning(), beforekill)
		r.kill()
		self.assertFalse(r.isRunning())

class TestRunnerSlurm(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestRunnerSlurm')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)
	
	def dataProvider_testInit(self):
		yield createJob(
			path.join(self.testdir, 'pTestInit'),
			config = {
				'runnerOpts': {'slurmRunner': {
					'slurm.J': 'SlurmJobName',
					'slurm.q': 'queue',
					'slurm.j': 'y',
					'slurm.M': 'xxx@abc.com',
					'slurm.m': 'yes',
					'slurm.mem': '4G',
					'slurm.notify': True,
					'preScript': '',
					'postScript': '',
					'cmdPrefix': 'srun prefix',
					'sbatch': path.join(__here__, 'mocks', 'sbatch'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', 'squeue'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}}
			}
		), 'SlurmJobName', path.join(self.testdir, 'stdout'), path.join(self.testdir, 'stderr')
		
		yield createJob(
			path.join(self.testdir, 'pTestInit'),
			index  = 1,
			config = {
				'runnerOpts': {'slurmRunner': {
					#'slurm.J': 'SlurmJobName',
					'slurm.q': 'queue',
					'slurm.j': 'y',
					'slurm.M': 'xxx@abc.com',
					'slurm.m': 'yes',
					'slurm.mem': '4G',
					'slurm.notify': True,
					'cmdPrefix': 'srun prefix',
					'preScript': '',
					'postScript': '',
					'sbatch': path.join(__here__, 'mocks', 'sbatch'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', 'squeue'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}}
			}
		),
		
	def testInit(self, job, jobname = None, outfile = None, errfile = None):
		self.maxDiff = 10000
		r = RunnerSlurm(job)
		self.assertIsInstance(r, RunnerSlurm)
		self.assertEqual(r.script, job.script + '.slurm')
		self.assertTrue(r.script)
		helpers.assertTextEqual(self, helpers.readFile(job.script + '.slurm', str), """#!/usr/bin/env bash
#SBATCH -J {name}
#SBATCH -o {jobdir}/job.stdout
#SBATCH -e {jobdir}/job.stderr
#SBATCH -M xxx@abc.com
#SBATCH -j y
#SBATCH -m yes
#SBATCH --mem 4G
#SBATCH --notify
#SBATCH -q queue
#
# Collect return code on exit
trap "status=\$?; echo \$status > {jobdir}/job.rc; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT
#
# Run pre-script
#
# Run the real script
{srun} {jobdir}/job.script
#
# Run post-script
#""".format(
		jobdir = path.dirname(job.script), 
		name = jobname or '{config[proc]}.{config[tag]}.{config[suffix]}.{index}'.format(config = job.config, index = job.index + 1), 
		srun = r.srun.call_args['_exe'], ))
	
	def dataProvider_testSubmit(self):
		job0 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			config = {
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'runnerOpts': {'slurmRunner': {
					'preScript' : '',
					'postScript': '',
					'sbatch': path.join(__here__, 'mocks', 'sbatch'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', 'squeue'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}},
			}
		)
		yield job0, [
			path.join(__here__, 'mocks', 'sbatch'), 
			job0.script + '.slurm'
		]

		job1 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			index = 1,
			config = {
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'runnerOpts': {'slurmRunner': {
					'preScript' : '',
					'postScript': '',
					'sbatch': path.join(__here__, 'mocks', 'qsub'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', 'squeue'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}},
			}
		)
		yield job1, [
			path.join(__here__, 'mocks', 'qsub'), 
			job1.script + '.slurm'
		], 1

		job2 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			index = 2,
			config = {
				'echo': {'jobs': [2], 'type': {'stdout': None}},
				'runnerOpts': {'slurmRunner': {
					'preScript' : '',
					'postScript': '',
					'sbatch': path.join(__here__, 'mocks', '_notexist_'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', 'squeue'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}},
			}
		)
		yield job2, [
			path.join(__here__, 'mocks', '_notexist_'), 
			job2.script + '.slurm'
		], 127
	
	def testSubmit(self, job, cmd, rc = 0):
		RunnerSlurm.INTERVAL = .1
		r = RunnerSlurm(job)
		c = r.submit()
		self.assertEqual(c.rc, rc)
		self.assertEqual(c.cmd, list2cmdline(cmd))

	def dataProvider_testKill(self):
		job0 = createJob(
			path.join(self.testdir, 'pTestKill'),
			config = {
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'runnerOpts': {'slurmRunner': {
					'preScript' : '',
					'postScript': '',
					'sbatch': path.join(__here__, 'mocks', 'sbatch'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', 'squeue'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}},
				'_script': 'sleep 3'
			}
		)
		yield job0, 

		job1 = createJob(
			path.join(self.testdir, 'pTestKill'),
			config = {
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'runnerOpts': {'slurmRunner': {
					'preScript' : '',
					'postScript': '',
					'sbatch': path.join(__here__, 'mocks', 'sbatch'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', '_notexist_'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}},
				'_script': 'sleep 3'
			}
		)
		yield job1, False
	
	def testKill(self, job, beforekill = True):
		RunnerSlurm.INTERVAL = .1
		r = RunnerSlurm(job)
		self.assertFalse(r.isRunning())
		r.submit()
		self.assertEqual(r.isRunning(), beforekill)
		r.kill()
		self.assertFalse(r.isRunning())


if __name__ == '__main__':
	clearMockQueue()
	testly.main(verbosity=2, failfast = True)
