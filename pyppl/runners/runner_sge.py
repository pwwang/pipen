from runner_local import runner_local
from time import sleep
from subprocess import Popen, list2cmdline 
import os, shlex, logging, sys, copy


class runner_sge (runner_local):

	def __init__ (self, script, config = {}):
		super(runner_sge, self).__init__(script, config)
		# construct an sge script
		sgefile = os.path.realpath(script + '.sge')
		
		sgesrc  = [
			'#!/usr/bin/env bash',
			#'',
			#'#$ -o ' + self.outfile,
			#'#$ -e ' + self.errfile,
			#'#$ -cwd'
		]
		
		conf = copy.copy (self._config ('sgeRunner', {}))
		if not conf.has_key ('sge_N'):
			sgesrc.append('#$ -N %s_%s.%s' % (self._config('id', os.path.basename (script) [:-len(self.index)-1]), self._config('tag', 'notag'), self.index)) # + self._config('id', os.path.basename (script)) + '.' + self._config('tag', 'notag'))
		else:
			sgesrc.append('#$ -N %s' % conf['sge_N'])
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
			sgesrc.append('#$ -o %s' % self.outfile)
			
		if conf.has_key('sge_e'):
			sgesrc.append('#$ -e %s' % conf['sge_e'])
			del conf['sge_e']
		else:
			sgesrc.append('#$ -e %s' % self.errfile)
			
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
		sgesrc.append ('trap "status=\$?; echo \$status > %s; exit \$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % self.rcfile)
		sgesrc.append (self._config('sgeRunner.preScript', ''))
		sgesrc.append ('')
		sgesrc.append (list2cmdline(self.script))
		sgesrc.append (self._config('sgeRunner.postScript', ''))
		
		with open (sgefile, 'w') as f:
			f.write ('\n'.join(sgesrc) + '\n')
		
		self.script = ['qsub', sgefile]
		
	def submit (self):
		if os.path.exists(self.rcfile):
			os.remove(self.rcfile)
		try:
			self.p = Popen (self.script)
			rc = self.p.wait()
			if rc != 0:
				open (self.errfile, 'w').write('Failed to submit job: %s.%s#%s' % (self._config('id'), self._config('tag'), self.index))
				open (self.rcfile, 'w').write('-1')
				
		except Exception as ex:
			open (self.errfile, 'w').write(str(ex))
			open (self.rcfile, 'w').write('-1') # not able to submit
			# don't retry if failed to submit
		sleep (0.1)
		
	def wait(self):
		if self.rc() == -1: return
		while self.p is None: sleep (1)
		
		while self.rc() == -99:
			if self._config('echo', False):
				self.flushFile('stdout')
				self.flushFile('stderr')
			sleep (5)
			
		self.p = None
		self.retry ()
		
