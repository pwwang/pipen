
from channel import channel
import utils

class aggr (object):
	
	commprops = ['tmpdir', 'forks', 'cache', 'retcodes', 'echo', 'runner', 'errorhow', 'errorntry']
	
	# aggr (p1, p2, p3, ..., depends = True)
	def __init__ (self, *arg):
		self.starts    = []
		self.ends      = []
		self.id = utils.varname(self.__class__.__name__, 50)
		
		depends = True
		arg     = list(arg)
		if isinstance(arg[-1], bool):
			depends = arg.pop(-1)
		
		self.__dict__['procs'] = arg
		for i, proc in enumerate(self.procs):
			if proc.tag == 'notag':
				self.__dict__[proc.id] = proc
			self.__dict__[proc.id + '_' + proc.tag] = proc
			proc.aggr  = self.id
			if depends and i>0:
				proc.depends = self.procs[i-1]
			if i==0: self.starts.append (proc)
			if i==len(self.procs)-1: self.ends.append(proc)
		
	def __setattr__ (self, name, value):
		if name in aggr.commprops or name.endswith('Runner'):
			for proc in self.procs:
				proc.__setattr__(name, value)
		elif name == 'input':
			if not isinstance(value, channel):
				value  = channel.create(value)
			chans = value.split()
			i = 0
			for proc in self.starts: # only str and list allowed: "input1, input2" or ["input1", "input2"]
				inkey = proc.input
				if isinstance(inkey, list):
					inkey = ','.join (inkey)
				if not isinstance (inkey, str) and not isinstance(inkey, unicode):
					raise RuntimeError('Expect list or str for proc keys for aggregation: %s, you may have already set the input channels?' % (self.id))
				
				inkeys = map(lambda x: x.strip(), utils.split(inkey, ','))
				if len(inkeys) > len(chans) - i:
					raise RuntimeError('Not enough data column for aggregation "%s"\nKeys: %s\n#Col: %s' % (self.id, inkeys, (len(chans)-1)))
				proc.input = {}
				for inkey in inkeys:
					proc.input[inkey] = chans[i]
					i = i + 1
					
		elif name == 'depends':
			for proc in self.ends:
				proc.depends = value
		elif name.startswith ('export'):
			for proc in self.ends:
				proc.__setattr__(name, value)
		elif name in ['starts', 'ends', 'id']:
			self.__dict__[name] = value
		else:
			raise AttributeError('Cannot set property "%s" of aggregation "%s"' % (name, self.id))
		
	def copy (self, tag='aggr', newid=None):
		name   = utils.varname('\w\.'+self.copy.__name__, 2) if newid is None else newid
		
		args   = []
		fordeps= {}
		for proc in self.procs:
			if tag == proc.tag:
				raise ValueError('Tag "%s" is used by proc "%s" before, cannot copy with the same tag for aggregation: %s.' % (tag, proc.id, self.id))
			newproc = proc.copy (tag, proc.id)
			newproc.aggr = name
			args.append (newproc)
			key = proc.id + '_' + proc.tag
			fordeps[key] = newproc
			
		for proc in args:
			newdeps = []
			for dep in proc.depends:
				key = dep.id + '_' + dep.tag
				newdeps.append (fordeps[key])
			newproc.depends = newdeps
		args.append (False)
		ret    = aggr (*args)
		ret.id = name
		return ret
		
		
	

		