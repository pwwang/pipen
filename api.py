#!/usr/bin/env python
"""
Generate API docs for PyPPL
"""
import sys
import inspect
import pyppl
from diot import OrderedDiot
#from pyppl.flowchart import Flowchart
from pyppl.template import Template, TemplateLiquid, TemplateJinja2

class Member:

	BLOCKMAP = dict(
		type = 'example',
		staticmethod = 'tip',
		function = 'abstract',
		classmethod = 'abstract',
		property = 'note'
	)

	TYPEMAP = dict(
		type = 'class',
		staticmethod = 'staticmethod',
		function = 'method',
		classmethod = 'method',
		property = 'property'
	)

	@staticmethod
	def deindent(lines):
		"""Remove indent based on the first line"""
		indention = lines[0][:-len(lines[0].lstrip())]
		ret = []
		for line in lines:
			if not line:
				continue
			if not line.startswith(indention):
				raise ValueError('Unexpected indention at doc line:\n' + repr(line))
			ret.append(line[len(indention):].replace('\t', '  '))
		return ret

	def __init__(self, ctype, name = None, objtype = None):
		self.ctype = ctype
		self.docs  = Member.deindent(ctype.__doc__.splitlines()[1:])
		self.name  = name or self.ctype.__name__
		self.type  = objtype or type(self.ctype).__name__

	def _docSecs(self):
		ret   = OrderedDiot(desc = [])
		name  = 'desc'
		for line in self.docs:
			if not line.startswith('@'):
				ret[name].append(line)
			else:
				name = line.strip('@: ')
				ret[name] = []
		return ret

	def markdown(self, doclevel = 1):
		try:
			args = tuple(inspect.getfullargspec(self.ctype))
		except TypeError:
			args = ('', None, None)
		strargs  = args[0]
		if args[1] is not None:
			strargs.append("*" + str(args[1]))
		if args[2] is not None:
			strargs.append("**" + str(args[2]))

		secs    = self._docSecs()
		prefix  = '\t' * (doclevel - 1)
		ret     = []
		ret.append('\n%s!!! %s "%s: `%s (%s)`"' % (
			prefix,
			Member.BLOCKMAP.get(self.type, 'hint'),
			Member.TYPEMAP.get(self.type, 'function'),
			self.name,
			', '.join(strargs)))
		ret.extend([prefix + '\t' + x for x in secs.pop('desc')])
		for key, val in secs.items():
			ret.append('\n' + prefix + '\t- **%s**\n' % key)
			val = Member.deindent(val)
			for v in val:
				if (v and v[0] in ('\t', ' ')) or ':' not in v:
					ret.append('\n' + prefix + '\t\t\t' + v)
				else:
					name, desc = v.split(':', 1)
					ret.append('\n' + prefix + '\t\t- `%s`: %s' % (name, desc))
		return '\n'.join(ret)

class Klass(Member):

	@staticmethod
	def allClasses():
		classes = [getattr(pyppl, klass) for klass in dir(pyppl)]
		classes.extend([Template, TemplateLiquid, TemplateJinja2])
		ret = []
		for klass in classes:
			if klass.__doc__ and klass.__doc__.startswith('@API'):
				if not inspect.isclass(klass):
					klass = klass.__class__
				ret.append(Klass(klass))
		return sorted(ret, key = lambda klass: klass.name != 'PyPPL')

	def members(self):
		mems = ((getattr(self.ctype, name), name) for name in dir(self.ctype))
		return [Member(mem, name, type(self.ctype.__dict__[name]).__name__)
			for mem, name in mems
			if name in self.ctype.__dict__ and hasattr(mem, '__doc__') \
				and isinstance(mem.__doc__, str) and mem.__doc__.startswith('@API')]

	def markdown(self, doclevel = 1):
		ret = super().markdown() + '\n'
		for member in self.members():
			ret += member.markdown(doclevel + 1) + '\n'
		return ret

def main():
	for klass in Klass.allClasses():
		sys.stderr.write("- Generating APIs for class: %s\n" % klass.name)
		print('## class: %s' % klass.name)
		print(klass.markdown())

if __name__ == "__main__":
	main()
