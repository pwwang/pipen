"""
A set of utitities for PyPPL
"""
import inspect
import re
from hashlib import md5
from .box import Box
from six import moves, string_types

def asStr(s, encoding = 'utf-8'):
	"""
	Convert everything (str, unicode, bytes) to str with python2, python3 compatiblity
	"""
	try: # pragma: no cover
		# python2
		unicode
		return s.encode(encoding) if isinstance(s, unicode) else str(s)
	except NameError: # pragma: no cover
		# python3
		return s.decode(encoding) if isinstance(s, bytes) else str(s)

def varname (maxline = 20, incldot = False):
	"""
	Get the variable name for ini
	@params:
		`maxline`: The max number of lines to retrive. Default: 20
		`incldot`: Whether include dot in the variable name. Default: False
	@returns:
		The variable name
	"""
	stack     = inspect.stack()

	if 'self' in stack[1][0].f_locals:
		theclass  = stack[1][0].f_locals["self"].__class__.__name__
		themethod = stack[1][0].f_code.co_name
	else:
		theclass  = stack[1][0].f_code.co_name
		themethod = ''

	srcfile   = stack[2][1]
	srclineno = stack[2][2]
	try:
		with open(srcfile) as f:
			srcs   = list(reversed(f.readlines()[max(0, srclineno-maxline): srclineno]))

		re_var = r'([A-Za-z_][\w.]*)' if incldot else r'([A-Za-z_]\w*)'
		if themethod and themethod != '__init__':
			#            var =     pp          .copy    (
			re_hit  = r'%s\s*=\s*([A-Za-z_]\w*\.)+%s\s*\(' % (re_var, themethod)
			#           pp.copy    (
			re_stop = r'([A-Za-z_]\w*\.)+%s\s*\(' % themethod
		else:
			#           var  =
			re_hit  = r'%s\s*=\s*([A-Za-z_]\w*\.)*%s\s*\(' % (re_var, theclass)
			re_stop = r'([A-Za-z_]\w*\.)*%s\s*\(' % theclass

		for src in srcs:
			hitgroup = re.search(re_hit, src)
			if hitgroup: return hitgroup.group(1)
			stopgroup = re.search(re_stop, src)
			if stopgroup: break
		
		varname.index += 1
		return 'var_%s' % (varname.index - 1)

	except Exception: # pragma: no cover
		varname.index += 1
		return 'var_%s' % (varname.index - 1)

varname.index = 0

def reduce(func, vec):
	"""
	Python2 and Python3 compatible reduce
	@params:
		`func`: The reduce function
		`vec`: The list to be reduced
	@returns:
		The reduced value
	"""
	return moves.reduce(func, vec)

def map(func, vec):
	"""
	Python2 and Python3 compatible map
	@params:
		`func`: The map function
		`vec`: The list to be maped
	@returns:
		The maped list
	"""
	return list(moves.map(func, vec))

def filter(func, vec):
	"""
	Python2 and Python3 compatible filter
	@params:
		`func`: The filter function
		`vec`:  The list to be filtered
	@returns:
		The filtered list
	"""
	return list(moves.filter(func, vec))

def range (i, *args, **kwargs):
	"""
	Convert a range to list, because in python3, range is not a list
	@params:
		`r`: the range data
	@returns:
		The converted list
	"""
	return list(moves.range(i, *args, **kwargs))

def split (s, delimter, trim = True):
	"""
	Split a string using a single-character delimter
	@params:
		`s`: the string
		`delimter`: the single-character delimter
		`trim`: whether to trim each part. Default: True
	@examples:
		```python
		ret = split("'a,b',c", ",")
		# ret == ["'a,b'", "c"]
		# ',' inside quotes will be recognized.
		```
	@returns:
		The list of substrings
	"""
	ret   = []
	special1 = ['(', ')', '[', ']', '{', '}']
	special2 = ['\'', '"']
	special3 = '\\'
	flags1   = [0, 0, 0]
	flags2   = [False, False]
	flags3   = False
	start = 0
	for i, c in enumerate(s):
		if c == special3:
			flags3 = not flags3
		elif not flags3:
			if c in special1:
				index = special1.index(c)
				if index % 2 == 0:
					flags1[int(index/2)] += 1
				else:
					flags1[int(index/2)] -= 1
			elif c in special2:
				index = special2.index(c)
				flags2[index] = not flags2[index]
			elif c == delimter and not any(flags1) and not any(flags2):
				r = s[start:i]
				if trim: r = r.strip()
				ret.append(r)
				start = i + 1
		else:
			flags3 = False
	r = s[start:]
	if trim: r = r.strip()
	ret.append(r)
	return ret

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

		if isinstance(v, list):
			origDict[k] = [e for e in v]
		elif k in origDict and isinstance(origDict[k], dict) and isinstance(v, dict):
			dictUpdate(origDict[k], newDict[k])
		else:
			origDict[k] = newDict[k]

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
		except Exception: # pragma: no cover
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
	s = md5(str(s).encode('utf-8')).hexdigest()
	number = int (s, 16)
	base = ''

	while number != 0:
		number, i = divmod(number, len(alphabet))
		base = alphabet[i] + base

	return base[:l]

def formatSecs (seconds):
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
	return "%02d:%02d:%02d.%03.0f" % (h, m, s, 1000*(s-int(s)))

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
	if isinstance(data, string_types):
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

def briefList(l):
	"""
	Briefly show an integer list, combine the continuous numbers.
	@params:
		`l`: The list
	@returns:
		The string to show for the briefed list.
	"""
	if len(l) == 0: return "[]"
	if len(l) == 1: return str(l[0])
	l       = sorted(l)
	groups  = [[]]
	ret     = []
	for i in range(0, len(l) - 1):
		e0 = l[i]
		e1 = l[i + 1]
		if e1 - e0 > 1:
			groups[-1].append(e0)
			groups.append([])
		else:
			groups[-1].append(e0)
	groups[-1].append(l[-1])
	for group in groups:
		if len(group) == 1:
			ret.append(str(group[0]))
		elif len(group) == 2:
			ret.append(str(group[0]))
			ret.append(str(group[1]))
		else:
			ret.append(str(group[0]) + '-' + str(group[-1]))
	return ', '.join(ret)
