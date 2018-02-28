"""
The aggregation of procs
"""
from six import string_types
from collections import OrderedDict
from .exception import AggrAttributeError, AggrCopyError
from . import utils


class DotProxy(object):
	"""
	The proxy to do dot for attributes:
	aggr.args.params.b = True
	"""
	def __init__(self, aggr, prefix = ''):
		"""
		@params:
			`aggr`: The aggr
			`prefix`: The prefix of the proxy
		"""
		self.__dict__['_aggr']   = aggr
		self.__dict__['_prefix'] = prefix
	
	def __getattr__(self, name):
		"""
		@params:
			`name`: The attribute name
		@return:
			Another proxy
		"""
		if name in self.__dict__:
			return self.__dict__[name]
		prefix = self._prefix if not self._prefix else self._prefix + '.'
		self.__dict__[name] = DotProxy(self._aggr, prefix + name)
		return self.__dict__[name]
	
	@staticmethod
	def _isDelegated(aggr, prefix, delegates):
		"""
		Tell if a prefix is delegated
		@params:
			`prefix`: The prefix, like 'a.a.b' from 'aggr.a.a.b'
			`delegates`: The delegates
				`key` is like 'args.a'
				`dval` is like 'a.a'
			The you are able to use aggr.a.a.b = 1 to set values for args.[p].args.a.b
		@returns:
			False if not delegated, else return the name array, in the above case: ['args', 'a', 'b']
		"""
		for key, value in delegates.items():
			procs, val = value
			if not prefix.startswith(key):
				continue
			rest = prefix[len(key):]
			if rest and not rest.startswith('.'):
				continue
			return procs(aggr), (val + rest).split('.')
		return False
		
		
	def __setattr__(self, name, value):
		"""
		@params:
			`name`: The name of the attribute
			`value`: The value of the attribute
		"""
		prefix  = self._prefix if not self._prefix else self._prefix + '.'
		prefix += name
		delegated = DotProxy._isDelegated(self._aggr, prefix, self._aggr._delegates)
		if not delegated:
			raise AggrAttributeError(prefix, 'Attribute is not delegated')
		procs, dots = delegated
		setname     = dots.pop(-1)
		for proc in procs:
			obj = proc
			for dot in dots: obj = getattr(obj, dot)
			setattr(obj, setname, value)
			
	def __getitem__(self, name):
		return getattr(self, name)
		
	def __setitem__(self, name, value):
		setattr(self, name, value)

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

	def __init__ (self, *args, **kwargs):
		"""
		Constructor
		@params:
			`args`: the set of processes
			`depends`: Whether auto deduce depends. Default: True
			`id`: The id of the aggr. Default: None (the variable name)
			`tag`: The tag of the processes. Default: None (a unique 4-char str according to the id)
		"""

		# depends = True, id = None, tag = None
		self.__dict__['_props'] = {
			'starts'   : [],
			'ends'     : [],
			'id'       : utils.varname() if 'id' not in kwargs or not kwargs['id'] else kwargs['id']
		}
		self.__dict__['_delegates'] = OrderedDict()
		self.__dict__['_procs']     = OrderedDict()
		
		tag = kwargs['tag'] if 'tag' in kwargs else ''
		
		for proc in args:
			pid = proc.id
			if pid in ['starts', 'ends', 'id', '_delegates', '_props', '_procs'] or pid in self.__dict__['_procs']:
				raise AggrAttributeError(pid, 'Use a different process id, attribute name is already taken')
			newtag       = tag if tag else utils.uid(proc.tag + '@' + self.id, 4)
			newproc      = proc.copy(tag = newtag, id = pid)
			newproc.aggr = self.id
			self.__dict__['_procs'][pid] = newproc
		
		if 'depends' not in kwargs or kwargs['depends']:
			procs = list(self._procs.values())
			self.starts = [procs[0]] if len(procs) > 0 else []
			self.ends   = [procs[-1]] if len(procs) > 0 else []
			for i, proc in enumerate(procs):
				if i == 0: continue
				proc.depends = procs[i-1]
		
		# depends respectively: 
		# For example: 
		# a.starts  == [ps1, ps2, ps3]
		# a.depends2 = pd1, pd2, pd3 => 
		# 	a.ps1.depends = pd1
		# 	a.ps2.depends = pd2
		# 	a.ps3.depends = pd3
		# a.depends = pd1, pd2, pd3 =>
		# 	a.ps1.depends = pd1, pd2, pd3
		# 	a.ps2.depends = pd1, pd2, pd3
		# 	a.ps3.depends = pd1, pd2, pd3
		self.delegate('depends2', 'starts')
		self.delegate('depends' , 'starts')
		self.delegate('input'   , 'starts')
		self.delegate('exdir'   , 'ends')
		self.delegate('exhow'   , 'ends')
		self.delegate('exow'    , 'ends')
		self.delegate('expart'  , 'ends')

	def delegate(self, attr, procs = None, pattr = None):
		"""
		Delegate attributes of processes to aggr.
		@params
			`attr` : The attribute of the aggregation
			`procs`: The ids of the processes. Default: None (all processes)
			`pattr`: The attr of the processes. Default: None (same as `attr`)
		"""
		if attr in ['starts', 'ends', 'id', '_delegates', '_props', '_procs'] or attr in self.__dict__['_procs']:
			raise AggrAttributeError(attr, 'Cannot delegate Proc attribute to an existing Aggr attribute')

		if pattr is None: pattr = attr
		
		# use callbacks to make sure they apply for futher processes
		if procs == 'starts':
			procs = lambda a: a.starts
		elif procs == 'ends':
			procs = lambda a: a.ends
		elif procs == 'both':
			procs = lambda a: a.starts + a.ends
		elif procs == 'neither':
			procs = lambda a: [p for p in a._procs.values() if p not in (a.starts + a.ends)]
		elif isinstance(procs, string_types):
			procs = lambda a, procs = procs: [a._procs[procs]]
		elif isinstance(procs, list):
			procs = lambda a, procs = procs: [a._procs[proc if isinstance(proc, string_types) else proc.id] for proc in procs]
		elif not procs:
			procs = lambda a: a._procs.values()
		else:
			procs = lambda a, procs = procs: procs
			
		self._delegates[attr] = procs, pattr

	def __getattr__(self, name):
		if name in self.__dict__:
			return self.__dict__[name]
		if name in self._props:
			return self._props[name]
		if name in self._procs:
			return self._procs[name]
		
		self.__dict__[name] = DotProxy(self, name)
		return self.__dict__[name]

	def __setattr__(self, name, value):
		if name == 'id':
			self._props[name] = value
		elif name in ['starts', 'ends']:
			self._props[name] = list(value) if isinstance(value, tuple) or isinstance(value, list) else [value]
		elif name in self.__dict__:
			raise AggrAttributeError(name, 'Built-in attribute is not allowed to be modified')
		# set attributes of procs:
		# aAggr.args = {'a': 1}
		else:
			delegated = DotProxy._isDelegated(self, name, self._delegates)
			if not delegated:
				raise AggrAttributeError(name, 'Attribute is not delegated')
			procs, dots = delegated
			dot = dots[0]
			if dot in ['depends2', 'input'] and not isinstance(value, (list, tuple)):
				value = [value]
			for i, proc in enumerate(procs):
				if dot in ['depends2', 'input'] and i < len(value):
					setattr(proc, 'depends' if dot == 'depends2' else dot, value[i])
				else:
					setattr(proc, dot, value)
	
	def addProc (self, p, tag = None, where = None, copy = True):
		"""
		Add a process to the aggregation.
		Note that you have to adjust the dependencies after you add processes.
		@params:
			`p`:     The process
			`where`: Add to where: 'starts', 'ends', 'both' or None (default)
		@returns:
			the aggregation itself
		"""
		newtag = tag if tag else utils.uid(p.tag + '@' + self.id, 4)

		newproc = p.copy(id = p.id) if copy else p
		newproc.tag  = newtag
		newproc.aggr = self.id
		self._procs[newproc.id] = newproc
		if where == 'starts' or where == 'both':
			self.starts.append (newproc)
		if where == 'ends' or where == 'both':
			self.ends.append (newproc)
		return self
		
	def copy (self, tag=None, deps=True, id=None):
		"""
		Like `proc`'s `copy` function, copy an aggregation. Each processes will be copied.
		@params:
			`tag`:      The new tag of all copied processes
			`deps`: Whether to copy the dependencies or not. Default: True
			- dependences for processes in starts will not be copied
			`id`:    Use a different id if you don't want to use the variant name
		@returns:
			The new aggregation
		"""
		name = utils.varname() if id is None else id
		tag  = utils.uid(name, 4) if not tag else tag
		ret  = Aggr (id = name)
		ret.starts = [None] * len(self.starts)
		ret.ends   = [None] * len(self.ends)


		for k, proc in self._procs.items():
			if tag == proc.tag:
				# This will happen to have procs with same id and tag
				raise AggrCopyError('%s.%s' % (proc.id, tag), 'Cannot copy process with same id and tag')
			
			newproc      = proc.copy (tag = tag, id = proc.id)
			newproc.aggr = name
			
			where = 'both' if proc in self.starts and proc in self.ends \
				else 'starts' if proc in self.starts \
				else 'ends' if proc in self.ends \
				else None
			
			ret.addProc (newproc, tag = tag, where = None, copy = False)
			if where == 'starts' or where == 'both':
				ret.starts[self.starts.index(proc)] = newproc
			if where == 'ends' or where == 'both':
				ret.ends[self.ends.index(proc)] = newproc
		
		# copy delegates
		for k, v in self._delegates.items():
			ret._delegates[k] = v
		
		# copy dependences
		if deps:
			for k, proc in ret._procs.items():
				proc.depends = [
					p if p not in self._procs.values() else \
					ret._procs[p.id] \
					for p in self._procs[k].depends
				]

		return ret
		