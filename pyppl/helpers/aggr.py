"""
The aggregation of procs
"""
from .channel import channel
from . import utils

class aggr (object):
	"""
	The aggregation of a set of processes

	@static variables:
		`commprops`: The common properties. If you set these properties to an aggregation, all the processes in this aggregation will have it.
	@magic methods:
		`__setattr__(self, name, value)`: Set property value of an aggregation.
		- if it's a common property, set it to all processes
		- if it is `input` set it to starting processes
		- if it is `depends` set it to the end processes
		- if it is related to `export` (startswith `ex`), set it to the end processes
		- if it is in ['starts', 'ends', 'id'], set it to the aggregation itself.
		- Otherwise a `ValueError` raised.
		- You can use `[aggr].[proc].[prop]` to set/get the properties of a processes in the aggregation.

	"""
	
	commprops = ['tag', 'tmpdir', 'forks', 'cache', 'retcodes', 'rc', 'echo', 'runner', 'errorhow', 'errhow', 'errorntry', 'errntry']
	
	# aggr (p1, p2, p3, ..., depends = True)
	def __init__ (self, *arg):
		"""
		Constructor
		@params:
			`arg`: the set of processes
		"""
		self.starts    = []
		self.ends      = []
		self.id = utils.varname(self.__class__.__name__, 50)
		
		depends = True
		arg     = list(arg)
		if isinstance(arg[-1], bool):
			depends = arg.pop(-1)
		
		self.__dict__['procs'] = arg
		for i, proc in enumerate(self.procs):
			if proc.tag == 'notag':
				self.__dict__[proc.id] = proc
			self.__dict__[proc.id + '_' + proc.tag] = proc
			proc.aggr  = self.id
			if depends and i>0:
				proc.depends = self.procs[i-1]
			if i==0: 
				self.starts.append (proc)
			if i==len(self.procs)-1: 
				self.ends.append(proc)
		
	def __setattr__ (self, name, value):
		if name in aggr.commprops or name.endswith('Runner'):
			for proc in self.procs:
				proc.__setattr__(name, value)
		elif name == 'input':
			if not isinstance(value, channel):
				value  = channel.create(value)
			
			start = 0
			for proc in self.starts: # only str and list allowed: "input1, input2" or ["input1", "input2"]
				inkey = proc.config['input']
				if isinstance(inkey, list):
					inkey = ','.join (inkey)
				if not isinstance (inkey, basestring):
					raise RuntimeError('Expect list or str for proc keys for aggregation: %s, you may have already set the input channels?' % (self.id))
				l = len (utils.split(inkey, ','))

				proc.input = {inkey: value.slice(start, l)}
				start += l
					
		elif name == 'depends':
			for proc in self.starts:
				proc.depends = value
		elif name.startswith ('ex'): # export
			for proc in self.ends:
				proc.__setattr__(name, value)
		elif name in ['starts', 'ends', 'id']:
			self.__dict__[name] = value
		else:
			raise AttributeError('Cannot set property "%s" of aggregation "%s"' % (name, self.id))
		
	def addProc (self, p, where = None):
		"""
		Add a process to the aggregation.
		Note that you have to adjust the dependencies after you add processes.
		@params:
			`p`:     The process
			`where`: Add to where: 'starts', 'ends', 'both' or None (default)
		@returns:
			the aggregation itself
		"""
		p.aggr  = self.id
		self.procs.append (p)
		if where == 'starts' or where == 'both':
			self.starts.append (p)
		if where == 'ends' or where == 'both':
			self.ends.append (p)
		tag = "_%s" % p.tag if p.tag != "notag" else ""
		self.__dict__ [p.id + tag] = p
		return self
		
	def copy (self, tag='aggr', copyDeps=True, newid=None):
		"""
		Like `proc`'s `copy` function, copy an aggregation. Each processes will be copied.
		@params:
			`tag`:      The new tag of all copied processes
			`copyDeps`: Whether to copy the dependencies or not. Default: True
			- dependences for processes in starts will not be copied
			`newid`:    Use a different id if you don't want to use the variant name
		@returns:
			The new aggregation
		"""
		name     = utils.varname(r'\w+\.'+self.copy.__name__, 2) if newid is None else newid
		tagstr   = '_' + tag if tag != 'notag' else ''
		args     = []
		depends  = {}
		newprocs = {}
		copy2    = {}
		starts   = []
		ends     = []
		for proc in self.procs:
			if tag == proc.tag:
				raise ValueError('Tag "%s" is used by proc "%s" before, cannot copy with the same tag for aggregation: %s.' % (tag, proc.id, self.id))
			newproc = proc.copy (tag, proc.id)
			args.append (newproc)
			key = newproc._name(False)
			depends[key]  = proc.depends
			newprocs[key] = newproc
			copy2[proc._name(False)] = key
			if proc in self.starts: starts.append (newproc)
			if proc in self.ends:   ends.append (newproc)
		
		if copyDeps:	
			for proc in args:
				if proc in starts: continue
				newdeps = []
				for dep in depends[proc._name(False)]:
					dn = dep._name(False)
					if not copy2.has_key(dn): newdeps.append (dep)
					else: newdeps.append (newprocs[copy2[dn]])
				proc.depends = newdeps

		args.append (False)
		ret        = aggr (*args)
		ret.starts = starts
		ret.ends   = ends
		ret.id     = name
		for p in ret.procs: p.aggr = name
		return ret
		
	

		