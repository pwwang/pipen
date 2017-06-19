"""
A set of utitities for pyppl
"""
import logging

try:
	basestring = basestring
except NameError:
	basestring = str

try:
	reduce = reduce
except NameError:
	from functools import reduce


class PyPPLLogFormatter (logging.Formatter):
	"""
	logging formatter for pyppl
	"""

	formatter        = "[%(asctime)s]%(message)s"
	"""
	PyPPL log formatter
	"""
	color_black       = '\033[0;30m'
	color_red         = '\033[0;31m'
	color_green       = '\033[0;32m'
	color_orange      = '\033[0;33m'
	color_blue        = '\033[0;34m'
	color_purple      = '\033[0;35m'
	color_cyan        = '\033[0;36m'
	color_lightgray   = '\033[0;37m'
	color_darkgray    = '\033[1;30m'
	color_lightred    = '\033[1;31m'
	color_lightgreen  = '\033[1;32m'
	color_yellow      = '\033[1;33m'
	color_lightblue   = '\033[1;34m'
	color_lightpurple = '\033[1;35m'
	color_lightcyan   = '\033[1;36m'
	color_white       = '\033[1;37m'
	color_clear       = '\033[0m'
	
	def __init__(self, fmt=None):
		if fmt is None: fmt = self.formatter
		logging.Formatter.__init__(self, fmt, "%Y-%m-%d %H:%M:%S")
	
	def format(self, record):
		level       = record.levelno
		if level    == logging.DEBUG:
			level   = 'DEBUG'
		elif level  == logging.INFO:
			level   = 'INFO'
		elif level  == logging.WARNING:
			level   = 'WARNING'
		elif level  == logging.ERROR:
			level   = 'ERROR'
		if record.msg.startswith ("[") and "]" in record.msg:
			level   = record.msg[1:].split(']')[0].strip()
		
		if level == 'DONE':
			record.msg = "[%s%7s%s]%s%s%s" % (PyPPLLogFormatter.color_lightgreen, level, PyPPLLogFormatter.color_clear, PyPPLLogFormatter.color_lightgreen, record.msg[9:], PyPPLLogFormatter.color_clear)
		elif level == 'DEBUG':
			record.msg = "[%s%7s%s]%s%s%s" % (PyPPLLogFormatter.color_darkgray, level, PyPPLLogFormatter.color_clear, PyPPLLogFormatter.color_darkgray, record.msg[9:], PyPPLLogFormatter.color_clear)
		elif level in ['INFO', 'P.PROPS', 'DEPENDS', 'OUTPUT', 'EXPORT']:
			record.msg = "[%s%7s%s]%s%s%s" % (PyPPLLogFormatter.color_green, level, PyPPLLogFormatter.color_clear, PyPPLLogFormatter.color_green, record.msg[9:], PyPPLLogFormatter.color_clear)
		elif level == 'START':
			record.msg = "[%s%7s%s]%s%s%s" % (PyPPLLogFormatter.color_lightcyan, level, PyPPLLogFormatter.color_clear, PyPPLLogFormatter.color_lightcyan, record.msg[9:], PyPPLLogFormatter.color_clear)
		elif level in ['INPUT', 'P.ARGS', 'BRINGS']:
			record.msg = "[%s%7s%s]%s%s%s" % (PyPPLLogFormatter.color_green, level, PyPPLLogFormatter.color_clear, PyPPLLogFormatter.color_green, record.msg[9:], PyPPLLogFormatter.color_clear)
		elif level in ['ERROR', 'STDERR']:
			record.msg = "[%s%7s%s]%s%s%s" % (PyPPLLogFormatter.color_red, level, PyPPLLogFormatter.color_clear, PyPPLLogFormatter.color_red, record.msg[9:], PyPPLLogFormatter.color_clear)
		elif level == 'WARNING':
			record.msg = "[%s%7s%s]%s%s%s" % (PyPPLLogFormatter.color_yellow, level, PyPPLLogFormatter.color_clear, PyPPLLogFormatter.color_yellow, record.msg[9:], PyPPLLogFormatter.color_clear)
		elif level in ['CACHED', 'RUNNING']:
			record.msg = "[%s%7s%s]%s%s%s" % (PyPPLLogFormatter.color_orange, level, PyPPLLogFormatter.color_clear, PyPPLLogFormatter.color_orange, record.msg[9:], PyPPLLogFormatter.color_clear)
		
		return logging.Formatter.format(self, record)

def getLogger (level = 'info', name='PyPPL', colored=True):
	"""
	Get the default logger
	@params:
		`level`: The log level, default: info
		`name`:  The name of the logger, default: PyPPL
	@returns:
		The logger
	"""
	ch = logging.StreamHandler()
	ch.setFormatter (PyPPLLogFormatter() if colored else logging.Formatter(PyPPLLogFormatter.formatter, "%Y-%m-%d %H:%M:%S"))
	logger = logging.getLogger (name)
	logger.setLevel (getattr(logging, level.upper()))
	#if ch not in logger.handlers:
	logger.addHandler (ch)
	return logger

def varname (func, maxline = 20):
	"""
	Get the variable name inside the function or class __init__
	@params
		`func`: the name of the function. Use self.__class__.__name__ for __init__, func.__name__ for functions
		`maxline`: max no. of lines to retrieve if it cannot be retrived in current line (i.e. line breaks between arguments)
		**Note:** use less number to avoid:
		```python
			a = func ()
			...
			func ()
		```
		No variable used in second call, but if maxline to large, it will be wrongly report varable name as `a`
	@examples:
		```python
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
				print varname (r'\\w+\\.' + self.method.__name__, 0)
		```
	@returns:
		The variable name
	"""
	import re
	import inspect
	frame   = inspect.currentframe()
	frames  = inspect.getouterframes(frame)
	frame   = frames[2]
	src     = ''.join(frame[4])

	fn      = frame[1]
	lino    = frame[2]
	#            ;         ab             =    pyppl.proc (
	varpat  = r'(^|[^\w])([A-Za-z_]\w*)\s*=\s*([A-Za-z_][\w_]+\.)*%s\s*\(' % func
	#            ;         pyppl.proc (
	funcpat = r'(^|[^\w])([A-Za-z_][\w_]+\.)*%s\s*\(' % func
	m       = re.search(varpat, src)
	if m: 
		return m.group(2)
	varname.index += 1
	suffix  = str(varname.index)
	thefunc = func if not '\\.' in func else func.split('\\.')[1]
	m       = re.search(funcpat, src)
	if m: 
		return thefunc + '_' + suffix
	
	lines   = open(fn).readlines()[max(0, lino-maxline-1):lino-1]
	for line in reversed(lines):
		m   = re.search(varpat, line)
		if m: 
			return m.group(2)
		m   = re.search(funcpat, line)
		if m: 
			return thefunc + '_' + suffix
	
	return thefunc + '_' + suffix
varname.index = 0

def randstr (length = 8):
	"""
	Generate a random string
	@params:
		`length`: the length of the string, default: 8
	@returns:
		The random string
	"""
	import random
	return ''.join([random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijkllmnopqrstuvwxyz1234567890") for _ in range(length)])

def split (s, delimter):
	"""
	Split a string using a single-character delimter
	@params:
		`s`: the string
		`delimter`: the single-character delimter
	@examples:
		```python
		ret = split("'a,b',c", ",")
		# ret == ["'a,b'", "c"]
		# ',' inside quotes will be recognized.
		```
	@returns:
		The list of substrings
	"""
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
	"""
	Format a string with placeholders
	@params:
		`tpl`:  The string with placeholders
		`args`: The data for the placeholders
	@returns:
		The formatted string
	"""
	import re
	from sys import stderr
	s = tpl
	m = re.findall ("{{.+?}}", s)
	
	for n in m:
		nneat = n.strip("{}")
		parts = split(nneat, "|")
		key   = parts.pop(0).strip()
		if not key in args:
			stderr.write ("[KEY]      ->" + str(key) + "\n")
			stderr.write ("[DATA]     ->" + str(args) + "\n")
			stderr.write ("[TEMPLATE] ->\n")
			stderr.write (tpl + "\n")
			stderr.write ("-" * 80 + "\n")
			raise KeyError ("No key found in the data!")
		
		value = args[key]
		while parts:
			func = parts.pop(0).strip()
			val2replace = ("'%s'" % value) if isinstance(value, basestring) else ("%s" % value)
			func = re.sub(r"(?<=\(|\s|,)_(?=\)|,|\s)", val2replace, func, 1)
			
			if func.startswith(".") or func.startswith("["):
				value = eval ('%s%s' % (val2replace, func))
			elif func.startswith ('lambda'):
				value = eval ('(%s)(%s)' % (func, val2replace))
			elif func in format.shorts:
				value = eval ('(%s)(%s)' % (format.shorts[func], val2replace))
			else:
				value = eval (func)

		s     = s.replace (n, str(value))
	return s

format.shorts = {
	# convert python bool to R bool
	'Rbool':     "lambda x: str(bool(x)).upper()",
	'realpath':  "lambda x: __import__('os').path.realpath (x)",
	'readlink':  "lambda x: __import__('os').readlink (x)",
	'dirname':   "lambda x: __import__('os').path.dirname (x)",
	'basename':  "lambda x: __import__('os').path.basename (x)",
	'bn':        "lambda x: __import__('os').path.basename (x)",
	# /a/b/c.txt => c
	'filename':  "lambda x: __import__('os').path.splitext (__import__('os').path.basename(x))[0]",
	'fn':        "lambda x: __import__('os').path.splitext (__import__('os').path.basename(x))[0]",
	# /a/b/c.txt => .txt
	'ext':       "lambda x: __import__('os').path.splitext (__import__('os').path.basename(x))[1]",
	# /a/b/c.d.txt => c
	'fnnodot':   "lambda x: __import__('os').path.basename (x).split('.')[0]",
	# /a/b/c.txt => /a/b/c
	'prefix':    "lambda x: __import__('os').path.splitext (x)[0]",
	# /a/b/c.d.txt => /a/b/c
	'pxnodot':   "lambda x: __import__('os').path.join (__import__('os').path.dirname(x), __import__('os').path.basename (x).split('.')[0])",
	# array-space quote
	'asquote':   "lambda x: '\"' + '\" \"'.join(x) + '\"'",
	# array-comma quote
	'acquote':   "lambda x: '\"' + '\",\"'.join(x) + '\"'",
	'quote':     "lambda x: '\"%s\"' % str(x)",
	'squote':    "lambda x: \"'%s'\" % str(x)"
}

def dictUpdate(origDict, newDict):
	"""
	Update a dictionary recursively. 
	@params:
		`origDict`: The original dictionary
		`newDict`:  The new dictionary
	@examples:
		```python
		od1 = {"a": {"b": {"c": 1, "d":1}}}
		od2 = {key:value for key:value in od1.items()}
		nd  = {"a": {"b": {"d": 2}}}
		od1.update(nd)
		# od1 == {"a": {"b": {"d": 2}}}, od1["a"]["b"] is lost
		dictUpdate(od2, nd)
		# od2 == {"a": {"b": {"c": 1, "d": 2}}}
		```
	"""
	for k, v in newDict.items():
		if not isinstance(v, dict) or not k in origDict or not isinstance(origDict[k], dict):
			origDict[k] = newDict[k]
		else:
			dictUpdate(origDict[k], newDict[k])
			
def funcsig (func):
	"""
	Get the signature of a function
	Try to get the source first, if failed, try to get its name, otherwise return None
	@params:
		`func`: The function
	@returns:
		The signature
	"""
	if callable (func):
		try:
			from inspect import getsource
			sig = getsource(func)
		except Exception:
			sig = func.__name__
	else:
		sig = 'None'
	return sig

def uid(s, l = 8, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'):
	"""
	Calculate a short uid based on a string.
	Safe enough, tested on 1000000 32-char strings, no repeated uid found.
	This is used to calcuate a uid for a process
	@params:
		`s`: the base string
		`l`: the length of the uid
		`alphabet`: the charset used to generate the uid
	@returns:
		The uid
	"""
	from hashlib import md5
	s = md5(s).hexdigest()
	number = int (s, 16)
	base = ''

	while number != 0:
		number, i = divmod(number, len(alphabet))
		base = alphabet[i] + base

	return base[:l]

def targz (tgzfile, srcdir):
	"""
	Do a "tar zcf"-like for a directory
	@params:
		`tgzfile`: the final .tgz file
		`srcdir`:  the source directory
	"""
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
	"""
	Do a "tar zxf"-like for .tgz file
	@params:
		`tfile`:  the .tgz file
		`dstdir`: which directory to extract the file to
	"""
	import tarfile
	tar = tarfile.open (tfile, 'r:gz')
	tar.extractall (dstdir)
	tar.close()
	
def gz (gzfile, srcfile):
	"""
	Do a "gzip"-like for a file
	@params:
		`gzfile`:  the final .gz file
		`srcfile`: the source file
	"""
	from gzip import open as gzopen
	from shutil import copyfileobj
	fin  = open (srcfile, 'rb')
	fout = gzopen (gzfile, 'wb')
	copyfileobj (fin, fout)
	fin.close()
	fout.close()
	
def ungz (gzfile, dstfile):
	"""
	Do a "gunzip"-like for a .gz file
	@params:
		`gzfile`:  the .gz file
		`dstfile`: the extracted file
	"""
	from gzip import open as gzopen
	from shutil import copyfileobj
	fin  = gzopen (gzfile, 'rb')
	fout = open (dstfile, 'wb')
	copyfileobj (fin, fout)
	fin.close()
	fout.close()

def dirmtime (d):
	"""
	Calculate the mtime for a directory.
	Should be the max mtime of all files in it.
	@params:
		`d`:  the directory
	@returns:
		The mtime.
	"""
	from os.path import getmtime, join, exists
	from os import walk
	mtime = 0
	for root, dirs, files in walk(d):
		m = getmtime (root) if exists(root) else 0
		if m > mtime: 
			mtime = m
		for dr in dirs:
			m = dirmtime (join (root, dr))
			if m > mtime: 
				mtime = m
		for f in files:
			m = getmtime (join (root, f)) if exists(join(root, f)) else False
			if m > mtime: 
				mtime = m
	return mtime


def filesig (fn):
	"""
	Calculate a signature for a file according to its path and mtime
	@params:
		`fn`: the file
	@returns:
		The md5 deigested signature.
	"""
	from os.path import realpath, abspath, getmtime, isdir, exists
	fname = abspath(realpath(fn))
	if not exists (fname): 
		return False
	mtime = dirmtime(fname) if isdir (fname) else getmtime(fname)
	# not using fname, because we intend to allow links to replace the original file
	# say in case of export using move
	if not mtime: 
		return False
	return fn + '@' + str(mtime)

def alwaysList (data):
	"""
	Convert a string or a list with element 
	@params:
		`data`: the data to be converted
	@examples:
		```python
		data = ["a, b, c", "d"]
		ret  = alwaysList (data)
		# ret == ["a", "b", "c", "d"]
		```
	@returns:
		The split list
	"""
	if isinstance(data, basestring):
		ret = split (data, ',')
	elif isinstance(data, list):
		ret = []
		for d in data:
			if ',' in d: 
				ret += split(d, ',')
			else: 
				ret.append (d)
	else:
		raise ValueError('Expect string or list to convert to list.')
	return [x.strip() for x in ret]

def chmodX (thefile):
	"""
	Convert script file to executable or add extract shebang to cmd line
	@params:
		`thefile`: the script file
	@returns:
		A list with or without the path of the interpreter as the first element and the script file as the last element
	"""
	import os
	import stat
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

def padBoth (s, length, left, right = None):
	"""
	Pad at left and right sides of a string with different strings
	@params:
		`s`:      The string to be padded
		`length`: The total length of the final string
		`left`:   The string to be added on the left side
		`right`:  The string to be added on the right side.
		        If it is None, will be the same as `left`. 
	@returns:
		The logger
	"""
	if right is None: 
		right = left
	padlen = length - len (s)
	if padlen%2 == 1:
		llen = int((padlen - 1)/2)
		rlen = int((padlen + 1)/2)
	else:
		llen = rlen = int(padlen/2)
	lstr = (left * int(llen/len (left)))[:llen]
	rstr = (right * int(rlen/len(right)))[:rlen]
	return lstr + s + rstr

def formatTime (seconds):
	"""
	Format a time duration
	@params:
		`seconds`: the time duration in seconds
	@returns:
		The formated string.
		For example: "01:01:01.001" stands for 1 hour 1 min 1 sec and 1 minisec.
	"""
	m, s = divmod(seconds, 60)
	h, m = divmod(m, 60)
	return "%02d:%02d:%02d.%03d" % (h, m, s, 1000*(s-int(s)))

def isSamefile (f1, f2):
	"""
	Tell whether two paths pointing to the same file
	@params:
		`f1`: the first path
		`f2`: the second path
	@returns:
		True if yes, otherwise False
		If any of the path does not exist, return False
	"""
	from os import path
	if not path.exists (f1) or not path.exists(f2):
		return False
	return path.samefile (f1, f2)
	
def range2list (r):
	"""
	Convert a range to list, because in python3, range is not a list
	@params:
		`r`: the range data
	@returns:
		The converted list
	"""
	try:
		if isinstance (r, range):
			r = list(r)
	except TypeError:
		pass
	return r
