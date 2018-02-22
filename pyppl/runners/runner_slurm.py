import copy
from subprocess import check_output
from .runner import Runner

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
		slurmfile = self.job.script + '.slurm'
		
		slurmsrc  = ['#!/usr/bin/env bash']
	
		conf = {}
		if 'slurmRunner' in self.job.proc.props or 'slurmRunner' in self.job.proc.config:
			conf = copy.copy (self.job.proc.slurmRunner)

		self.commands = {'sbatch': 'sbatch', 'srun': 'srun', 'squeue': 'squeue'}
		if 'sbatch' in conf:
			self.commands['sbatch'] = conf['sbatch']
		if 'srun' in conf:
			self.commands['srun']   = conf['srun']
		if 'squeue' in conf:
			self.commands['squeue'] = conf['squeue']
		
		cmdPrefix = self.commands['srun']
		if 'cmdPrefix' in conf:
			cmdPrefix = conf['cmdPrefix']
		
		if not 'slurm.J' in conf:
			jobname = '.'.join([
				self.job.proc.id,
				self.job.proc.tag,
				self.job.proc._suffix(),
				str(self.job.index)
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
		
		with open (slurmfile, 'w') as f:
			f.write ('\n'.join(slurmsrc) + '\n')
		
		self.script = [self.commands['sbatch'], slurmfile]

	def getpid (self):
		"""
		Get the job identity and save it to job.pidfile
		"""
		# sbatch: Submitted batch job 99999999
		content = ''
		with open(self.job.outfile) as f:
			content = f.read().strip()
		if not 'Submitted batch job' in content:
			return
		pid = int (content.split(' ')[-1])
		self.job.pid (pid)

	def isRunning (self):
		"""
		Tell whether the job is still running
		@returns:
			True if it is running else False
		"""
		jobid = self.job.pid ()
		if not jobid: return False
		try:
			# header line
			# jid xxx xxx
			jid = str(check_output([self.commands['squeue'], '-j', jobid]).splitlines()[1].split()[0].decode())
			return jobid == jid
		except Exception:
			return False

