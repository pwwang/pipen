"""
The aggregation of procs
"""
import fnmatch
from box import Box
from collections import OrderedDict
from . import utils

class _Proxy(list):
	def __getattr__(self, item):
		if hasattr(super(_Proxy, self), item):
			return super(_Proxy, self).getattr(item)

		return self.__class__(getattr(x, item) for x in self)

	def __setattr__(self, name, value):
		if hasattr(super(_Proxy, self), name):
			return super(_Proxy, self).__setattr__(name, value)

		if isinstance(value, tuple):
			for i, val in enumerate(value):
				setattr(self[i], name, val)
		else:
			for x in self:
				setattr(x, name, value)

	def __getitem__(self, item):
		if isinstance(item, (int, slice)):
			return super(_Proxy, self).__getitem__(item)
		return self.__getattr__(item)

	def __setitem__(self, item, value):
		if isinstance(item, (int, slice)):
			return super(_Proxy, self).__setattr__(item, value)
		return self.__setattr__(item, value)

	def add(self, anything):
		if isinstance(anything, _Proxy):
			for at in anything:
				self.add(at)
		elif not anything in self:
			self.append(anything)

class Aggr(Box):

	def __init__(self, *procs, **kwargs):
		from . import Proc
		boxargs = OrderedDict()

		boxargs['id']               = kwargs.get('id') or utils.varname()
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
				boxargs[proc.id] = proc.copy(proc.id, tag = boxargs['tag'] or 
					proc.tag.split('@')[0] + '@' + boxargs['id'])
			else:
				proc.tag = boxargs['tag'] or proc.tag.split('@')[0] + '@' + boxargs['id']
				boxargs[proc.id] = proc
			if depends and i > 0:
				boxargs[proc.id].depends = boxargs[boxargs['_idprocs'][i - 1]]

		if depends and boxargs['_idprocs']:
			boxargs['starts'] = _Proxy([boxargs[boxargs['_idprocs'][0]]])
			boxargs['ends']   = _Proxy([boxargs[boxargs['_idprocs'][-1]]])
		boxargs['groups']['starts'] = boxargs['starts']
		boxargs['groups']['ends']   = boxargs['ends']

		super(Aggr, self).__init__(boxargs.items(), ordered_box = True, box_intact_types = [_Proxy])

	def setGroup(self, name, *items):
		self.groups[name] = _Proxy(sum((self[item] for item in items), _Proxy()))
	
	def copy (self, id = None, tag = None, depends = True, groups = True):
		id  = id or utils.varname()
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

	def __getitem__(self, item, _ignore_default = True):
		from . import Proc
		if isinstance(item, slice):
			return _Proxy(self[it] for it in self._idprocs[item])
		if isinstance(item, int):
			return self[self._idprocs[item]]
		if isinstance(item, (tuple, list)):
			ret = _Proxy()
			for it in item:
				ret.add(self[it])
			return ret
		if item in self:
			return super(Aggr, self).__getitem__(item)
		if item in self.groups:
			return self.groups[item]
		if item in self.groups:
			return self.groups[item]
		keys = fnmatch.filter(self._idprocs, item)
		return _Proxy(self[key] for key in keys)

