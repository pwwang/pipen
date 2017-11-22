"""
The aggregation of procs
"""
from collections import OrderedDict
from . import utils

class _Proxy(object):
	"""
	A proxy class to implement: 
	```
	a = Aggr()
	a.arg.tool = 'bedtools' <=>
	# for each process in a:
	p.arg.tool = 'bedtools'
	```
	"""
	def __init__(self, aggr, attr, sub):
		self.__dict__['_aggr'] = aggr
		self.__dict__['_attr'] = attr
		self.__dict__['_subs'] = [sub]

	def addsub(self, sub):
		self._subs.append(sub)
	
	def __setattr__(self, name, value):
		if name not in self._subs and not any([a.endswith('*') for a  in self._subs]):
			raise AttributeError('%s.%s is not delegated.' % (self._attr, name))
		setattr(self._aggr, self._attr + '.' + name, value)

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
		self.__dict__['_proxies']   = {}
		self.__dict__['_delegates'] = {}
		self.__dict__['_procs']     = OrderedDict()
		tag = utils.uid(self.id, 4) if 'tag' not in kwargs or not kwargs['tag'] else kwargs['tag']
		
		for proc in args:
			pid = proc.id
			if pid in ['starts', 'ends', 'id'] or pid in self.__dict__['_procs'] or hasattr(self, pid):
				raise AttributeError('%s is an attribute of Aggr, use a different process id.' % pid)
			newproc      = proc.copy(tag = tag, newid = pid)
			newproc.aggr = self.id
			self.__dict__['_procs'][pid] = newproc
		
		if 'depends' not in kwargs or kwargs['depends']:
			procs = list(self.__dict__['_procs'].values())
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
		if attr in self.__dict__['_props'] or attr in self.__dict__['_procs']:
			raise AttributeError('Cannot delegate process attribute to an existing Aggr attribute: %s.' % attr)

		if pattr is None: pattr = attr

		if '.' in attr:
			# can only do
			# a.delegate('a', None, 'b') or
			# a.delegate('a.b', None, 'b') or
			# a.delegate('a.b', None, 'b.c.d.e') or
			# a.delegate('a.*', None, 'b.*') or
			# a.delegate('a.*', None, 'b.c.*') or
			if attr.count('.') > 1: 
				raise AttributeError('Cannot delegate process attribute to a "2-dot" Aggr attribute: %s' % attr)
			# args.x
			attrname, attrsub = attr.split('.')
			if attrname in self.__dict__['_props'] or attrname in self.__dict__['_procs']:
				raise AttributeError('Cannot delegate process attribute to an existing Aggr attribute: %s.' % attrname)
			if pattr.endswith('.*') and attrsub != '*': 
				raise AttributeError('Cannot delegate multiple attributes to a single one.')
			
			if not attrname in self.__dict__['_proxies']:
				self.__dict__['_proxies'][attrname] = _Proxy(self, attrname, attrsub)
			else:
				self.__dict__['_proxies'][attrname].addsub(attrsub)

		elif pattr.endswith('.*'): 
			raise AttributeError('Cannot delegate multiple attributes to a single one.')

		self.__dict__['_delegates'][attr] = procs, pattr

	def __getattr__(self, name):
		if name not in self.__dict__['_props'] and   \
		   name not in self.__dict__['_proxies'] and \
		   name not in self.__dict__['_procs']:
			raise AttributeError('No such attribute: %s' % name)
		return self.__dict__['_props'][name]   if name in self.__dict__['_props'] else   \
			   self.__dict__['_proxies'][name] if name in self.__dict__['_proxies'] else \
			   self.__dict__['_procs'][name]

	def __setattr__(self, name, value):
		if name == 'id':
			self.__dict__['_props'][name] = value
		elif name in ['starts', 'ends']:
			self.__dict__['_props'][name] = list(value) if isinstance(value, tuple) or isinstance(value, list) else [value]
		elif name in self.__dict__:
			raise AttributeError('Attribute %s is not allowed to be modified.' % name)
		# no star
		elif name in self.__dict__['_delegates']:
			procs, attr = self.__dict__['_delegates'][name]
			if procs is None:
				procs = self.__dict__['_procs'].values()
			elif procs == 'starts':
				procs = self.starts
			elif procs == 'ends':
				procs = self.ends
			elif procs == 'both':
				procs = list(set(self.starts + self.ends))
			else:
				procs = [self.__dict__['_procs'][pid] for pid in utils.alwaysList(procs)]

			for i, proc in enumerate(procs):
				if name == 'depends2':
					if i < len(value): proc.depends = value[i]
				elif name == 'input':
					if i < len(value): proc.input   = value[i]
				elif '.' not in attr:
					setattr(proc, attr, value)
				else:
					parts = attr.split('.')
					newv  = {parts.pop(-1): value}
					oldv  = proc
					while parts:
						key  = parts.pop(0)
						oldv = getattr(oldv, key)
					utils.dictUpdate(oldv, newv)
		elif '.' in name and (name.split('.')[0] + ".*") in self.__dict__['_delegates']:
			procs, attr = self.__dict__['_delegates'][(name.split('.')[0] + ".*")]
			if procs is None:
				procs = self.__dict__['_procs'].values()
			elif procs == 'starts':
				procs = self.starts
			elif procs == 'ends':
				procs = self.ends
			elif procs == 'both':
				procs = list(set(self.starts + self.ends))
			else:
				procs = [self.__dict__['_procs'][pid] for pid in utils.alwaysList(procs)]

			attrs = attr.split('.')
			for i, proc in enumerate(procs):
				parts = attrs[:-1] + [name.split('.')[-1]]
				newv  = {parts.pop(-1): value}
				oldv  = proc
				while parts:
					key  = parts.pop(0)
					oldv = getattr(oldv, key)
				utils.dictUpdate(oldv, newv)
		else:
			for _, proc in self.__dict__['_procs'].items():
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
		if tag is not None:
			tag = utils.uid(self.id, 4) if not self.__dict__['_procs'] else list(self.__dict__['_procs'].values())[0].tag

		newproc = p.copy(tag = tag, newid = p.id) if copy else p
		newproc.aggr = self.id
		self.__dict__['_procs'][newproc.id] = newproc
		if where == 'starts' or where == 'both':
			self.starts.append (newproc)
		if where == 'ends' or where == 'both':
			self.ends.append (newproc)
		return self
		
	def copy (self, tag=None, deps=True, newid=None):
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
		name = utils.varname() if newid is None else newid
		tag  = utils.uid(name, 4) if not tag else tag
		ret  = Aggr (id = name)

		for k, v in self.__dict__['_delegates'].items():
			if k not in ret.__dict__['_delegates']:
				ret.delegate(k, *v)

		for _, proc in self.__dict__['_procs'].items():
			if tag == proc.tag:
				# This will happen to have procs with same id and tag
				raise ValueError('Tag "%s" is used by proc "%s" before, cannot copy with the same tag for aggregation: %s.' % (tag, proc.id, self.id))
			
			if proc not in self.starts and deps:
				for d in proc.depends:
					if d not in self.__dict__['_procs'].values():
						raise ValueError('Failed to copy "%s": a non-start proc ("%s") depends on a proc("%s") does not belong to "%s"' % (self.id, proc.name(), d.name(), self.id))
			newproc      = proc.copy (tag, proc.id)
			newproc.aggr = name

			
			where = 'both' if proc in self.starts and proc in self.ends \
				else 'starts' if proc in self.starts \
				else 'ends' if proc in self.ends \
				else None
			
			ret.addProc (newproc, tag = tag, where = where, copy = False)
		
		# copy dependences
		if deps:
			for _, proc in ret.__dict__['_procs'].items():
				if proc in ret.starts: continue
				proc.depends = [ret.__dict__['_procs'][p.id] for p in self.__dict__['_procs'][proc.id].depends]

		return ret
		