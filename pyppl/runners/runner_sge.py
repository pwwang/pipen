import copy

from .runner import Runner
from .helpers import SgeHelper

class RunnerSge (Runner):
	"""
	The sge runner
	"""
	
	INTERVAL = 5

	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
			`config`: The properties of the process
		"""
		super(RunnerSge, self).__init__(job)

		# construct an sge script
		sgefile = self.job.script + '.sge'
		sgesrc  = ['#!/usr/bin/env bash']

		conf = {}
		if 'sgeRunner' in self.job.proc.props or 'sgeRunner' in self.job.proc.config:
			conf = copy.copy (self.job.proc.sgeRunner)
		
		commands = {'qsub': 'qsub', 'qstat': 'qstat', 'qdel': 'qdel'}
		if 'qsub' in conf:
			commands['qsub'] = conf['qsub']
		if 'qstat' in conf:
			commands['qstat'] = conf['qstat']
		if 'qdel' in conf:
			commands['qdel'] = conf['qdel']
			
		if not 'sge.N' in conf:
			jobname = '.'.join([
				self.job.proc.id,
				self.job.proc.tag,
				self.job.proc._suffix(),
				str(self.job.index + 1)
			])
			sgesrc.append('#$ -N %s' % jobname)
		else:
			jobname = conf['sge.N']
			sgesrc.append('#$ -N %s' % jobname)
			del conf['sge.N']
		
		if 'sge.q' in conf:
			sgesrc.append('#$ -q %s' % conf['sge.q'])
			del conf['sge.q']
			
		if 'sge.j' in conf:
			sgesrc.append('#$ -j %s' % conf['sge.j'])
			del conf['sge.j']
		
		if 'sge.o' in conf:
			sgesrc.append('#$ -o %s' % conf['sge.o'])
			del conf['sge.o']
		else:
			sgesrc.append('#$ -o %s' % self.job.outfile)
			
		if 'sge.e' in conf:
			sgesrc.append('#$ -e %s' % conf['sge.e'])
			del conf['sge.e']
		else:
			sgesrc.append('#$ -e %s' % self.job.errfile)
			
		sgesrc.append('#$ -cwd')
		
		if 'sge.M' in conf:
			sgesrc.append('#$ -M %s' % conf['sge.M'])
			del conf['sge.M']
		
		if 'sge.m' in conf:
			sgesrc.append('#$ -m %s' % conf['sge.m'])
			del conf['sge.m']
		
		for k in sorted(conf.keys()):
			if not k.startswith ('sge.'): continue
			v = conf[k]
			k = k[4:].strip()
			src = '#$ -' + k
			if v != True: # {'notify': True} ==> -notify
				src += ' ' + str(v)
			sgesrc.append(src)

		sgesrc.append ('')
		sgesrc.append ('trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.job.rcfile)
		
		if 'preScript' in conf:
			sgesrc.append (conf['preScript'])

		sgesrc.append ('')
		sgesrc.append (self.cmd2run)

		if 'postScript' in conf:
			sgesrc.append (conf['postScript'])
		
		with open (sgefile, 'w') as f:
			f.write ('\n'.join(sgesrc) + '\n')
		
		self.helper = SgeHelper(sgefile, commands)


