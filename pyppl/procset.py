"""
The procset for a set of procs
"""
import inspect
from types import GeneratorType
from fnmatch import fnmatch, filter as fnfilter
from diot import Diot, OrderedDiot
from varname import varname

class Proxy(list):
	"""
	A proxy class extended from list to enable dot access
	to all members and set attributes for all members.
	"""

	def __getattr__(self, item):
		try:
			# Get the attributes of list
			return getattr(super(Proxy, self), item)
		except AttributeError:
			return self.__class__(getattr(proxy, item) for proxy in self)

	def __setattr__(self, name, value):
		# We are unable to setattr of existing attribute of list
		#if hasattr(super(Proxy, self), name):
		#	super(Proxy, self).__setattr__(name, value)
		if isinstance(value, Values):
			for i, val in enumerate(value):
				setattr(self[i], name, val)
		else:
			for proxy in self:
				setattr(proxy, name, value)

	def __getitem__(self, item):
		if isinstance(item, int):
			return super(Proxy, self).__getitem__(item)
		if isinstance(item, slice):
			return self.__class__(super(Proxy, self).__getitem__(item))
		return self.__getattr__(item)

	def __setitem__(self, item, value):
		if isinstance(item, (int, slice)):
			return super(Proxy, self).__setitem__(item, value)
		return self.__setattr__(item, value)

	def add(self, anything):
		"""
		Add elements to the list.
		@params:
			`anything`: anything that is to be added.
				If it is a Proxy, element will be added individually
				Otherwise the whole `anything` will be added as one element.
		"""
		if not anything:
			return
		if isinstance(anything, Proxy):
			for thing in anything:
				self.add(thing)
		elif anything not in self:
			self.append(anything)

class Values(Proxy):
	"""A Proxy class but element can be passed one by one"""
	def __init__(self, *args, **kwargs):
		super().__init__(args, **kwargs)

class PSProxy:
	"""A Proxy for procset"""
	def __init__(self, procset, path = None):
		self.__dict__['procset'] = procset
		self.__dict__['path']    = path or []

	def _delegated_attrs(self, attr_to_set):
		path_to_check = '.'.join(self.path + [attr_to_set])
		for dele_name in self.procset.delegates.keys():
			if fnmatch(path_to_check, dele_name):
				procs = self.procset.delegated(dele_name)
				break
		else:
			procs = Proxy(self.procset.procs.values())
		for pat in self.path:
			procs = getattr(procs, pat)
		return procs

	def __getattr__(self, item):
		self.path.append(item)
		return self

	def __setattr__(self, name, value):
		attrs = self._delegated_attrs(name)
		if isinstance(value, Values):
			for i, val in enumerate(value):
				setattr(attrs[i], name, val)
		else:
			for attr in attrs:
				setattr(attr, name, value)

class ProcSet:
	"""@API
	The ProcSet for a set of processes
	"""
	# pylint: disable=redefined-builtin
	def __init__(self, *procs, id = None, tag = None, copy = True, depends = True):
		"""@API
		Constructor
		@params:
			*procs (Proc) : the set of processes
			**kwargs: Other arguments to instantiate a `ProcSet`
				depends (bool): Whether auto deduce depends. Default: `True`
				id (str): The id of the procset. Default: `None` (the variable name)
				tag (str): The tag of the processes. Default: `None`
				copy (bool): Whether copy the processes or just use them. Default: `True`
		"""

		self.__dict__['id']        = id or varname(context = 50)
		self.__dict__['tag']       = tag
		self.__dict__['starts']    = Proxy()
		self.__dict__['ends']      = Proxy()
		self.__dict__['delegates'] = OrderedDiot(diot_nest = False)
		self.__dict__['procs']     = OrderedDiot(diot_nest = False)
		self.__dict__['modules']   = Diot(diot_nest = False)
		# save initial states before a module is called
		# states will be resumed before each module is called
		self.__dict__['initials']  = Diot(diot_nest = False)

		prevproc = None
		for proc in procs:
			assert hasattr(proc, 'id') and hasattr(proc, 'tag'), \
				'Argument has to be a Proc object: %r.' % proc
			if copy:
				self.procs[proc.id] = proc.copy(proc.id,
					tag = (self.tag or proc.tag.split('@', 1)[0]) + '@' + self.id)
			else:
				self.procs[proc.id] = proc
				proc.tag = (self.tag or proc.tag.split('@', 1)[0]) + '@' + self.id

			if depends and prevproc is None:
				self.starts.add(self[proc.id])

			if depends and prevproc:
				self.procs[proc.id].depends = prevproc

			prevproc = self.procs[proc.id]

		if depends and prevproc:
			self.ends.add(prevproc)

		self.delegate('input', 'starts')
		self.delegate('depends', 'starts')
		self.delegate('ex*', 'ends')

	def delegate(self, attr, *procs):
		"""@API
		Delegate process attributes to procset.
		@params:
			*procs (str|Proc): The first argument is the name of the attributes.
				- The rest of them should be `Proc`s or `Proc` selectors.
		"""
		procs = list(procs)
		self.delegates[attr] = procs

	def delegated(self, name):
		"""@API
		Get the detegated processes by specific attribute name
		@params:
			name (str): the attribute name to query
		@returns:
			(Proxy): The set of processes
		"""
		if name not in self.delegates:
			return None
		return self[self.delegates[name]]

	def restore_states(self):
		"""@API
		Restore the initial state of a procset
		"""
		if not self.initials: # extract the inital states
			self.initials.starts  = self.starts[:]
			self.initials.ends    = self.ends[:]
			self.initials.depends = {pid: proc.depends for pid, proc in self.procs.items()}
		else:
			self.__dict__['starts'] = self.initials.starts[:]
			self.__dict__['ends']   = self.initials.ends[:]
			for pid, depends in self.initials.items():
				self.procs[pid] = depends

	def module(self, name):
		"""@API
		A decorator used to define a module.
		@params:
			name (callable|str): The function to be decorated or the name of the module.
		@returns:
			(callable): The decorator
		"""
		if callable(name):
			funcname = name.__name__
			if funcname.startswith(self.id + '_'):
				funcname = funcname[(len(self.id) + 1):]
			return self.module(funcname)(name)

		def decorator(func):
			signature = inspect.signature(func)
			defaults  = {
				key: val.default
				for key, val in signature.parameters.items()
				if val.default is not inspect.Parameter.empty}
			def modfun(*args, **kwargs):
				if kwargs.get('restore', defaults.get('restore', True)):
					self.restore_states()
				func(self, *args, **kwargs)

			self.modules[name] = modfun
			return self.modules[name]
		return decorator

	# pylint: disable=arguments-differ,redefined-builtin,unused-argument,invalid-name
	def copy (self, id = None, tag = None, depends = True):
		"""@API
		Like `proc`'s `copy` function, copy a procset. Each processes will be copied.
		@params:
			id (str): Use a different id if you don't want to use the variant name
			tag (str): The new tag of all copied processes
			depends (bool): Whether to copy the dependencies or not. Default: True
				- dependences for processes in starts will not be copied
		@returns:
			(ProcSet): The new procset
		"""
		id  = id or varname()
		ret = self.__class__(*self.procs.values(),
			id = id, tag = tag, copy = True, depends = False)

		if depends:
			for proc in ret.procs.values():
				proc.depends = [ret.procs[dep.id]
					if dep is self.procs[dep.id] else dep
					for dep in self.procs[proc.id].depends]

			ret.starts.add(
				Proxy(ret.procs[proc.id] for proc in self.starts))
			ret.ends.add(
				Proxy(ret.procs[proc.id] for proc in self.ends))

		return ret

	def __setattr__(self, item, value):
		if item in ('starts', 'ends'):
			self.__dict__[item] = self[value]
		elif item in ('id', 'tag'):
			self.__dict__[item] = value
		else:
			PSProxy(procset = self).__setattr__(item, value)

	def __getattr__(self, item):
		if item in self.__dict__:
			return self.__dict__[item]
		if item in self.procs:
			return self.procs[item]
		return PSProxy(procset = self, path = [item])

	def __getitem__(self, item, _ignore_default = True): # pylint:disable=too-many-return-statements
		"""@API:
		Process selector, always return Proxy object
		@params:
			item (any): The process selector.
		@returns:
			(Proxy): The processes match the item."""
		if item in ('starts', 'ends'):
			return self.__getattr__(item)
		if hasattr(item, 'id') and hasattr(item, 'tag') and not isinstance(item, ProcSet):
			return Proxy([self.procs[item.id]])
		if isinstance(item, slice):
			return Proxy(self.__getattr__(procid) for procid in list(self.procs.keys())[item])
		if isinstance(item, int):
			return self[list(self.procs.keys())[item]]
		if isinstance(item, (tuple, list, GeneratorType)):
			ret = Proxy()
			ret.add(Proxy(it for itm in item for it in self[itm]))
			return ret
		if item in self.procs:
			return Proxy([self.procs[item]])
		if ',' in item:
			return self[(it.strip() for it in item.split(','))]

		return self[fnfilter(self.procs.keys(), item)]
