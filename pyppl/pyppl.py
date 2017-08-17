import copy
import json
import logging
import os
import random
import sys
from subprocess import Popen
from time import time

from .helpers import aggr, proc, utils, logger

VERSION = "0.8.1"
			
class pyppl (object):
	"""
	The pyppl class
	
	@static variables:
		`tips`: The tips for users
	"""
	
	tips = [
		"You can find the stdout in <workdir>/<job.index>/job.stdout",
		"You can find the stderr in <workdir>/<job.index>/job.stderr",
		"You can find the script in <workdir>/<job.index>/job.script",
		"Check documentation at: https://www.gitbook.com/book/pwwang/pyppl",
		"You cannot have two processes with same id(variable name) and tag",
		"beforeCmd and afterCmd only run locally",
		"If 'workdir' is not set for a process, it will be PyPPL.<proc-id>.<proc-tag>.<uuid> under default <ppldir>",
		"The default <ppldir> will be './workdir'",
	]
	
	def __init__(self, config = None, cfile = None):
		"""
		Constructor
		@params:
			`config`: the configurations for the pipeline, default: {}
			`cfile`:  the configuration file for the pipeline, default: `~/.pyppl.json`
		"""
		dcfile1  = os.path.join (os.path.expanduser('~'), ".pyppl.json")
		dcfile2  = os.path.join (os.path.expanduser('~'), ".pyppl")

		if cfile is None:
			cfile = dcfile1 if os.path.exists(dcfile1) else dcfile2

		if config is None:
			config = {}

		if os.path.exists(cfile):
			with open(cfile) as f:
				hconfig  = json.load(f)
			#hconfig.update(config)
			utils.dictUpdate(hconfig, config)			
			config   = copy.copy(hconfig)

		loglevels = 'normal'
		if 'loglevels' in config:
			loglevels = config['loglevels']
			del config['loglevels']
			
		logtheme = True
		if 'logtheme' in config:
			logtheme = config['logtheme']
			del config['logtheme']
		
		loglvldiff = []
		if 'loglvldiff' in config:
			loglvldiff = config['loglvldiff']
			del config['loglvldiff']
			
		logfile = os.path.splitext(sys.argv[0])[0] + ".pyppl.log"
		if 'logfile' in config:
			if config['logfile'] is not True:
				logfile = config['logfile']
			del config['logfile']
			
		logger.getLogger (loglevels, logtheme, logfile, loglvldiff)
		logger.logger.info ('[  PYPPL] Version: %s' % (VERSION))
		logger.logger.info ('[   TIPS] %s' % (random.choice(pyppl.tips)))
		if os.path.exists (cfile):
			logger.logger.info ('[ CONFIG] Read from %s' % cfile)
			
		self.config = config
		self.heads  = []
		
	@staticmethod
	def _any2procs (arg):
		"""
		Get procs from anything (aggr.starts, proc, procs, proc names)
		@params:
			`arg`: anything
		@returns:
			A set of procs
		"""
		procs = [a for a in arg if not isinstance(a, list)]
		for a in arg:
			if isinstance(a, list): 
				procs += a
		
		ret = []
		for pany in set(procs):
			if isinstance(pany, proc):
				if not pany in ret:
					ret.append(pany)
			elif isinstance(pany, aggr):
				for p in pany.starts:
					if not p in ret:
						ret.append(p)
			else:
				found = False
				for p in proc.PROCS:
					if p in ret:
						found = True
						continue
					if p.id == pany:
						found = True
						ret.append(p)
					elif p.id + '.' + p.tag == pany:
						found = True
						ret.append(p)
				if not found:
					raise Exception('Cannot find any process associates with "%s"' % str(pany))
		return ret
			

	def starts (self, *arg):
		"""
		Set the starting processes of the pipeline
		@params:
			`args`: the starting processes
		@returns:
			The pipeline object itself.
		"""
		self.heads = pyppl._any2procs(arg)
		return self
	
	def start (self, *arg):
		"""
		Alias of starts
		"""
		self.starts(*arg)
		return self
	
	def _alldepends (self, p):
		"""
		Find all dependents of a process
		Must call after start being called
		@params 
			`p`: The process
		@returns:
			A set of processes that this process depends on
		"""
		ret = []
		if p in self.heads: 
			return ret
		for dp in p.depends:
			ret.append(dp)
			ret += self._alldepends(dp)
		return list(set(ret))
		
	def resume (self, *arg):
		"""
		Mark processes as to be resumed
		@params:
			`args`: the processes to be marked
		@returns:
			The pipeline object itself.
		"""
		resuming_procs = pyppl._any2procs(arg)
		ps2skip = []
		for rp in resuming_procs:
			rp.props['resume'] = True
			ps2skip += self._alldepends(rp)
		ps2skip = set(ps2skip)
		
		ovlap  = list(ps2skip & set(resuming_procs))
		if ovlap:
			logger.logger.info ('[WARNING] processes marked for resuming will be skipped, as a resuming process depends on them.')
			logger.logger.info ('[WARNING] They are: %s' % [ol._name() for ol in ovlap])
		del ovlap
		
		for p2s in ps2skip:
			p2s.props['resume'] = 'skip'			

		return self
		
	
	def run (self, profile = 'local'):
		"""
		Run the pipeline
		@params:
			`profile`: the profile used to run, if not found, it'll be used as runner name. default: 'local'
		@returns:
			The pipeline object itself.
		"""
		timer = time()
		config = {}
		if 'proc' in self.config:
			utils.dictUpdate(config, self.config['proc'])
		
		if profile in self.config:
			utils.dictUpdate(config, self.config[profile])
		
		if not 'runner' in config:
			if profile in proc.RUNNERS:
				config['runner'] = profile
			else:
				config['runner'] = 'local'
		
		next2run = self.heads
		finished = []
		
		while next2run:
			next2run2 = []
			for p in sorted(next2run, key = lambda x: x._name()):
				p.run (config)
				finished.append (p)
				next2run2 += p.props['nexts']
			# next procs to run must be not finished and all their depends are finished
			next2run = [n for n in set(next2run2) if n not in finished and all(x in finished for x in n.depends)]
			
		logger.logger.info ('[   DONE] Total time: %s' % utils.formatTime (time()-timer))
		return self
		
	
	def _node (self, p):
		"""
		Give dot expression of a node of a process
		"""
		# default attributes
		attrs = {
			'shape':     'box',
			'style':     'rounded,filled',
			'fillcolor': '#ffffff',
			'color':     '#000000',
			'fontcolor': '#000000',
		}
		if p in self.heads:
			attrs['style']         = 'filled'
			attrs['color']         = '#259229'
		elif not p.nexts:
			attrs['style']         = 'filled'
			attrs['color']         = '#d63125'
		if p.exdir:
			attrs['fontcolor']     = '#c71be4'
		if p.resume == 'skip':
			attrs['fillcolor']     = '#eaeaea'
		elif p.resume == True:
			attrs['fillcolor']     = '#b9ffcd'
		
		return '"%s" [%s]' % (p._name(), ' '.join(['%s="%s"' % (k,v) for k,v in attrs.items()]))
	
	def flowchart (self, dotfile = None, fcfile = None, dot = "dot -Tsvg {{dotfile}} > {{fcfile}}"):
		"""
		Generate graph in dot language and visualize it.
		@params:
			`dotfile`: Where to same the dot graph. Default: `None` (`os.path.splitext(sys.argv[0])[0] + ".pyppl.dot"`)
			`fcfile`:  The flowchart file. Default: `None` (`os.path.splitext(sys.argv[0])[0] + ".pyppl.svg"`)
			- For example: run `python pipeline.py` will save it to `pipeline.pyppl.svg`
			`dot`:     The dot visulizer. Default: "dot -Tsvg {{dotfile}} > {{fcfile}}"
		@returns:
			The pipeline object itself.
		"""
		ret  = 'digraph PyPPL {\n'
			
		next2run = self.heads 
		finished = []
		while next2run:
			next2run2 = []
			for p in next2run:
				if p not in finished:
					finished.append (p)
				ret += '	"%s" -> {%s}\n' % (p._name(), ' '.join(['"%s"' % n._name() for n in p.nexts]))
				next2run2 = set(next2run2) | set(p.nexts)
			next2run = [n for n in next2run2 if n not in finished and all(x in finished for x in n.depends)]
		
		for node in finished:
			ret += '	%s\n' % (self._node(node))
		ret += '}\n'
		
		if dotfile is None: dotfile = os.path.splitext(sys.argv[0])[0] + ".pyppl.dot"
		if fcfile  is None: fcfile  = os.path.splitext(sys.argv[0])[0] + ".pyppl.svg"
		
		with open (dotfile, "w") as f:
			f.write (ret)
			
		logger.logger.info ('[   INFO] DOT file saved to: %s' % dotfile)
		try:
			dotcmd = utils.format (dot, {"dotfile": dotfile, "fcfile":fcfile})
			Popen (dotcmd, shell=True).wait()
			logger.logger.info ('[   INFO] Flowchart file saved to: %s' % fcfile)
		except Exception as ex:
			logger.logger.info ('[  ERROR] %s' % ex)
			logger.logger.info ('[   INFO] Skipped to generate flowchart to: %s' % fcfile)
		return self
