# A string template for python
# Same as .format but add function support for string interplolation
# Version: 0.0.1
# Author: pwwang@pwwang.com
# Examples: 
#	@see strtpl.unittest.py
#
 
import re

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
			if slash % 2 == 0 and wrap1 % 2 == 0 and wrap2 % 2 == 0 and wrap3 % 2 == 0 and wrap4 % 2 == 0 and wrap5 % 2 ==0:
				ret.append (s[start:i])
				start = i + 1
		else: 
			slash = 0
	ret.append (s[start:])
	return ret

def format (tpl, args):
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

