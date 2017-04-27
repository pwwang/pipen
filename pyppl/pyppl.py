import logging, os, sys, random, json, copy
from helpers import *
from runners import *
from time import time
VERSION = "0.6.1"
			
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
		"If 'workdir' is not set for a process, it will be PyPPL.<proc-id>.<proc-tag>.<uuid> under default <tmpdir>",
		"The default <tmpdir> will be './workdir'",
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
		suffix  = utils.randstr ()
		self.logger = utils.getLogger (loglevel, self.__class__.__name__ + suffix)
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
					raise ValueError('Proc %s already added.', pa.id)
				self.heads.append(pa)
			elif isinstance(pa, aggr):
				for p in pa.procs:
					if p in self.heads:
						raise ValueError('Proc %s already added.', p.id)
					self.heads.append(p)
			else:
				raise ValueError('An "proc" or "aggr" instance required.')
		return self
	
	def run (self, profile = 'local'):
		"""
		Run the pipeline
		@params:
			`profile`: the profile used to run, if not found, it'll be used as runner name. default: 'local'
		"""
		timer = time()
		config = {}
		if self.config.has_key('proc'):
			utils.dictUpdate(config, self.config['proc'])
		
		if self.config.has_key(profile):
			utils.dictUpdate(config, self.config[profile])
		
		if not config.has_key('runner'):
			if proc.runners.has_key (profile):
				config['runner'] = profile
			else:
				config['runner'] = 'local'

		next2run = self.heads
		finished = []
		
		while next2run:
			next2run2 = []
			for p in next2run:
				p.setLogger(self.logger)
				p.run (config)
				finished.append (p)
				next2run2 += p.props['nexts']
			next2run = [n for n in list(set(next2run2)) if n not in finished and all(x in finished for x in n.props['depends'])]
		self.logger.info ('[   DONE] Total time: %s' % utils.formatTime (time()-timer))
		

	
	def dot (self):
		"""
		Generate graph in dot language
		@returns:
			The dot graph string.
		"""
		ret  = "digraph PyPPL {\n"
		next2run = self.heads 
		finished = []
		shapes = {}
		for p in next2run:
			shapes["%s.%s" % (p.id, p.tag)] = '[shape=box, style=filled, color="#c9fcb3"]'
		while next2run:
			next2run2 = []
			for p in next2run:
				finished.append (p)
				if p.exportdir and not shapes.has_key(p.id+'.'+p.tag):
					shapes["%s.%s" % (p.id, p.tag)] = '[shape=box, style=filled, color="#f0f998", fontcolor=red]'
				for n in p.props['nexts']:
					ret += '	"%s.%s" -> "%s.%s"\n' % (p.id, p.tag, n.id, n.tag)
					if not n.props['nexts']:
						shapes["%s.%s" % (n.id, n.tag)] = '[shape=box, style=filled, color="#fcc9b3" %s]' % ("fontcolor=red" if n.exportdir else "")
				next2run2 += p.props['nexts']
			next2run = [n for n in list(set(next2run2)) if n not in finished and all(x in finished for x in n.props['depends'])]
		for node, shape in shapes.iteritems():
			ret += '	"%s" %s\n' % (node, shape)
		ret += '}\n'
		return ret




