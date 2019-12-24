"""
Channel for pyppl
"""
import sys
import functools

from os import path
from glob import glob
from liquid import LiquidStream

# pylint: disable=invalid-name

class Channel(list): # pylint: disable=too-many-public-methods
	"""@API
	The channen class, extended from `list`
	"""

	@staticmethod
	def _tuplize(atuple):
		"""@API
		A private method, try to convert an element to tuple
		If it's a string, convert it to `(atuple, )`
		Else if it is iterable, convert it to `tuple(atuple)`
		Otherwise, convert it to `(atuple, )`
		Notice that string is also iterable.
		@params:
			atuple (str|list|tuple): the element to be converted
		@returns:
			(tuple): The converted element
		"""
		if isinstance(atuple, (str, list)):
			return (atuple, )

		try:
			iter(atuple)
		except TypeError:
			return (atuple, )
		return tuple(atuple)

	@staticmethod
	def create(alist = None):
		"""@API
		Create a Channel from a list
		@params:
			alist (list|Channel): The list, default: []
		@returns:
			(Channel): The Channel created from the list
		"""
		if alist is None:
			alist = []

		if not isinstance(alist, list):
			alist = [alist]

		ret = Channel()
		length = 0
		for ele in alist:
			row = Channel._tuplize(ele)
			if length == 0:
				length = len(row)
			if length != len(row):
				raise ValueError('Inconsistent width of row (%s) with previous row (%s)' %
					(len(row), length))
			ret.append (row)
		return ret

	@staticmethod
	def nones(length, width):
		"""@API
		Create a channel with `None`s
		@params:
			length (int): The length of the channel
			width (int):  The width of the channel
		@returns:
			(Channel): The created channel
		"""
		ret = Channel()
		row = (None, ) * width
		for _ in range(length):
			ret.append(row[:])
		return ret

	@staticmethod
	def fromChannels(*args):
		"""@API
		Create a Channel from Channels
		@params:
			*args (any): The Channels or anything can be created as a `Channel`
		@returns:
			(Channel): The Channel merged from other Channels
		"""
		ret = Channel.create()
		return ret.insert (None, *args)

	@staticmethod
	def fromPattern(pattern, ftype = 'any', sortby = 'name', reverse=False):
		"""@API
		Create a Channel from a path pattern
		@params:
			pattern (str): the pattern with wild cards
			ftype (str): the type of the files/dirs to include
			  - 'dir', 'file', 'link' or 'any' (default)
			sortby (str):  how the list is sorted
			  - 'name' (default), 'mtime', 'size'
			reverse (bool): reverse sort. Default: `False`
		@returns:
			(Channel): The Channel created from the path
		"""
		if sortby == 'name':
			key = str
		elif sortby == 'mtime':
			key = path.getmtime
		elif sortby == 'size':
			key = path.getsize

		filt  = lambda afile: True
		if ftype == 'link':
			filt = path.islink
		elif ftype == 'dir':
			filt = lambda afile: path.isdir(afile) and not path.islink(afile)
		elif ftype == 'file':
			filt = lambda afile: path.isfile(afile) and not path.islink(afile)
		files = [afile for afile in glob(str(pattern)) if filt(afile)]
		return Channel.create(sorted(files, key=key, reverse=reverse))

	@staticmethod
	def fromPairs(pattern):
		"""@API
		Create a width = 2 Channel from a pattern
		@params:
			pattern (str): the pattern
		@returns:
			(Channel): The Channel create from every 2 files match the pattern
		"""
		ret  = sorted(glob(pattern))
		chan = Channel.create()
		for i in range(0, len(ret), 2):
			chan.append ((ret[i], ret[i+1]))
		return chan

	@staticmethod
	def fromFile(filename, header = False, skip = 0, delimit = "\t"):
		"""@API
		Create Channel from the file content
		It's like a matrix file, each row is a row for a Channel.
		And each column is a column for a Channel.
		@params:
			filename (file): the file
			header (bool):  Whether the file contains header. If True, will attach the header
				- So you can use `channel.<header>` to fetch the column
			skip (int): first lines to skip, default: `0`
			delimit (str): the delimit for columns, default: `\t`
		@returns:
			(Channel): A Channel created from the file
		"""
		ret     = Channel.create()
		i       = -1
		headers = []
		with open(filename) as fhandler:
			for line in fhandler:
				i += 1
				if i < skip:
					continue
				line = line.rstrip("\n")
				if not line:
					continue
				if header:
					headers = line.split(delimit)
					header  = False
				else:
					ret.append (tuple(line.split(delimit)))
		if headers:
			lenheaders = len(headers)
			channelwid = ret.width()
			if lenheaders == channelwid - 1:
				headers.insert(0, 'RowNames')
			elif lenheaders != channelwid:
				raise ValueError('Number of headers and columns doesn\'t match: %s, %s.' %
					(lenheaders, channelwid))
			ret.attach(*headers)

		return ret

	@staticmethod
	def fromArgv():
		"""@API
		Create a Channel from `sys.argv[1:]`
		"python test.py a b c" creates a width=1 Channel
		"python test.py a,1 b,2 c,3" creates a width=2 Channel
		@returns:
			(Channel): The Channel created from the command line arguments
		"""
		ret  = Channel.create()
		args = sys.argv[1:]
		alen = len (args)
		if alen == 0:
			return ret

		width = None
		for arg in args:
			items = tuple(LiquidStream.from_string(arg).split(','))
			if width is not None and width != len(items):
				raise ValueError('Width %s (%s) is not consistent with previous %s' %
					(len(items), arg, width))
			width = len(items)
			ret.append (items)
		return ret

	@staticmethod
	def fromParams(*pnames):
		"""@API
		Create a Channel from params
		@params:
			*pnames (str): The names of the option
		@returns:
			(Channel): The Channel created from `pyparam`.
		"""
		from pyparam import params
		ret = Channel.create()
		width = None
		for pname in pnames:
			param = getattr(params, pname)
			data  = param.value
			if not param.type.startswith('list') or not isinstance(data, list):
				data = [param.value]
			if width is not None and width != len(data):
				raise ValueError('Width %s (%s) is not consistent with previous %s' %
					(len(data), data, width))
			width = len(data)
			ret = ret.cbind(data)
		if ret:
			ret.attach(*pnames)
		return ret

	# pylint: disable=too-many-arguments
	def expand(self, col = 0, pattern = "*", ftype = 'any', sortby = 'name', reverse = False):
		"""@API
		expand the Channel according to the files in <col>, other cols will keep the same
		`[(dir1/dir2, 1)].expand (0, "*")` will expand to
		`[(dir1/dir2/file1, 1), (dir1/dir2/file2, 1), ...]`
		length: 1 -> N
		width:  M -> M
		@params:
			col (int): the index of the column used to expand
			pattern (str): use a pattern to filter the files/dirs, default: `*`
			ftype (str): the type of the files/dirs to include
			  - 'dir', 'file', 'link' or 'any' (default)
			sortby (str):  how the list is sorted
			  - 'name' (default), 'mtime', 'size'
			reverse (bool): reverse sort. Default: False
		@returns:
			(Channel): The expanded Channel
		"""
		ret = Channel.create()
		if not self:
			return ret

		for row in self:
			row    = list(row)
			folder = row[col]
			files  = Channel.fromPattern(
				path.join(folder, pattern), ftype=ftype, sortby=sortby, reverse=reverse).flatten()
			for afile in files:
				row[col] = afile
				ret.append(tuple(row))
		return ret

	def collapse(self, col = 0):
		"""@API
		Do the reverse of expand
		length: N -> 1
		width:  M -> M
		@params:
			col (int):     the index of the column used to collapse
		@returns:
			(Channel): The collapsed Channel
		"""
		if not self:
			raise ValueError('Cannot collapse an empty Channel.')

		paths = self.colAt(col).flatten()
		compx = path.dirname(path.commonprefix(paths))
		row   = list(self[0])
		row[col] = compx
		return Channel.create(tuple(row))

	def copy(self):
		"""@API
		Copy a Channel using `copy.copy`
		@returns:
			(Channel): The copied Channel
		"""
		return self.slice(0)

	def width(self):
		"""@API
		Get the width of a Channel
		@returns:
			(int): The width of the Channel
		"""
		if not self:
			return 0
		return len(self[0]) if isinstance(self[0], tuple) else 1

	def length(self):
		"""@API
		Get the length of a Channel
		It's just an alias of `len(chan)`
		@returns:
			(int): The length of the Channel
		"""
		return len(self)

	def map(self, func):
		"""@API
		Alias of python builtin `map`
		@params:
			func (callable): the function
		@returns:
			(Channel): The transformed Channel
		"""
		return Channel.create([func(x) for x in self])

	def mapCol(self, func, col = 0):
		"""@API
		Map for a column
		@params:
			func (callable): the function
			col (int): the index of the column. Default: `0`
		@returns:
			(Channel): The transformed Channel
		"""
		return Channel.create([
			s[:col] + (func(s[col]), ) + s[(col+1):] for s in self
		])

	def filter (self, func = None):
		"""@API
		Alias of python builtin `filter`
		@params:
			func (callable): the function. Default: `None`
		@returns:
			(Channel): The filtered Channel
		"""
		func = func or bool
		return Channel.create([x for x in self if func(x)])

	def filterCol(self, func = None, col = 0):
		"""@API
		Just filter on the specific column
		@params:
			func (callable): the function
			col (int): the column to filter
		@returns:
			(Channel): The filtered Channel
		"""
		func = func or bool
		return Channel.create([s for s in self if func(s[col])])

	def reduce (self, func):
		"""@API
		Alias of python builtin `reduce`
		@params:
			func (callable): the function
		@returns:
			(Channel): The reduced value
		"""
		return functools.reduce(func, self)

	def reduceCol (self, func, col = 0):
		"""@API
		Reduce a column
		@params:
			func (callable): the function
			col (int): the column to reduce
		@returns:
			(Channel): The reduced value
		"""
		return functools.reduce(func, [s[col] for s in self])

	def rbind (self, *rows):
		"""@API
		The multiple-argument versoin of `rbind`
		@params:
			*rows (any): the rows to be bound to Channel
		@returns:
			(Channel): The combined Channel
		"""
		ret = self.copy()
		for row in rows:
			if not row:
				continue
			if not isinstance(row, Channel):
				row = Channel.create(row)
			if row.length() == 0 or row.width() == 0:
				continue

			if ret.length() == 0:
				ret = row
			elif row.width() == 1:
				ret.extend([rele * ret.width() for rele in row])
			elif ret.width() == 1:
				for i in range(ret.length()):
					ret[i] *= row.width()
				ret.extend(row)
			elif row.width() != ret.width():
				raise ValueError('Unable to rbind unequal width channels (%s, %s)' %
					(ret.width(), row.width()))
			else:
				ret.extend(row)
		return ret

	def insert (self, cidx, *cols):
		"""@API
		Insert columns to a channel
		@params:
			cidx (int): Insert into which index of column?
			*cols (any): the columns to be bound to Channel
		@returns:
			(Channel): The combined Channel
		"""
		ret  = self.copy()
		#cols = [col if isinstance(col, Channel) else Channel.create(col) for col in cols if col]
		# fix #29
		cols = [col if isinstance(col, Channel) else Channel.create(col) for col in cols]
		cols = [col for col in cols if col.width() > 0 and col.length() > 0]
		if not cols:
			return ret

		if cidx is None:
			colsbefore = ret
			colsafter  = []
		else:
			colsbefore = [s[:cidx] for s in ret]
			colsafter  = [s[cidx:] for s in ret]

		maxlen = max([col.length() for col in cols])
		maxlen = max(maxlen, len(ret))
		if ret.length() == 1:
			colsbefore *= maxlen
			colsafter  *= maxlen

		length = max(len(colsbefore), len(colsafter))
		for col in cols:
			# has been filtered with col.width() > 0
			#if col.width() == 0:
			#	continue
			if col.length() == 1:
				# oringal col has been changed
				#col *= maxlen
				col = col.repRow(maxlen)
			if length > 0 and length != col.length():
				raise ValueError(
					'Cannot bind column (length: %s) to Channel (length: %s).' % (
						col.length(), length
					))

			colsbefore = [colsbefore[i] + c for i, c in enumerate(col)] if colsbefore else col
			length = max(len(colsbefore), len(colsafter))

		return Channel([c + colsafter[i] for i, c in enumerate(colsbefore)]
			if colsafter else colsbefore)

	def cbind(self, *cols):
		"""@API
		Add columns to the channel
		@params:
			*cols (any): The columns
		@returns:
			(Channel): The channel with the columns inserted.
		"""
		return self.insert(None, *cols)

	def colAt (self, index):
		"""@API
		Fetch one column of a Channel
		@params:
			index (int): which column to fetch
		@returns:
			(Channel): The Channel with that column
		"""
		if not isinstance(index, list):
			index = [index]
		chs = []
		for idx in index:
			chs.append(self.slice (idx, 1))
		return Channel.fromChannels(*chs)

	def rowAt (self, index):
		"""@API
		Fetch one row of a Channel
		@params:
			index (int): which row to fetch
		@returns:
			(Channel): The Channel with that row
		"""
		if not isinstance(index, list):
			index = [index]
		rows = []
		for idx in index:
			rows.extend(self[idx:(idx+1 if idx!=-1 else None)])
		return Channel(rows)

	def unique(self):
		"""@API
		Make the channel unique, remove duplicated rows
		Try to keep the order
		@returns:
			(Channel): The channel with unique rows.
		"""
		rows = []
		for row in self:
			if row not in rows:
				rows.append(row)
		return Channel(rows)

	def slice (self, start, length = None):
		"""@API
		Fetch some columns of a Channel
		@params:
			start (int):  from column to start
			length (int): how many columns to fetch, default: None (from start to the end)
		@returns:
			(Channel): The Channel with fetched columns
		"""
		return Channel([s[start:(start + length)] for s in self]) \
				if length and start != -1 else Channel.create([s[start:] for s in self])

	def fold (self, nfold = 1):
		"""@API
		Fold a Channel. Make a row to n-length chunk rows
		```
		a1	a2	a3	a4
		b1	b2	b3	b4
		if nfold==2, fold(2) will change it to:
		a1	a2
		a3	a4
		b1	b2
		b3	b4
		```
		@params:
			nfold (int): the size of the chunk
		@returns
			(Channel): The new Channel
		"""
		if nfold <= 0 or self.width() % nfold != 0:
			raise ValueError ('Failed to fold, the width %s cannot be divided by %s' %
				(self.width(), nfold))

		nrows = int(self.width() / nfold)
		ret = []
		for row in self:
			for i in [x*nfold for x in range(nrows)]:
				ret.append (row[i:i+nfold])
		return Channel(ret)

	def unfold (self, nfold = 2):
		"""@API
		Do the reverse thing as self.fold does
		@params:
			nfold (int): How many rows to combind each time. default: 2
		@returns:
			(Channel): The unfolded Channel
		"""
		if nfold <= 0 or len(self) % nfold != 0:
			raise ValueError ('Failed to unfold, the length %s cannot be divided by %s' %
				(len(self), nfold))

		nrows = int(len(self) / nfold)
		ret = []
		for i in range(nrows):
			row = ()
			for j in range(nfold):
				row += self[i*nfold + j]
			ret.append(row)
		return Channel.create(ret)

	def split (self, flatten=False):
		"""@API
		Split a Channel to single-column Channels
		@returns:
			(list[Channel]): The list of single-column Channels
		"""
		return [ self.flatten(i) for i in range(self.width()) ] if flatten else \
			   [ self.colAt(i) for i in range(self.width()) ]

	def attach(self, *names, flatten = False):
		"""@API
		Attach columns to names of Channel, so we can access each column by:
		`ch.col0` == ch.colAt(0)
		@params:
			*names (str): The names. Have to be as length as channel's width.
				None of them should be Channel's property name
			flatten (bool): Whether flatten the channel for the name being attached
		"""
		mywidth = self.width()
		lnames  = len(names)
		if mywidth < lnames:
			raise ValueError(
				'More names (%s) to attach than the width (%s) of the channel.' %
				(lnames, mywidth))
		for i, name in enumerate(names):
			if hasattr(self, name) and \
				not isinstance(getattr(self, name), Channel) and \
				not isinstance(getattr(self, name), list):
				raise AttributeError(
					'Cannot attach column to "%s" as it is already an attribute of Channel.' %
					name)
			setattr(self, name, self.flatten(i) if flatten else self.colAt(i))

	def get(self, idx = 0):
		"""@API
		Get the element of a flattened channel
		@params:
			idx (int): The index of the element to get. Default: 0
		@return:
			(any): The element
		"""
		return self.flatten()[idx]

	def repCol(self, nrep = 2):
		"""@API
		Repeat column and return a new channel
		@params:
			nrep (int): how many times to repeat.
		@returns:
			(Channel): The new channel with repeated columns
		"""
		cols = [self] * (nrep - 1)
		return self.cbind(*cols)

	def repRow(self, nrep = 2):
		"""@API
		Repeat row and return a new channel
		@params:
			nrep (int): how many times to repeat.
		@returns:
			(Channel): The new channel with repeated rows
		"""
		rows = [self] * (nrep - 1)
		return self.rbind(*rows)

	def flatten (self, col = None):
		"""@API
		Convert a single-column Channel to a list (remove the tuple signs)
		`[(a,), (b,)]` to `[a, b]`
		@params:
			col (int): The column to flat. None for all columns (default)
		@returns:
			(list): The list converted from the Channel.
		"""
		return [item for sublist in self for item in sublist] if col is None else \
			   [sublist[col] for sublist in self]

	def transpose(self):
		"""@API
		Transpose the channel
		@returns:
			(Channel): The transposed channel.
		"""
		ret = Channel.nones(length = self.width(), width = self.length())
		ret = [list(row) for row in ret]
		for i, row in enumerate(self):
			for j, val in enumerate(row):
				ret[j][i] = val
		ret = [tuple(row) for row in ret]
		return Channel(ret)

	# We will try to deprecate the camelCase functions
	t             = transpose
	from_pattern  = fromPattern
	from_pairs    = fromPairs
	from_file     = fromFile
	from_argv     = fromArgv
	from_params   = fromParams
	from_channels = fromChannels
	map_col       = mapCol
	filter_col    = filterCol
	reduce_col    = reduceCol
	col_at        = colAt
	row_at        = rowAt
	rep_col       = repCol
	rep_row       = repRow
