"""
The aggregation of procs
"""
from .channel import Channel
from . import utils

class Aggr (object):
	"""
	The aggregation of a set of processes

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

	# aggr (p1, p2, p3, ..., depends = True)
	def __init__ (self, *arg, **kwargs):
		"""
		Constructor
		@params:
			`arg`: the set of processes
		"""
		self.starts = []
		self.ends   = []
		self.id     = utils.varname()
		
		arg     = list(arg)
		depends = True if not 'depends' in kwargs else kwargs['depends']
		
		self.procs = []
		for proc in arg:
			pid                = proc.id
			if hasattr(self, pid):
				raise AttributeError('%s is an attribute of Aggr, use a different process id.' % pid)
			newproc            = proc.copy(tag = utils.uid(self.id, 4), newid = pid)
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
			procs:    The ids of the procs to set. Default: None (all procs)
				- if propname == 'input', it defaults to 'starts'
		"""
		dot2dictargs = lambda name, val: val if '.' not in name else {name.split('.')[-1]: val}

		if propname == 'input' and procs is None:
			procs = 'starts'
		if procs is None:
			procs = [p.id for p in self.procs]
		elif procs == 'starts':
			procs = [p.id for p in self.starts]
		elif procs == 'ends':
			procs = [p.id for p in self.ends]
		else:
			procs = utils.alwaysList (procs)
		
		procs = [self.__dict__[pid] for pid in procs]
		if propname == 'input':
			# callback for each process
			if all([callable(pv) for pv in propval]):
				for i, proc in enumerate(procs):
					proc.input = propval[i]
			else:
				if not isinstance(propval, Channel):
					propval = Channel.create(propval)

				idx = 0
				for proc in procs:
					procinput = proc.config['input']
					# Issue: cannot assure the order of keys, unless procinput is an OrderedDict
					if isinstance(procinput, dict):
						raise TypeError('Expect orginal input as string or list rather than dict. Please specify input for each process separately.')
					inkeys     = utils.alwaysList(procinput)
					inlen      = len(inkeys)
					proc.input = ', '.join(inkeys)
					proc.input = propval.slice(idx, inlen)
					idx += inlen
		else:
			for proc in procs:
				if propname.startswith('args'):
					utils.dictUpdate (proc.args, dot2dictargs(propname, propval))
				elif propname.startswith('tplenvs'):
					utils.dictUpdate (proc.tplenvs, dot2dictargs(propname, propval))
				else:
					setattr(proc, propname, propval)
	
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
		newproc = p.copy(tag = utils.uid(self.id, 4), newid = p.id)
		newproc.aggr = self.id
		self.procs.append (newproc)
		if where == 'starts' or where == 'both':
			self.starts.append (newproc)
		if where == 'ends' or where == 'both':
			self.ends.append (newproc)
		self.__dict__[p.id] = newproc
		return self
		
	def copy (self, tag='notag', deps=True, newid=None):
		"""
		Like `proc`'s `copy` function, copy an aggregation. Each processes will be copied.
		@params:
			`tag`:      The new tag of all copied processes
			`deps`: Whether to copy the dependencies or not. Default: True
			- dependences for processes in starts will not be copied
			`newid`:    Use a different id if you don't want to use the variant name
		@returns:
			The new aggregation
		"""
		name     = utils.varname() if newid is None else newid
		tagstr   = utils.uid(name, 4) if not tag or tag == 'notag' else tag
		ret      = Aggr ()
		ret.id   = name
		
		for proc in self.procs:
			if tag == proc.tag:
				# This will happen to have procs with same id and tag
				raise ValueError('Tag "%s" is used by proc "%s" before, cannot copy with the same tag for aggregation: %s.' % (tag, proc.id, self.id))
			
			if proc not in self.starts and deps:
				for d in proc.depends:
					if d not in self.procs:
						raise ValueError('Failed to copy "%s": a non-start proc ("%s") depends on a proc("%s") does not belong to "%s"' % (self.id, proc.name(), d.name(), self.id))					
			
			newproc      = proc.copy (tag, proc.id)
			newproc.aggr = name

			
			where = 'both' if proc in self.starts and proc in self.ends \
				else 'starts' if proc in self.starts \
				else 'ends' if proc in self.ends \
				else None
			
			ret.addProc (newproc, where = where)
		
		ret.set ('tag', tagstr)
		# copy dependences
		for proc in self.procs:
			if proc in self.starts:
				continue
			
			ret.__dict__[proc.id].depends = [ret.__dict__[d.id] for d in proc.depends]

		return ret
		
	

		