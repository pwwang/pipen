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
	def __init__(self, procs, delegates, prefix):
		self.__dict__['_DotProxy_procs']     = procs if isinstance(procs, list) else [procs]
		self.__dict__['_DotProxy_delegates'] = delegates
		self.__dict__['_DotProxy_prefix']    = prefix

	@staticmethod
	def _setProcsAttr(procs, prefix, name, value):
		for proc in procs:
			obj = proc
			for p in prefix:
				obj = getattr(obj, p)
			setattr(obj, name, value)

	@staticmethod
	def _setProcsItem(procs, prefix, name, value):
		for proc in procs:
			obj = proc
			for p in prefix:
				obj = getattr(obj, p)
			obj[name] = value

	def __getattr__(self, name):
		if name in self.__dict__:
			return self.__dict__[name]
		
		attr  = '.'.join(self._DotProxy_prefix + [name])
		procs = self._DotProxy_delegates.get(attr, self._DotProxy_procs)
		return _DotProxy(procs, self._DotProxy_delegates, self._DotProxy_prefix + [name])

	def __setattr__(self, name, value):
		if name in self.__dict__:
			raise AttributeError('{} is a readonly attribute of _DotProxy.'.format(name))
		attr  = '.'.join(self._DotProxy_prefix + [name])
		procs = self._DotProxy_delegates.get(attr, self._DotProxy_procs)
		_DotProxy._setProcsAttr(procs, self._DotProxy_prefix, name, value)

	def __getitem__(self, name):
		"""
		will be treated as getattr
		"""
		return self.__getattr__(name)

	def __setitem__(self, name, value):
		if name in self.__dict__:
			return self.__dict__[name]
		
		attr  = '.'.join(self._DotProxy_prefix + [name])
		procs = self._DotProxy_delegates.get(attr, self._DotProxy_procs)
		_DotProxy._setProcsItem(procs, self._DotProxy_prefix, name, value)
	

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
	def __init__(self, name, procs, starts, ends, delegates):
		self.__dict__['_ids']       = list(procs.keys())
		self.__dict__['_starts']    = [proc.id for proc in starts]
		self.__dict__['_ends']      = [proc.id for proc in ends]
		self.__dict__['_procs']     = list(procs.values())
		self.__dict__['_attr']      = name
		self.__dict__['_delegates'] = delegates

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

	def __getattr__(self, name):
		"""
		aggr.args.name.xxx
		          ^^^^
		"""
		if name in self.__dict__:
			return self.__dict__[name]

		# check if args.name is delegated:
		attr = '.'.join([self._attr, name])
		if attr in self._delegates:
			procs = self._delegates[attr]
		elif self._attr in self._delegates:
			procs = self._delegates[self._attr]
		else:
			procs = self._procs
		return _DotProxy(procs, self._delegates, [self._attr, name])

	def __setattr__(self, name, value):
		"""
		aggr.args.params = '-input xxx'
		"""
		# check if args.name is delegated:
		attr = '.'.join([self._attr, name])
		if attr in self._delegates:
			procs = self._delegates[attr]
		elif self._attr in self._delegates:
			procs = self._delegates[self._attr]
		else:
			procs = self._procs
		
		for proc in procs:
			setattr(getattr(proc, self._attr), name, value)

	def __getitem__(self, index):
		"""
		Get a list of attributes and send them to _DotProxy for dot operations
		aggr.args[procs].params
		"""
		try:
			index = self._any2index(index)
		except ValueError:
			# not recommended, but just for avilability
			# getting attribute instead of selecting procs
			return self.__getattr__(index)
		
		if isinstance(index, int):
			procs = [self._procs[index]]
		elif isinstance(index, slice):
			procs = self._procs[index]
		else:
			procs = []
			for idx in index:
				if isinstance(idx, int):
					procs.append(self._procs[idx])
				else:
					procs.extend(self._procs[idx])
		
		# return _DotProxy(procs, self._delegates, [self._attr])
		# should not apply delegates any more, because specified processes have been selected.
		return _DotProxy(procs, {}, [self._attr])

	def __setitem__(self, index, value):
		"""
		Set the attributes for the select procs
		"""
		try:
			index = self._any2index(index)
		except ValueError:
			# not recommended, but just for avilability
			self.__setattr__(index, value)
			return

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

		#             depends              = True, id = None, tag = None
		self.__dict__['starts']            = []
		self.__dict__['ends']              = []
		self.__dict__['id']                = kwargs.get('id') or utils.varname()
		self.__dict__['_procs']            = OrderedDict()
		self.__dict__['_delegates']        = {}
		# starts/ends may be changed later, remember the attrs to update them
		self.__dict__['_delegates_starts'] = []
		self.__dict__['_delegates_ends']   = []
		self.__dict__['_config']           = {}

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

		self.delegate(Aggr.ATTR_STARTS, 'starts')
		self.delegate(Aggr.ATTR_ENDS, 'ends')

	def delegate(self, attrs, procs):
		"""
		Delegate the procs to have the attributes set by:
		`aggr.args.a.b = 1`
		Instead of setting `args.a.b` of all processes, `args.a.b` of only delegated processes will be set.
		`procs` can be `starts`/`ends`, but it cannot be set with other procs, which means you can do:  
		`aggr.delegate('args', 'starts')`, but not `aggr.delegate('args', ['starts', 'pXXX'])`
		"""
		if not isinstance(attrs, (tuple, list)):
			attrs = utils.alwaysList(attrs)
		if isinstance(procs, string_types):
			procs = utils.alwaysList(procs)
		elif not isinstance(procs, (tuple, list)):
			procs = [procs]

		if procs == ['starts']:
			self._delegates_starts.extend(attrs)
		if procs == ['ends']:
			self._delegates_ends.extend(attrs)

		theprocs = []
		for proc in procs:
			if proc == 'starts':				
				theprocs.extend(self.starts) # what if self.starts is changed later?
			elif proc == 'ends':
				theprocs.extend(self.ends)
			elif isinstance(proc, string_types):
				theprocs.append(self._procs[proc])
			else:
				theprocs.append(proc)
				
		for attr in attrs:
			self._delegates[attr] = theprocs			

	def __getattr__(self, name):
		if name in self.__dict__:
			return self.__dict__[name]
		if name in self._procs:
			return self._procs[name]

		# This disables assignment of attribute of a specific process
		# if name in self._delegates:
		# 	procs = self._delegates[name]
		# 	procs = {proc.id:proc for proc in procs}
		# else:
		# 	procs = self._procs
		return _Proxy(name, self._procs, self.starts, self.ends, self._delegates)

	def __setattr__(self, name, value):
		if name == 'id':
			self.__dict__['id'] = value
		elif name in ['starts', 'ends']:
			self.__dict__[name] = list(value) if isinstance(value, (list, tuple)) else [value]
			# update delegates here?
			if name == 'starts':
				for attr in self._delegates_starts:
					self._delegates[attr] = self.starts
			else:
				for attr in self._delegates_ends:
					self._delegates[attr] = self.ends
		elif name in self.__dict__:
			raise AggrAttributeError(name, 'Built-in attribute is not allowed to be modified')
		else:
			if name in self._delegates or (name[-1] == '2' and name[:-1] in self._delegates):
				procs = self._delegates[name[:-1] if name[-1] == '2' else name]
			else:
				procs = [proc for proc in self._procs.values() if not name in proc.sets]

			if name in Aggr.ATTR_STARTS:
				# don't pass the samething for input and depends of all processes
				# if you do want that, please use input2 and depends2
				# make sure passing a list explictly
				if not isinstance(value, list):
					raise AggrAttributeError(name, 'Expecting a list for attribute')
				for i, val in enumerate(value):
					setattr(procs[i], name, val)
			else:
				if name[-1] == '2' and name[:-1] in Aggr.ATTR_STARTS:
					name = name[:-1]
				for proc in procs:
					setattr(proc, name, value)

	def config(self, name, on, off):
		self._config[name] = dict(on = on, off = off)

	def on(self, *names):
		names = sum([utils.alwaysList(name) for name in names], [])
		for name in names:
			self._config[name]['on'](self)
	
	def off(self, *names):
		names = sum([utils.alwaysList(name) for name in names], [])
		for name in names:
			self._config[name]['off'](self)

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
