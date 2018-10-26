"""
Slurm runner for PyPPL
"""
import re
import copy
from subprocess import CalledProcessError
from .runner import Runner
from ..utils import cmd, box

class RunnerSlurm (Runner):
	"""
	The slurm runner
	"""
	
	INTERVAL = 5
	
	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
			`config`: The properties of the process
		"""
		super(RunnerSlurm, self).__init__(job)

		# construct an slurm script
		self.script = self.job.script + '.slurm'
		slurmsrc    = ['#!/usr/bin/env bash']
	
		conf = self.job.config.get('runnerOpts', {})
		conf = copy.copy(conf.get('slurmRunner', {}))

		self.commands = {'sbatch': 'sbatch', 'srun': 'srun', 'squeue': 'squeue', 'scancel': 'scancel'}
		if 'sbatch' in conf:
			self.commands['sbatch']  = conf['sbatch']
		if 'srun' in conf:
			self.commands['srun']    = conf['srun']
		if 'squeue' in conf:
			self.commands['squeue']  = conf['squeue']
		if 'scancel' in conf:
			self.commands['scancel'] = conf['scancel']
		
		cmdPrefix = self.commands['srun']
		if 'cmdPrefix' in conf:
			cmdPrefix = conf['cmdPrefix']
		
		if not 'slurm.J' in conf:
			jobname = '.'.join([
				self.job.config['proc'],
				self.job.config['tag'],
				self.job.config['suffix'],
				str(self.job.index + 1)
			])
			slurmsrc.append('#SBATCH -J %s' % jobname)
		else:
			jobname = conf['slurm.J']
			slurmsrc.append('#SBATCH -J %s' % jobname)
			del conf['slurm.J']
		
		if 'slurm.o' in conf:
			slurmsrc.append('#SBATCH -o %s' % conf['slurm.o'])
			del conf['slurm.o']
		else:
			slurmsrc.append('#SBATCH -o %s' % self.job.outfile)
			
		if 'slurm.e' in conf:
			slurmsrc.append('#SBATCH -e %s' % conf['slurm.e'])
			del conf['slurm.e']
		else:
			slurmsrc.append('#SBATCH -e %s' % self.job.errfile)
		
		for k in sorted(conf.keys()):
			if not k.startswith ('slurm.'): continue
			v = conf[k]
			k = k[6:].strip()
			src = '#SBATCH -' + (k if len(k)==1 else '-' + k)
			if v != True: # {'notify': True} ==> -notify
				src += ' ' + str(v)
			slurmsrc.append(src)

		slurmsrc.append ('')
		slurmsrc.append ('trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.job.rcfile)
		
		if 'preScript' in conf:
			slurmsrc.append (conf['preScript'])

		slurmsrc.append ('')
		slurmsrc.append (cmdPrefix + ' ' + self.cmd2run)

		if 'postScript' in conf:
			slurmsrc.append (conf['postScript'])
		
		with open (self.script, 'w') as f:
			f.write ('\n'.join(slurmsrc) + '\n')
		
	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed 
			else a `Box` object with stderr as the exception and rc as 1
		"""
		cmdlist = [self.commands['sbatch'], self.script]
		try:
			r = cmd.run(cmdlist)
			# Submitted batch job 1823334668
			m = re.search(r'\s(\d+)$', r.stdout.strip())
			if not m:
				r.rc = 1
			else:
				self.job.pid = m.group(1)
			return r

		except (OSError, CalledProcessError) as ex:
			r        = box.Box()
			r.stderr = str(ex)
			r.rc     = 1
			r.cmd    = cmdlist
			return r

	def kill(self):
		"""
		Kill the job
		"""
		cmdlist = [self.commands['scancel'], str(self.job.pid)]
		try:
			cmd.run(cmdlist)
		except (OSError, CalledProcessError): # pragma: no cover
			pass

	def isRunning(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if not self.job.pid:
			return False
		cmdlist = [self.commands['squeue'], '-j', str(self.job.pid)]
		try:
			r = cmd.run(cmdlist)
			return r.rc == 0
		except (OSError, CalledProcessError):
			return False
