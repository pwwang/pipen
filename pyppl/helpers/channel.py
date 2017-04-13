from copy import copy as pycopy
import utils

class channel (list):
	
	@staticmethod
	def create (l = []):
		if l is None: l = []
		ret = channel()
		for e in l:
			ret.append (channel._tuplize(e))
		return ret

	@staticmethod
	def fromChannels (*args):
		ret = channel.create()
		ret.merge (*args)
		return ret
	
	@staticmethod
	# type = 'dir', 'file', 'link' or 'any'
	def fromPath (pattern, type = 'any'):
		from glob import glob
		ret = channel.create(sorted(glob(pattern)))
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
		ret  = channel.create()
		args = argv[1:]
		alen = len (args)
		if alen == 0: return ret
		
		width = None
		for arg in args:
			items = channel._tuplize(utils.split(arg, ','))
			if width is not None and width != len(items):
				raise ValueError('Width %s (%s) is not consistent with previous %s' % (len(items), arg, width))
			width = len(items)
			ret.append (items)
		return ret
	
	@staticmethod
	def _tuplize (tu):
		if isinstance(tu, (str, unicode)):
			tu = (tu, )
		else:
			try: iter(tu)
			except:	tu = (tu, )
		return tuple(tu)
	
	# expand the channel according to the files in <col>, other cols will keep the same
	# [(dir1/dir2, 1)].expand (0, "*") will expand to
	# [(dir1/dir2/file1, 1), (dir1/dir2/file2, 1), ...]
	# length: 1 -> N
	# width:  M -> M
	def expand (self, col = 0, pattern = "*"):
		from glob import glob
		import os
		folder = self[0][col]
		files  = glob (os.path.join(folder, pattern))
		
		tmp = list (self[0])
		for i, f in enumerate(files):
			n = pycopy(tmp)
			n [col] = f
			if i == 0:
				self[i] = tuple(n)
			else:
				self.append (tuple(n))
		return self
		
	# do the reverse of expand
	# length: N -> 1
	# width:  M -> M
	def collapse (self, col = 0):
		from os.path import dirname
		tmp = list (self[0])
		tmp[col] = dirname (tmp[col])
		self = channel.create([tuple(tmp)])
		return self
	
	def copy (self):
		return pycopy(self)

	def width (self):
		if not self: return 0
		ele = self[0]
		if not isinstance(ele, tuple): return 1
		return len(ele)
	
	def length (self):
		return len (self)

	def map (self, func):
		return channel.create(map(func, self))

	def filter (self, func):
		return channel.create(filter(func, self))

	def reduce (self, func):
		return channel.create(reduce(func, self))
	
	def rbind (self, row):
		row = channel._tuplize(row)
		if self.length() != 0 and self.width() != len(row):
			raise ValueError ('Cannot bind row (len: %s) to channel (width: %s): width is different.' % (len(row), self.width()))
		self.append (row)
		return self
	
	def rbindMany (self, *rows):
		for row in rows: self.rbind(row)
		return self
	
	def cbind (self, col):
		if not isinstance(col, list): col = [col]
		if len (col) == 1: col = col * max(1, self.length())
		if self.length() == 0 :
			for ele in col: self.append (channel._tuplize(ele))
		elif self.length() == len (col):
			for i in range (self.length()):
				self[i] += channel._tuplize(col[i])
		else:
			raise ValueError ('Cannot bind column (len: %s) to channel (length: %s): length is different.' % (len(col), self.length()))
		return self
	
	def cbindMany (self, *cols):
		for col in cols:
			self.cbind(col)
		return self
		
	def merge (self, *chans):
		for chan in chans:
			if not isinstance(chan, channel): chan = channel.create(chan)
			cols = [x.toList() for x in chan.split()]
			self.cbindMany (*cols)
		return self
	
	def colAt (self, index):
		return self.slice (index, 1)
	
	def slice (self, start, length = None):
		if start is None: start = self.width()
		if length is None: length = self.width()
		if start < 0: start = start + self.width()
		if start >= self.width(): return channel.create()
		ret = channel.create()
		if length == 0: return ret
		for ele in self:
			row = tuple (ele[start:start+length])
			ret.rbind (row)
		return ret
	
	def insert (self, index, col):
		if not isinstance(col, list): col = [col]
		if len (col) == 1: col = col * max(1, self.length())
		part1 = self.slice (0, index)
		part2 = self.slice (index)
		del self[:]
		self.merge (part1)
		self.cbind (col)
		self.merge (part2)
		return self
	
	def split (self):
		return [ self.colAt(i) for i in range(self.width()) ]
	
	def toList (self): # [(a,), (b,)] to [a, b], only applicable when width =1
		if self.width() != 1:
			raise ValueError ('Width = %s, but expect width = 1.' % self.width())
		
		return [ e[0] if isinstance(e, tuple) else e for e in self ]

	
  
