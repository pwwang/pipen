
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
	import re, random, inspect
	frame   = inspect.currentframe()
	frames  = inspect.getouterframes(frame)
	# frames[0] : this frame
	# frames[1] : the func/method calling this one
	# frames[2] : assignment
	frame   = frames[2]
	src     = ''.join(frame[4])

	file    = frame[1]
	lino    = frame[2]
	varpat  = r'(^|[^\w])([A-Za-z]\w*)\s*=\s*%s\s*\(' % func
	funcpat = r'(^|[^\w])%s\s*\(' % func
	
	m       = re.search(varpat, src)
	if m: return m.group(2)
	suffix  = ''.join([random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijkllmnopqrstuvwxyz1234567890") for _ in range(8)])
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
				ret.append (s[start:i])
				start = i + 1
		else: 
			slash = 0
	ret.append (s[start:])
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
