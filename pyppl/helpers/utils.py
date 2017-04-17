
"""
Get the variable name inside the function or class __init__
@params
	func: the name of the function. Use self.__class__.__name__ for __init__, func.__name__ for functions
	maxline: max no. of lines to retrieve if it cannot be retrived in current line (i.e. line breaks between arguments)
	- Note: use less number to avoid:
	```
		a = func ()
		...
		func ()
	```
	No variable used in second call, but if maxline to large, it will be wrongly report varable name as `a`
@examples:
	```
	def func (a, b):
		print varname (func.__name__)
	funcVar = func(1,2) # prints funcVar
	funcVar2 = func (1,
	2)   # prints funcVar2
	func(3,3) # also prints funcVar2, as it retrieve 10 lines above this line!
	
	def func2 ():
		print varname(func.__name__, 0) # no args, don't retrive
	funcVar3 = func2() # prints funcVar3
	func2() # prints func2_xxxxxxxx, don't retrieve
	
	class stuff (object):
		def __init__ (self):
			print varname (self.__class__.__name__)
		
		def method (self):
			print varname ('\w+\.' + self.method.__name__, 0)
	```
"""
def varname (func, maxline = 20):
	import re, inspect
	frame   = inspect.currentframe()
	frames  = inspect.getouterframes(frame)
	frame   = frames[2]
	src     = ''.join(frame[4])

	file    = frame[1]
	lino    = frame[2]
	varpat  = r'(^|[^\w])([A-Za-z]\w*)\s*=\s*%s\s*\(' % func
	funcpat = r'(^|[^\w])%s\s*\(' % func
	
	m       = re.search(varpat, src)
	if m: return m.group(2)
	suffix  = randstr(8)
	thefunc = func if not '\\.' in func else func.split('\\.')[1]
	m       = re.search(funcpat, src)
	if m: return thefunc + '_' + suffix
	
	lines   = open(file).readlines()[max(0, lino-maxline-1):lino-1]
	for line in reversed(lines):
		m   = re.search(varpat, line)
		if m: return m.group(2)
		m   = re.search(funcpat, line)
		if m: return thefunc + '_' + suffix
	
	return thefunc + '_' + suffix

def randstr (length = 8):
	import random
	return ''.join([random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijkllmnopqrstuvwxyz1234567890") for _ in range(length)])

def split (s, delimter):
	ret = []
	wrap1 = 0 # (
	wrap2 = 0 # [
	wrap3 = 0 # {
	wrap4 = 0 # '
	wrap5 = 0 # "
	slash = 0 # \
	start = 0
	for i, c in enumerate(s):
		if c == '\\': 
			slash += 1
		elif c == '(':
			if slash % 2 == 0:
				wrap1 += 1
				slash = 0
		elif c == '[':
			if slash % 2 == 0:
				wrap2 += 1
				slash = 0
		elif c == '{':
			if slash % 2 == 0:
				wrap3 += 1
				slash = 0
		elif c == '\'':
			if slash % 2 == 0:
				wrap4 += 1
				slash = 0
		elif c == '"':
			if slash % 2 == 0:
				wrap5 += 1
				slash = 0
		elif c == ')':
			if slash % 2 == 0:
				wrap1 -= 1
				slash = 0
		elif c == ']':
			if slash % 2 == 0:
				wrap2 -= 1
				slash = 0
		elif c == '}':
			if slash % 2 == 0:
				wrap3 -= 1
				slash = 0
		elif c == delimter:
			if slash % 2 == 0 and wrap1 == 0 and wrap2 == 0 and wrap3 == 0 and wrap4 %2 == 0 and wrap5 % 2 == 0:
				ret.append (s[start:i].strip())
				start = i + 1
		else: 
			slash = 0
	ret.append (s[start:].strip())
	return ret

def format (tpl, args):
	import re
	s = tpl
	m = re.findall ("{{.+?}}", s)
	
	for n in m:
		nneat = n.strip("{}")
		parts = split(nneat, "|")
		key   = parts.pop(0).strip()
		value = args[key]

		while parts:
			func = parts.pop(0).strip()
			val2replace = ("'%s'" % value) if isinstance(value, basestring) else ("%s" % value)
			func = re.sub("(?<=\(|\s|,)_(?=\)|,|\s)", val2replace, func, 1)
			
			if func.startswith(".") or func.startswith("["):
				value = eval ('%s%s' % (val2replace, func))
			else:
				value = eval (func)

		s     = s.replace (n, str(value))
	return s

def dictUpdate(origDict, newDict):
	for k, v in newDict.iteritems():
		if not isinstance(v, dict) or not origDict.has_key(k) or not isinstance(origDict[k], dict):
			origDict[k] = newDict[k]
		else:
			dictUpdate(origDict[k], newDict[k])
			
def funcSig (func):
	if callable (func):
		try:
			from inspect import getsource
			sig = getsource(func)
		except:
			sig = func.__name__
	else:
		sig = 'None'
	return sig

# safe enough, tested on 1000000 32-char strings, no repeated uid found.
def uid(s, l = 8, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'):
	from hashlib import md5
	s = md5(s).hexdigest()
	number = int (s, 16)
	base = ''

	while number != 0:
		number, i = divmod(number, len(alphabet))
		base = alphabet[i] + base

	return base[:l]

def targz (tgzfile, srcdir):
	from tarfile import open as taropen
	from glob import glob
	from os import chdir, getcwd
	cwd = getcwd()
	tar = taropen(tgzfile, 'w:gz')
	chdir (srcdir)
	for name in glob ('./*'):
		tar.add(name)
	tar.close()
	chdir (cwd)
	
def untargz (tfile, dstdir):
	import tarfile
	tar = tarfile.open (tfile, 'r:gz')
	tar.extractall (dstdir)
	tar.close()
	
def gz (gzfile, srcfile):
	from gzip import open as gzopen
	from shutil import copyfileobj
	fin  = open (srcfile, 'rb')
	fout = gzopen (gzfile, 'wb')
	copyfileobj (fin, fout)
	
def ungz (gzfile, dstfile):
	from gzip import open as gzopen
	from shutil import copyfileobj
	fin  = gzopen (gzfile, 'rb')
	fout = open (dstfile, 'wb')
	copyfileobj (fin, fout)

def dirmtime (d):
	from os.path import getmtime, join
	from os import walk
	mtime = 0
	for root, dirs, files in walk(d):
		m = getmtime (root)
		if m > mtime: mtime = m
		for dr in dirs:
			m = dirmtime (join (root, dr))
			if m > mtime: mtime = m
		for f in files:
			m = getmtime (join (root, f))
			if m > mtime: mtime = m
	return mtime

# file signature, use absolute path and mtime
def fileSig (fn):
	from os.path import realpath, abspath, getmtime, isdir
	from hashlib import md5
	fn    = abspath(realpath(fn))
	mtime = dirmtime(fn) if isdir (fn) else getmtime(fn)

	return md5(fn + '@' + str(mtime)).hexdigest()

# convert str to list separated by ,
def alwaysList (data):
	if isinstance(data, (str, unicode)):
		ret = split (data, ',')
	elif isinstance(data, list):
		ret = []
		for d in data:
			if ',' in d: ret += split(d, ',')
			else: ret.append (d)
	else:
		raise ValueError('Expect string or list to convert to list.')
	return map (lambda x: x.strip(), ret)

# sanitize output key
def sanitizeOutKey (key):
	parts = split(key, ':')
	
	if len(parts) == 1:
		sanitizeOutKey.index += 1
		return ('__out.%s__' % sanitizeOutKey.index, 'var', key)
	
	if len(parts) == 2:
		if parts[0] in ['var', 'file', 'path', 'dir']:
			sanitizeOutKey.index += 1
			return ('__out.%s__' % sanitizeOutKey.index, parts[0], parts[1])
		else:
			return (parts[0], 'var', parts[1])
	
	if len(parts) == 3:
		if parts[1] not in ['var', 'file', 'path', 'dir']:
			raise ValueError ('Expect type: var, file or path instead of %s' % parts[1])
	else:
		raise ValueError ('You have extra colons in output key: %s' % key)
	
	return tuple (parts)
sanitizeOutKey.index = 0

# convert script file to executable or add extract shebang to cmd line
def chmodX (thefile):
	import os, stat
	thefile = os.path.realpath(thefile)
	ret = [thefile]
	try:
		st = os.stat (thefile)
		os.chmod (thefile, st.st_mode | stat.S_IEXEC)
	except Exception as e1:
		try:
			shebang = open (thefile).read().strip().split("\n")[0]
			if not shebang.startswith("#!"):
				raise Exception()
			ret = shebang[2:].strip().split() + [thefile]
		except Exception as e2:
			raise Exception("Cannot change %s as executable or read the shebang from it:\n%s\n%s" % (thefile, e1, e2))
	return ret

def getLogger (level = 'info', name='PyPPL'):
	import logging
	ch = logging.StreamHandler()
	ch.setFormatter (logging.Formatter("[%(asctime)-15s] %(message)s"))
	logger = logging.getLogger (name)
	logger.setLevel (getattr(logging, level.upper()))
	logger.addHandler (ch)
	return logger

def padBoth (s, length, left, right = None):
	if right is None: right = left
	padlen = length - len (s)
	if padlen%2 == 1:
		llen = (padlen - 1)/2
		rlen = (padlen + 1)/2
	else:
		llen = rlen = padlen/2
	lstr = (left * (llen/len (left)))[:llen]
	rstr = (right * (rlen/len(right)))[:rlen]
	return lstr + s + rstr