"""
The procset for a set of procs
"""
import inspect
from types import GeneratorType
from fnmatch import fnmatch, filter as fnfilter
from functools import partial
from collections import OrderedDict
from .utils import varname, Box, OBox

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

	def __init__(self, *args, **kwargs):
		super(Values, self).__init__(args, **kwargs)

class PSProxy(object):

	def __init__(self, procset, path = None):
		self.__dict__['procset'] = procset
		self.__dict__['path']    = path or []

	def _delegatedAttrs(self, attr_to_set):
		path_to_check = '.'.join(self.path + [attr_to_set])
		for dele_name in self.procset.delegates.keys():
			if fnmatch(path_to_check, dele_name):
				procs = self.procset.delegated(dele_name)
				break
		else:
			procs = Proxy(self.procset.procs.values())
		for p in self.path:
			procs = getattr(procs, p)
		return procs

	def __getattr__(self, item):
		self.path.append(item)
		return self

	def __setattr__(self, name, value):
		attrs = self._delegatedAttrs(name)

		if isinstance(value, Values):
			for i, val in enumerate(value):
				setattr(attrs[i], name, val)
		else:
			for attr in attrs:
				setattr(attr, name, value)

class ProcSet(object):
	"""
	The ProcSet for a set of processes
	"""

	def __init__(self, *procs, **kwargs):
		"""
		Constructor
		@params:
			`*procs` : the set of processes
			`depends`: Whether auto deduce depends. Default: True
			`id`     : The id of the procset. Default: None (the variable name)
			`tag`    : The tag of the processes. Default: None (a unique 4-char str according to the id)
			`copy`   : Whether copy the processes or just use them. Default: `True`
		"""

		self.__dict__['id']        = kwargs.get('id') or varname(context = 101)
		self.__dict__['tag']       = kwargs.get('tag')
		self.__dict__['starts']    = Proxy()
		self.__dict__['ends']      = Proxy()
		self.__dict__['delegates'] = OBox()
		self.__dict__['procs']     = OBox()
		self.__dict__['modules']   = Box()
		# save initial states before a module is called
		# states will be resumed before each module is called
		self.__dict__['initials']  = Box()

		ifcopy  = kwargs.get('copy', True)
		depends = kwargs.get('depends', True)

		prevproc = None
		for proc in procs:
			assert hasattr(proc, 'id') and hasattr(proc, 'tag'), \
				'Argument has to be a Proc object: %r.' % proc
			if ifcopy:
				self.procs[proc.id] = proc.copy(proc.id,
					tag = (self.tag or proc.tag.split('@', 1)[0]) + '@' + self.id)
			else:
				self.procs[proc.id] = proc
				proc.config.tag = (self.tag or proc.tag.split('@', 1)[0]) + '@' + self.id

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

	def delegate(self, *procs):
		procs = list(procs)
		name  = procs.pop(0)
		self.delegates[name] = procs

	def delegated(self, name):
		if name not in self.delegates:
			return None
		return self[self.delegates[name]]

	def restoreStates(self):
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
				if defaults.get('restore', kwargs.get('restore', True)):
					self.restoreStates()
				func(self, *args, **kwargs)

			self.modules[name] = modfun
			return self.modules[name]
		return decorator

	# pylint: disable=arguments-differ,redefined-builtin,unused-argument,fixme
	def copy (self, id = None, tag = None, depends = True):
		"""
		Like `proc`'s `copy` function, copy a procset. Each processes will be copied.
		@params:
			`id`     : Use a different id if you don't want to use the variant name
			`tag`    : The new tag of all copied processes
			`depends`: Whether to copy the dependencies or not. Default: True
				- dependences for processes in starts will not be copied
		@returns:
			The new procset
		"""
		id  = id or varname()
		ret = self.__class__(*self.procs.values(), id = id, tag = tag, copy = True, depends = False)

		if depends:
			for procid, proc in ret.procs.items():
				proc.depends = [ret.procs[dep.id] if dep is self.procs[dep.id] else dep
					for dep in self.procs[proc.id].depends]

			ret.starts.add(Proxy(ret.procs[proc.id] for proc in self.starts))
			ret.ends.add(Proxy(ret.procs[proc.id] for proc in self.ends))

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

	def __getitem__(self, item, _ignore_default = True):
		"""Process selector, always return Proxy object"""
		if item in ('starts', 'ends'):
			return self.__getattr__(item)
		if hasattr(item, 'id') and hasattr(item, 'tag') and not isinstance(item, ProcSet):
			return Proxy([self.procs[item.id]])
		if isinstance(item, slice):
			return Proxy(self.__getattr__(procid) for procid in self.procs.keys()[item])
		if isinstance(item, int):
			return self[self.procs.keys()[item]]
		if isinstance(item, (tuple, list, GeneratorType)):
			ret = Proxy()
			ret.add(Proxy(it for itm in item for it in self[itm]))
			return ret
		if item in self.procs:
			return Proxy([self.procs[item]])
		if ',' in item:
			return self[(it.strip() for it in item.split(','))]

		return self[fnfilter(self.procs.keys(), item)]
