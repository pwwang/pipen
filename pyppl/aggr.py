"""
The aggregation of procs
"""
from six import string_types
from collections import OrderedDict
from .exception import AggrAttributeError, AggrCopyError
from . import utils

class _DotProxy(object):
	"""
	Implement something like:
	```
	aggr = Aggr(...)
	aggr.args[0].inopts.cnames = True
	     -------
	# or do for a set of objects
	aggr.args[:2].inopts.cnames = True
	```
	"""
	def __init__(self, objs):
		self.__dict__['_DotProxy_objs'] = objs if isinstance(objs, list) else [objs]

	def __getattr__(self, name):
		if name == '_DotProxy_objs':
			return self.__dict__['_DotProxy_objs']
		return _DotProxy([getattr(obj, name) for obj in self._DotProxy_objs])

	def __setattr__(self, name, value):
		if name == '_DotProxy_objs':
			raise AttributeError('_DotProxy_objs is a readonly attribute of _DotProxy.')
		for obj in self._DotProxy_objs:
			setattr(obj, name, value)

	def __getitem__(self, name):
		return _DotProxy([obj[name] for obj in self._DotProxy_objs])

	def __setitem__(self, name, value):
		for obj in self._DotProxy_objs:
			obj[name] = value
	

class _Proxy(object):
	"""
	The proxy used to set attribute for processes.
	Implement something like this:
	```
	aggr = Aggr(...)
	aggr.args[0].inopts.cnames = True
	     ----
	aggr.args['pSurvival'].inopts.cnames = True
	aggr.forks[0] = 10
	     -----
	aggr.forks = 10 # for all procs
	```
	"""
	def __init__(self, name, procs, starts, ends):
		self.__dict__['_ids']    = list(procs.keys())
		self.__dict__['_starts'] = [proc.id for proc in starts]
		self.__dict__['_ends']   = [proc.id for proc in ends]
		self.__dict__['_procs']  = list(procs.values())
		self.__dict__['_attr']   = name

	def _any2index(self, anything):
		"""
		Convert anything to index to fetch attrs of the procs
		```
		procids = ['a', 'b', 'c']
		_any2index('a')   # 0
		_any2index(0)     # 0
		_any2index(1:2)   # slice(1,2)
		_any2index([1,3]) # [1,3]
		_any2index(['b', 'c']) # [2,3]
		_any2index('b,c') # [2,3]
		```
		"""
		if isinstance(anything, (int, slice)):
			return anything
		elif isinstance(anything, (list, tuple)):
			return [self._any2index(a) for a in anything]
		elif ',' in anything:
			return self._any2index(utils.alwaysList(anything))
		elif anything == 'starts':
			return self._any2index(self._starts)
		elif anything == 'ends':
			return self._any2index(self._ends)
		else: # str
			return self._ids.index(anything)

	def __getitem__(self, index):
		"""
		Get a list of attributes and send them to _DotProxy for dot operations
		"""
		index = self._any2index(index)
		
		if isinstance(index, int):
			ret = getattr(self._procs[index], self._attr)
		elif isinstance(index, slice):
			ret = [getattr(proc, self._attr) for proc in self._procs[index]]
		else:
			ret = []
			for idx in index:
				if isinstance(idx, int):
					ret.append(getattr(self._procs[idx], self._attr))
				else:
					ret.extend([getattr(proc, self._attr) for proc in self._procs[idx]])
		
		return _DotProxy(ret)

	def __setitem__(self, index, value):
		"""
		Set the attributes for the select procs
		"""
		index = self._any2index(index)
		if isinstance(index, int):
			setattr(self._procs[index], self._attr, value)
		elif isinstance(index, slice):
			for proc in self._procs[index]:
				setattr(proc, self._attr, value)
		else:
			for idx in index:
				if isinstance(idx, int):
					setattr(self._procs[idx], self._attr, value)
				else:
					for proc in self._procs[idx]:
						setattr(proc, self._attr, value)

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
	ATTR_STARTS = ['input', 'depends']
	ATTR_ENDS   = ['exdir', 'exhow', 'exow', 'expart']

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
		self.__dict__['starts'] = []
		self.__dict__['ends']   = []
		self.__dict__['id']     = kwargs.get('id') or utils.varname()
		self.__dict__['_procs'] = OrderedDict()

		tag = kwargs['tag'] if 'tag' in kwargs else ''

		for proc in args:
			pid = proc.id
			if pid in ['starts', 'ends', 'id', '_procs'] or pid in self.__dict__['_procs']:
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

	def __getattr__(self, name):
		if name in self.__dict__:
			return self.__dict__[name]
		if name in self._procs:
			return self._procs[name]

		if name in Aggr.ATTR_STARTS:
			return _Proxy(name, self.starts, self.starts, self.ends)
		elif name in Aggr.ATTR_ENDS:
			return _Proxy(name, self.ends, self.starts, self.ends)
		else:
			return _Proxy(name, self._procs, self.starts, self.ends)

	def __setattr__(self, name, value):
		if name == 'id':
			self.__dict__['id'] = value
		elif name in ['starts', 'ends']:
			self.__dict__[name] = list(value) if isinstance(value, (list, tuple)) else [value]
		elif name in self.__dict__:
			raise AggrAttributeError(name, 'Built-in attribute is not allowed to be modified')
		elif name in Aggr.ATTR_STARTS:
			# don't pass the samething for input and depends of all processes
			# if you do want that, please use input2 and depends2
			# make sure passing a list explictly
			if not isinstance(value, list):
				raise AggrAttributeError(name, 'Expecting a list for attribute')
			for i, val in enumerate(value):
				setattr(self.starts[i], name, val)
		elif name in [attr + '2' for attr in Aggr.ATTR_STARTS]:
			# input2, depends2
			name = name[:-1]
			for proc in self.starts:
				setattr(proc, name, value)
		elif name in Aggr.ATTR_ENDS:
			for proc in self.ends:
				setattr(proc, name, value)
		else:
			# set attributes of all procs:
			# aAggr.args = {'a': 1}
			for proc in self._procs.values():
				# don't overwrite the config that has been set
				if name in proc.sets: continue
				setattr(proc, name, value)

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

		# copy dependences
		if deps:
			for k, proc in ret._procs.items():
				proc.depends = [
					p if p not in self._procs.values() else \
					ret._procs[p.id] \
					for p in self._procs[k].depends
				]

		return ret
