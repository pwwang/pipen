import copy
import json
import logging
import os
import random
import sys
from subprocess import Popen
from time import time

from helpers import *
from runners import *

VERSION = "0.7.0"
			
class pyppl (object):
	"""
	The pyppl class
	
	@static variables:
		`tips`: The tips for users
	"""
	
	tips = [
		"You can find the stdout in <workdir>/scripts/script.<index>.stdout",
		"You can find the stderr in <workdir>/scripts/script.<index>.stderr",
		"You can find the script in <workdir>/scripts/script.<index>",
		"Check documentation at: https://www.gitbook.com/book/pwwang/pyppl",
		"You cannot have two processes with same id(variable name) and tag",
		"beforeCmd and afterCmd only run locally",
		"If 'workdir' is not set for a process, it will be PyPPL.<proc-id>.<proc-tag>.<uuid> under default <ppldir>",
		"The default <ppldir> will be './workdir'",
	]
	
	def __init__(self, config = {}, cfile = None):
		"""
		Constructor
		@params:
			`config`: the configurations for the pipeline, default: {}
			`cfile`:  the configuration file for the pipeline, default: `~/.pyppl`
		"""
		cfile    = os.path.join (os.path.expanduser('~'), ".pyppl") if cfile is None else cfile
		if os.path.exists(cfile):			
			hconfig  = json.load(open(cfile))
			#hconfig.update(config)
			utils.dictUpdate(hconfig, config)			
			config   = copy.copy(hconfig)

		loglevel = 'info'
		if config.has_key('loglevel'):
			loglevel = config['loglevel']
			del config['loglevel']
			
		logcolor = True
		if config.has_key('logcolor'):
			logcolor = config['logcolor']
			del config['logcolor']
			
		suffix  = utils.randstr ()
		self.logger = utils.getLogger (loglevel, self.__class__.__name__ + suffix, logcolor)
		self.logger.info ('[  PyPPL] Version: %s' % (VERSION))
		self.logger.info ('[   TIPS] %s' % (random.choice(pyppl.tips)))
		if os.path.exists (cfile):
			self.logger.info ('[ CONFIG] Read from %s' % cfile)
			
		self.config = config
		self.heads  = []

	def starts (self, *arg):
		"""
		Set the starting processes of the pipeline
		@params:
			`args`: the starting processes
		@returns:
			The pipeline object itself.
		"""
		for pa in arg:
			if isinstance(pa, proc):
				if pa in self.heads:
					raise ValueError('Proc %s already added.', pa._name(False))
				self.heads.append(pa)
			elif isinstance(pa, aggr):
				for p in pa.starts:
					if p in self.heads:
						raise ValueError('Proc %s already added.', p._name(False))
					self.heads.append(p)
			else:
				raise ValueError('An "proc" or "aggr" instance required.')
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
		if self.config.has_key('proc'):
			utils.dictUpdate(config, self.config['proc'])
		
		if self.config.has_key(profile):
			utils.dictUpdate(config, self.config[profile])
		
		if not config.has_key('runner'):
			if proc.RUNNERS.has_key (profile):
				config['runner'] = profile
			else:
				config['runner'] = 'local'

		next2run = self.heads
		finished = []
		
		while next2run:
			next2run2 = []
			for p in next2run:
				p.props['logger'] = self.logger
				p.run (config)
				finished.append (p)
				next2run2 += p.props['nexts']
			next2run = [n for n in list(set(next2run2)) if n not in finished and all(x in finished for x in n.props['depends'])]
		self.logger.info ('[   DONE] Total time: %s' % utils.formatTime (time()-timer))
		return self

	
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
		ret  = "digraph PyPPL {\n"
		next2run = self.heads 
		finished = []
		shapes = {}
		for p in next2run:
			shapes[p._name()] = '[shape=box, style=filled, color="#c9fcb3" %s]' % ("fontcolor=red" if p.exportdir else "")
		while next2run:
			next2run2 = []
			for p in next2run:
				finished.append (p)
				if p.exportdir and not shapes.has_key(p._name()):
					shapes[p._name()] = '[shape=box, style=filled, color="#f0f998", fontcolor=red]'
				for n in p.props['nexts']:
					ret += '	"%s" -> "%s"\n' % (p._name(), n._name())
					if not n.props['nexts']:
						shapes[n._name()] = '[shape=box, style=filled, color="#fcc9b3" %s]' % ("fontcolor=red" if n.exportdir else "")
				next2run2 += p.props['nexts']
			next2run = [n for n in list(set(next2run2)) if n not in finished and all(x in finished for x in n.props['depends'])]
		for node, shape in shapes.iteritems():
			ret += '	"%s" %s\n' % (node, shape)
		ret += '}\n'
		if dotfile is None: dotfile = os.path.splitext(sys.argv[0])[0] + ".pyppl.dot"
		if fcfile  is None: fcfile  = os.path.splitext(sys.argv[0])[0] + ".pyppl.svg"
		open (dotfile, "w").write (ret)
		self.logger.info ('[   INFO] DOT file saved to: %s' % dotfile)
		try:
			dotcmd = utils.format (dot, {"dotfile": dotfile, "fcfile":fcfile})
			Popen (dotcmd, shell=True).wait()
			self.logger.info ('[   INFO] Flowchart file saved to: %s' % fcfile)
		except Exception as ex:
			self.logger.error ('[  ERROR] %s' % ex)
			self.logger.error ('[  ERROR] Skipped to generate flowchart to: %s' % fcfile)
		return self
