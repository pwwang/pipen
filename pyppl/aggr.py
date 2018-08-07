"""
The aggregation of procs
"""
from six import string_types
from collections import OrderedDict
from .exception import AggrAttributeError, AggrCopyError, AggrKeyError
from . import utils

class _Proxy(object):
	"""
	A proxy for a list of procs to set/get their attributes	
	"""
	def __init__(self, aggr, procs = None, prefix = None, check = False):
		self.__dict__['_aggr']   = aggr
		self.__dict__['_procs']  = procs or list(aggr._procs.values())
		self.__dict__['_prefix'] = prefix or []
		self.__dict__['_check']  = check # check delegates or not

	def __getattr__(self, name):
		if name in self.__dict__: # pragma: no cover
			return self.__dict__[name]
		return self[name]

	def __setattr__(self, name, value):
		prefix = self._prefix + [name]
		# check if any attributes are delegated to aggr
		procs = self._procs
		if self._check: 
			for i in range(len(prefix), 0, -1):
				attr = '.'.join(prefix[:i])
				if attr in self._aggr._delegates:
					procs = self._aggr._select(self._aggr._delegates[attr])
					break
				elif attr.endswith('2') and attr[:-1] in self._aggr._delegates:
					procs = self._aggr._select(self._aggr._delegates[attr[:-1]])
					break
		
		if prefix == ['depends'] or prefix == ['depends2']:
			value = self._aggr._select(value, forceList = True, flatten = False)
		
		if prefix == ['input'] or prefix == ['depends']:
			if not isinstance(value, list):
				raise AggrAttributeError(value, 'Require a list as input for a list of procs, but got.')
			for i, proc in enumerate(procs):
				if i < len(value) and value[i] is not None:
					setattr(proc, prefix[0], value[i])
		elif prefix == ['input2'] or prefix == ['depends2']:
			for proc in procs:
				setattr(proc, prefix[0][:-1], value)
		elif len(prefix) == 1:
			p = prefix[0]
			for proc in procs:
				if p in proc.sets:
					continue
				setattr(proc, p, value)
		else:	
			for proc in procs:
				obj = proc
				for px in self._prefix:
					obj = getattr(obj, px)
				setattr(obj, name, value)
	
	def __getitem__(self, name):
		return _Proxy(self._aggr, self._procs, self._prefix + [name], self._check)

	def __setitem__(self, name, value):
		self.__setattr__(name, value)

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

		#             depends       = True, id = None, tag = None
		self.__dict__['starts']     = []
		self.__dict__['ends']       = []
		self.__dict__['id']         = kwargs.get('id') or utils.varname()
		self.__dict__['_procs']     = OrderedDict()
		self.__dict__['_delegates'] = {}
		self.__dict__['_modules']     = {}

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

		theprocs = []
		for proc in procs:
			if proc == 'starts' or proc == 'ends':
				theprocs.append(proc)
			elif isinstance(proc, string_types):
				theprocs.append(self._procs[proc])
			else:
				theprocs.append(proc)
				
		for attr in attrs:
			self._delegates[attr] = theprocs

	def _select(self, key, forceList = False, flatten = True):
		"""
		Select processes
		```
		# self._procs = OrderedDict([
		#	('a', Proc(id = 'a')), 
		#	('b', Proc(id = 'b')), 
		#	('c', Proc(id = 'c')),
		#	('d', Proc(id = 'd'))
		# ])

		self['a'] # proc a
		self[0]   # proc a
		self[1:2] # _Proxy of (proc b, proc c)
		self[1,3] # _Proxy of (proc b, proc d)
		self['b', 'c'] # _Proxy of (proc b, proc c)
		self['b,c'] # _Proxy of (proc b, proc c)
		self[Proc(id = 'd')] # proc d
		"""
		if isinstance(key, (slice, int)):
			ret = list(self._procs.values())[key]
		elif isinstance(key, string_types):
			if ',' in key:
				ret = self._select(utils.alwaysList(key))
			elif key == 'starts':
				ret = self._select(self.starts)
			elif key == 'ends':
				ret = self._select(self.ends)
			else:
				ret = self._procs[key]
		elif isinstance(key, (tuple, list)):
			ret = [self._select(k) for k in key if k != '' and k is not None]
			if flatten:
				ret = sum([r if isinstance(r, list) else [r] for r in ret], [])
		elif hasattr(key, 'id'): # Proc
			ret = key
		else:
			ret = None
		
		if not ret or not forceList or isinstance(ret, list): 
			return ret
		return [ret]

	def __getitem__(self, key):
		"""
		Select processes
		```
		# self._procs = OrderedDict([
		#	('a', Proc(id = 'a')), 
		#	('b', Proc(id = 'b')), 
		#	('c', Proc(id = 'c')),
		#	('d', Proc(id = 'd'))
		# ])

		self['a'] # proc a
		self[0]   # proc a
		self[1:2] # _Proxy of (proc b, proc c)
		self[1,3] # _Proxy of (proc b, proc d)
		self['b', 'c'] # _Proxy of (proc b, proc c)
		self['b,c'] # _Proxy of (proc b, proc c)
		self[Proc(id = 'd')] # proc d
		"""
		procs = self._select(key)
		if procs is None:
			raise AggrKeyError(key, "I don't know how to select procs using")
		if isinstance(procs, list):
			return _Proxy(self, procs)
		return procs

	def __getattr__(self, name):
		if name in self.__dict__: # pragma: no cover
			return self.__dict__[name]
		if name in self._procs:
			return self._procs[name]

		# This disables assignment of attribute of a specific process
		# if name in self._delegates:
		# 	procs = self._delegates[name]
		# 	procs = {proc.id:proc for proc in procs}
		# else:
		# 	procs = self._procs

		# Trying to setattr for all procs
		# aggr.args.xxx
		return _Proxy(self, prefix = [name], check = True)

	def __setattr__(self, name, value):
		if name == 'id':
			self.__dict__['id'] = value
		elif name in ['starts', 'ends']:
			self.__dict__[name] = self._select(value, forceList = True)
		elif name in self.__dict__: # pragma: no cover
			raise AggrAttributeError(name, 'Built-in attribute is not allowed to be modified directly.')
		else:
			proxy = _Proxy(self, check = True)
			setattr(proxy, name, value)

	def moduleFunc(self, name, on, off = None):
		self._modules[name] = dict(on = on, off = off, status = 'off')

	def module(self, name, starts = None, depends = None, ends = None, starts_shared = None, depends_shared = None, ends_shared = None):
		"""
		Define a function for aggr.
		The "shared" parameters will be indicators not to remove those processes 
		when the shared function is on.
		@params:
			`name`          : The name of the function
			`starts`        : A list of start processes.
			`depends`       : A dict of dependences of the procs
			`ends`          : A list of end processes
			`starts_shared` : A dict of functions that shares the same starts
			`depends_shared`: A dict of functions that shares the same depends
			`ends_shared`   : A dict of functions that shares the same ends
				- For example: `{<procs>: <func>}`
		"""
		starts  = starts or []
		depends = depends or {}
		ends    = ends or []

		starts_shared  = starts_shared or {}
		depends_shared = depends_shared or {}
		ends_shared    = ends_shared or {}

		def on(a):
			a.addStart(starts)
			for key, val in depends.items():
				if isinstance(a[key], _Proxy):
					a[key].depends = a._select(val, forceList = True, flatten = False)
				else:
					a[key].depends = a._select(val, forceList = True, flatten = True)
			a.addEnd(ends)

		def off(a):
			startsdel = a._select(starts, forceList = True)
			# get all starts that need to keep
			startskeep = []
			for key, val in starts_shared.items():
				funcs = utils.alwaysList(val)
				# skip if all funcs are off
				if all([a._modules[func]['status'] == 'off' for func in funcs]): 
					continue
				startskeep.extend(a._select(key, forceList = True))
			a.delStart([proc for proc in startsdel if proc not in startskeep])

			depsdel = list(depends.keys())
			# depends need to keep
			depskeep = []
			for key, val in depends_shared.items():
				funcs = utils.alwaysList(val)
				# skip if all funcs are off
				if all([a._modules[func]['status'] == 'off' for func in funcs]): 
					continue
				depskeep.extend(a._select(key, forceList = True))

			for proc in a._select(depsdel, forceList = True):
				if proc in depskeep:
					continue
				proc.depends = []
			
			endsdel = a._select(ends, forceList = True)
			# get all ends that need to keep
			endskeep = []
			for key, val in ends_shared.items():
				funcs = utils.alwaysList(val)
				# skip if all funcs are off
				if all([a._modules[func]['status'] == 'off' for func in funcs]): 
					continue
				endskeep.extend(a._select(key, forceList = True))
			a.delEnd([proc for proc in endsdel if proc not in endskeep])
		
		self.moduleFunc(name, on, off)

	def on(self, *names):
		names = sum([utils.alwaysList(name) for name in names], [])
		names = names or self._modules.keys()
		for name in names:
			if self._modules[name]['on']:
				self._modules[name]['status'] = 'on'
				self._modules[name]['on'](self)
	
	def off(self, *names):
		names = sum([utils.alwaysList(name) for name in names], [])
		names = names or self._modules.keys()
		for name in names:
			if self._modules[name]['off']:
				self._modules[name]['status'] = 'off'
				self._modules[name]['off'](self)

	def addStart(self, *procs):
		order       = self._procs.values()
		procs       = self._select(procs, forceList = True) + self.starts
		self.starts = [proc for proc in order if proc in procs]
	
	def delStart(self, *procs):
		procs       = self._select(procs, forceList = True)
		self.starts = [proc for proc in self.starts if proc not in procs]

	def addEnd(self, *procs):
		order     = self._procs.values()
		procs     = self._select(procs, forceList = True) + self.ends
		self.ends = [proc for proc in order if proc in procs]
	
	def delEnd(self, *procs):
		procs     = self._select(procs, forceList = True)
		self.ends = [proc for proc in self.ends if proc not in procs]

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

	def copy (self, tag=None, depends=True, id=None, delegates = True, modules = True):
		"""
		Like `proc`'s `copy` function, copy an aggregation. Each processes will be copied.
		@params:
			`tag`:      The new tag of all copied processes
			`depends`: Whether to copy the dependencies or not. Default: True
			- dependences for processes in starts will not be copied
			`id`:    Use a different id if you don't want to use the variant name
			`delegates`: Copy delegates? Default: `True`
			`configs`: Copy configs? Default: `True`
		@returns:
			The new aggregation
		"""
		name = utils.varname() if id is None else id
		tag  = utils.uid(name, 4) if not tag else tag
		ret  = Aggr (id = name)
		ret.__dict__['starts'] = [None] * len(self.starts)
		ret.__dict__['ends']   = [None] * len(self.ends)
		
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
		if depends:
			for k, proc in ret._procs.items():
				proc.depends = [
					p if p not in self._procs.values() else ret._procs[p.id] 
					for p in self._procs[k].depends
				]

		if delegates:
			for k, procs in self._delegates.items():
				ret._delegates[k] = [
					proc if isinstance(proc, string_types) else ret._procs[proc.id] 
					for proc in procs
				]
		else:
			# trigger the default delegates
			ret.starts = ret.starts
			ret.ends   = ret.ends

		if modules:
			for k, v in self._modules.items():
				ret._modules[k] = v

		return ret
