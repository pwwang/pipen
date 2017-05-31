from runner_local import runner_local
from time import sleep
from subprocess import Popen, list2cmdline, check_output 
from multiprocessing import cpu_count
import os, shlex, logging, sys, copy
from ..helpers.job import job as pjob


class runner_sge (runner_local):
	"""
	The sge runner

	@static variables:
		`maxsubmit`: how many job to submit at one time. Default: `int (multiprocess.cpu_count()/2)`
		`interval`:  how long should I wait in seconds if maxsubmit reached

	"""
	
	maxsubmit = int (cpu_count()/2)
	interval  = 30 
	
	def __init__ (self, job, config = {}):
		"""
		Constructor
		@params:
			`job`:    The job object
			`config`: The properties of the process
		"""
		super(runner_sge, self).__init__(job, config)
		self.submitRun = False
		# construct an sge script
		sgefile = os.path.realpath(self.job.script + '.sge')
		# get suffix
		suffix  = os.path.basename (os.path.dirname(os.path.dirname(self.job.script))).split('.')[-1]
		sgesrc  = [
			'#!/usr/bin/env bash',
			#'',
			#'#$ -o ' + self.outfile,
			#'#$ -e ' + self.errfile,
			#'#$ -cwd'
		]
		self.jobname = '%s.%s.%s.%s' % (
			self._config('id'),
			self._config('tag'),
			suffix,
			self.job.index
		)
		
		conf = copy.copy (self._config ('sgeRunner', {}))
		if not conf.has_key ('sge_N'):
			sgesrc.append('#$ -N %s' % self.jobname) 
		else:
			self.jobname = conf['sge_N']
			sgesrc.append('#$ -N %s' % self.jobname)
			del conf['sge_N']
		
		if conf.has_key('sge_q'):
			sgesrc.append('#$ -q %s' % conf['sge_q'])
			del conf['sge_q']
			
		if conf.has_key('sge_j'):
			sgesrc.append('#$ -j %s' % conf['sge_j'])
			del conf['sge_j']
		
		if conf.has_key('sge_o'):
			sgesrc.append('#$ -o %s' % conf['sge_o'])
			del conf['sge_o']
		else:
			sgesrc.append('#$ -o %s' % self.job.outfile)
			
		if conf.has_key('sge_e'):
			sgesrc.append('#$ -e %s' % conf['sge_e'])
			del conf['sge_e']
		else:
			sgesrc.append('#$ -e %s' % self.job.errfile)
			
		sgesrc.append('#$ -cwd')
		
		if conf.has_key('sge_M'):
			sgesrc.append('#$ -M %s' % conf['sge_M'])
			del conf['sge_M']
		
		if conf.has_key('sge_m'):
			sgesrc.append('#$ -m %s' % conf['sge_m'])
			del conf['sge_m']
		
		for k in sorted(conf.keys()):
			if not k.startswith ('sge_'): continue
			v = conf[k]
			k = k[4:].strip()
			src = '#$ -' + k
			if v != True: # {'notify': True} ==> -notify
				src += ' ' + str(v)
			sgesrc.append(src)
		sgesrc.append ('')
		sgesrc.append ('trap "status=\$?; echo \$status > %s; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.job.rcfile)
		sgesrc.append (self._config('sgeRunner.preScript', ''))
		sgesrc.append ('')
		sgesrc.append (list2cmdline(self.script))
		sgesrc.append (self._config('sgeRunner.postScript', ''))
		
		open (sgefile, 'w').write ('\n'.join(sgesrc) + '\n')
		
		self.script = ['qsub', sgefile]


	def isRunning (self):
		"""
		Try to tell whether the job is still running using qstat.
		@returns:
			`True` if yes, otherwise `False`
		"""
		# rcfile already generated
		if self.job.rc() != pjob.emptyRc: return False

		qstout = check_output (['qstat', '-xml'])
		#  <JB_name>pMuTect2.nothread.3</JB_name>
		qstout = [line for line in qstout.split("\n") if "<JB_name>" + self.jobname + "</JB_name>" in line]
		return bool (qstout)