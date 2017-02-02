
class channel (list):
  
	@staticmethod
	def create (l = []):
		ret = channel()
		for e in l:
			ret.append (channel._tuplize(e))
		return ret

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
		ret = channel.create(glob(pattern))
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
	def fromArgv (width = 1):
		from sys import argv
		args = argv[1:]
		alen = len (args)
		if width == None: width = alen
		if alen % width != 0:
			raise Exception('Length (%s) of argv[1:] must be exactly divided by width (%s)' % (alen, width))
		
		ret = channel()
		for i in xrange(0, alen, width):
			tmp = ()
			for j in range(width):
				tmp += (args[i+j], )
			ret.append (tmp)
		return ret
	
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
		return channel.create(map(func, self))

	def filter (self, func):
		return channel.create(filter(func, self))

	def reduce (self, func):
		return channel.create(reduce(func, self))

	def merge (self, *args):
		if not args: return
		maxlen = max(map(len, args))
		minlen = min(map(len, args))
		if maxlen != minlen:
			raise Exception('Cannot merge channels with different length (%s, %s).' % (maxlen, minlen))
		clen = len (self)
		if clen != 0 and clen != maxlen:
			raise Exception('Cannot merge channels with different length (%s, %s).' % (maxlen, clen))

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
			if i == 0:
				for t in tu: ret.append(channel())

			for j, t in enumerate(tu):
				ret[j].append(channel._tuplize(t))
		return ret
			

	
  
