"""
The aggregation of procs
"""
import fnmatch
from collections import OrderedDict
from box import Box
from .utils import varname

class _Proxy(list):
	"""
	A proxy class extended from list to enable dot access
	to all members and set attributes for all members.
	"""
	def __getattr__(self, item):
		if hasattr(super(_Proxy, self), item):
			return getattr(super(_Proxy, self), item)

		return self.__class__(getattr(proxy, item) for proxy in self)

	def __setattr__(self, name, value):
		if hasattr(super(_Proxy, self), name):
			super(_Proxy, self).__setattr__(name, value)

		if isinstance(value, tuple):
			for i, val in enumerate(value):
				setattr(self[i], name, val)
		else:
			for proxy in self:
				setattr(proxy, name, value)

	def __getitem__(self, item):
		if isinstance(item, (int, slice)):
			return super(_Proxy, self).__getitem__(item)
		return self.__getattr__(item)

	def __setitem__(self, item, value):
		if isinstance(item, (int, slice)):
			return super(_Proxy, self).__setattr__(item, value)
		return self.__setattr__(item, value)

	def add(self, anything):
		"""
		Add elements to the list.
		@params:
			`anything`: anything that is to be added.
				If it is a _Proxy, element will be added individually
				Otherwise the whole `anything` will be added as one element.
		"""
		if isinstance(anything, _Proxy):
			for thing in anything:
				self.add(thing)
		elif not anything in self:
			self.append(anything)

class Aggr(Box):
	"""
	The aggregation of a set of processes
	"""

	def __init__(self, *procs, **kwargs):
		"""
		Constructor
		@params:
			`*procs` : the set of processes
			`depends`: Whether auto deduce depends. Default: True
			`id`     : The id of the aggr. Default: None (the variable name)
			`tag`    : The tag of the processes. Default: None (a unique 4-char str according to the id)
			`copy`   : Whether copy the processes or just use them. Default: `True`
		"""
		from . import Proc
		boxargs = OrderedDict()

		boxargs['id']               = kwargs.get('id') or varname()
		boxargs['tag']              = kwargs.get('tag')
		boxargs['starts']           = _Proxy()
		boxargs['ends']             = _Proxy()
		boxargs['groups']           = Box(box_intact_types = [_Proxy])
		boxargs['_idprocs']          = []

		ifcopy  = kwargs.get('copy', True)
		depends = kwargs.get('depends', True)

		for i, proc in enumerate(procs):
			assert isinstance(proc, Proc), 'Argument has to be a Proc object: %r.' % proc
			boxargs['_idprocs'].append(proc.id)
			if ifcopy:
				boxargs[proc.id] = proc.copy(proc.id,
					tag = (boxargs['tag'] or proc.tag.split('@', 1)[0]) + '@' + boxargs['id']
				)
			else:
				proc.tag = (boxargs['tag'] or proc.tag.split('@', 1)[0]) + '@' + boxargs['id']
				boxargs[proc.id] = proc
			boxargs[proc.id].aggr = boxargs['id']
			if depends and i > 0:
				boxargs[proc.id].depends = boxargs[boxargs['_idprocs'][i - 1]]

		if depends and boxargs['_idprocs']:
			boxargs['starts'] = _Proxy([boxargs[boxargs['_idprocs'][0]]])
			boxargs['ends']   = _Proxy([boxargs[boxargs['_idprocs'][-1]]])
		boxargs['groups']['starts'] = boxargs['starts']
		boxargs['groups']['ends']   = boxargs['ends']

		super(Aggr, self).__init__(boxargs.items(), ordered_box = True, box_intact_types = [_Proxy])

	def setGroup(self, name, *items):
		"""
		Set up groups
		@params:
			`name`: The name of the group. Once set, you can access it by:
				`aggr.<name>` or `aggr[<name>]`
			`*items`: The selectors of processes, which will be passed to `__getitem__`
		"""
		self.groups[name] = _Proxy(sum((self[item] for item in items), _Proxy()))

	# pylint: disable=arguments-differ,redefined-builtin,unused-argument,fixme
	# TODO: also copy depends relationship, then remove unsed-argument and fixme
	def copy (self, id = None, tag = None, depends = True, groups = True):
		"""
		Like `proc`'s `copy` function, copy an aggregation. Each processes will be copied.
		@params:
			`tag`    : The new tag of all copied processes
			`depends`: Whether to copy the dependencies or not. Default: True
				- dependences for processes in starts will not be copied
			`id`   : Use a different id if you don't want to use the variant name
			`grups`: Copy grups? Default: `True`
		@returns:
			The new aggregation
		"""
		id  = id or varname()
		ret = self.__class__(
			*[self[key] for key in self._idprocs], id = id, tag = tag, depends = False
		)
		for key in reversed(self._idprocs):
			ret[key].depends = [ret[proc.id] for proc in self[key].depends if proc.id in self]

		ret.starts.extend(ret[proc.id] for proc in self.starts)
		ret.ends.extend(ret[proc.id] for proc in self.ends)

		if groups:
			ret.groups.starts = ret.starts
			ret.groups.ends = ret.ends
			for group in self.groups.keys():
				if group in ('starts', 'ends'):
					continue
				ret.groups[group] = ret[self.groups[group]['id']]

		return ret

	def __setattr__(self, item, value):
		if item in ('starts', 'ends'):
			super(Aggr, self).__setattr__(item, _Proxy(value))
		elif item in ('depends', 'input'):
			self.starts.__setattr__(item, value)
		elif item in ('exdir', 'exhow', 'exow', 'expart'):
			self.ends.__setattr__(item, value)
		else:
			super(Aggr, self).__setattr__(item, value)

	def __getitem__(self, item, _ignore_default = True):
		if isinstance(item, slice):
			return _Proxy(self[itm] for itm in self._idprocs[item])
		if isinstance(item, int):
			return self[self._idprocs[item]]
		if isinstance(item, (tuple, list)):
			ret = _Proxy()
			for itm in item:
				ret.add(self[itm])
			return ret
		if item in self:
			return super(Aggr, self).__getitem__(item)
		if item in self.groups:
			return self.groups[item]
		keys = fnmatch.filter(self._idprocs, item)
		return _Proxy(self[key] for key in keys)
