"""
The aggregation of procs
"""
from .channel import Channel
from . import utils

class Aggr (object):
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
		self.starts                     = []
		self.ends                       = []
		self.id                         = utils.varname(self.__class__.__name__, 100)
		
		depends                         = True
		arg                             = list(arg)
		if len(arg) > 0 and isinstance(arg[-1], bool):
			depends                     = arg.pop(-1)
		
		self.procs                      = []
		for proc in arg:
			pid                = proc.id
			newproc            = proc.copy(utils.uid(self.id, 4), pid)
			newproc.aggr       = self.id
			self.__dict__[pid] = newproc
			self.procs.append (newproc)
		
		if depends:
			self.starts = [self.procs[0]] if len(self.procs) > 0 else []
			self.ends   = [self.procs[-1]] if len(self.procs) > 0 else []
			for i, proc in enumerate(self.procs):
				if i == 0: 
					continue
				proc.depends = self.procs[i-1]
				
	def set (self, propname, propval, procs = None):
		"""
		Set property for procs
		@params:
			propname: The property name
			propval:  The property value
			procs:    The ids of the procs to set
		"""
		if procs is None:
			procs = [p.id for p in self.procs]
		else:
			procs = utils.alwaysList (procs)
		for proc in [self.__dict__[pid] for pid in procs]:
			proc.__setattr__ (propname, propval)
			
	def updateArgs (self, arg, procs = None):
		"""
		update args for procs
		@params:
			arg:   the arg to update
			procs: The ids of the procs to update
		"""
		if procs is None:
			procs = [p.id for p in self.procs]
		else:
			procs = utils.alwaysList (procs)
		for proc in [self.__dict__[pid] for pid in procs]:
			utils.dictUpdate (proc.args, arg)
		
	def __setattr__ (self, name, value):
		if name in aggr.commprops or name.endswith('Runner'):
			self.set (name, value)
		elif name == 'input':
			if not isinstance(value, channel):
				value  = channel.create(value)
			
			start = 0
			for proc in self.starts: # only str and list allowed: "input1, input2" or ["input1", "input2"]
				inkey = proc.config['input']
				if isinstance(inkey, list):
					inkey = ','.join (inkey)
				if not isinstance (inkey, utils.basestring):
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
		elif name in ['starts', 'ends', 'id', 'procs']:
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
		newproc = p.copy(utils.uid(self.id, 4), p.id)
		newproc.aggr = self.id
		self.procs.append (newproc)
		if where == 'starts' or where == 'both':
			self.starts.append (newproc)
		if where == 'ends' or where == 'both':
			self.ends.append (newproc)
		self.__dict__[p.id] = newproc
		return self
		
	def copy (self, tag='notag', copyDeps=True, newid=None):
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
		tagstr   = utils.uid(name, 4) if not tag or tag == 'notag' else tag
		ret      = aggr ()
		ret.id   = name
		
		for proc in self.procs:
			if tag == proc.tag:
				raise ValueError('Tag "%s" is used by proc "%s" before, cannot copy with the same tag for aggregation: %s.' % (tag, proc.id, self.id))
			
			if proc not in self.starts and copyDeps:
				for d in proc.depends:
					if d not in self.procs:
						raise ValueError('Failed to copy "%s": a non-start proc ("%s") depends on a proc("%s") does not belong to "%s"' % (self.id, proc._name(), d._name(), self.id))					
			
			newproc      = proc.copy (tag, proc.id)
			newproc.aggr = name
			ret.addProc (newproc)
			if proc in self.starts:
				ret.starts.append (newproc)
			if proc in self.ends:
				ret.ends.append (newproc)
		
		ret.set ('tag', tagstr)
		# copy dependences
		for proc in self.procs:
			if proc in self.starts:
				continue
			
			ret.__dict__[proc.id].depends = [ret.__dict__[d.id] for d in proc.depends]

		return ret
		
	

		