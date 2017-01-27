
class channel (list):
  
	@staticmethod
	def create (l = []):
		return channel(l)

	@staticmethod
	def fromChannels (*args):
		ret = channel.create()
		if not args:
			return ret
		ret.merge (*args)
		return ret
  
	@staticmethod
	# type = 'dir', 'file', 'link' or 'any'
	def fromPath (pattern, type = 'any'):
		from glob import glob
		ret = channel (glob(pattern))
		if type != 'any':
			from os import path
		if type == 'dir':
			return ret.filter (path.isdir)
		elif type == 'file':
			return ret.filter (path.isfile)
		elif type == 'link':
			return ret.filter (path.islink)
		return ret

	@staticmethod
	def fromPairs (pattern):
		from glob import glob
		ret = sorted(glob(pattern))
		c = channel.create()
		for i in range(0, len(ret), 2):
			c.append ((ret[i], ret[i+1]))
		return c

	@staticmethod
	def fromArgv ():
		from sys import argv
		return channel(argv[1:])
	
	@staticmethod
	def _tuplize (tu):
		if isinstance(tu, str):
			tu = (tu, )
		else:
			try:
				iter(tu)
			except:
				tu = (tu, )
		return tu

	def width (self):
		if not self:
			return 0
		ele = self[0]
		if not isinstance(ele, tuple):
			return 1
		return len(ele)
	
	def length (self):
		return len (self)

	def map (self, func):
		return channel(map(func, self))

	def filter (self, func):
		return channel(filter(func, self))

	def reduce (self, func):
		return channel(reduce(func, self))

	def merge (self, *args):
		if not args: return
		maxlen = max(map(len, args))
		minlen = min(map(len, args))
		if maxlen != minlen:
			raise Exception('Cannot merge channels with different length.')
		clen = len (self)
		if clen != 0 and clen != maxlen:
			raise Exception('Cannot merge channels with different length.')

		for i in range(maxlen):
			tu = () if clen==0 else channel._tuplize(self[i])
			for arg in args:
				tu += channel._tuplize (arg[i])
			if clen == 0:
				self.append(tu)
			else:
				self[i] = tu
	
	def mergeCopy (self, *args):
		ret = channel.create(self)
		ret.merge(*args)
		return ret
	
	def split (self):
		ret = []
		for i, tu in enumerate(self):
			if isinstance(tu, str):
				tu = (tu, )
			try:
				iter(tu)
			except:
				tu = (tu, )
			for t in tu:
				if i==0: ret.append(channel.create())
			for j, t in enumerate(tu):
				ret[j].append(t)
		return ret
			

	
  
