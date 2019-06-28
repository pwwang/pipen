#!/usr/bin/env python
"""
Generate API docs for PyPPL
"""
import inspect
import types
import pyppl
from pyppl.utils import OBox
from pyppl.flowchart import Flowchart
from pyppl.template import Template, TemplateLiquid, TemplateJinja2

class Member:
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

	def __init__(self, ctype, name = None):
		self.ctype = ctype
		self.docs  = Member.deindent(ctype.__doc__.splitlines()[1:])
		self.name  = name or self.ctype.__name__

	def _docSecs(self):
		ret   = OBox(desc = [])
		name  = 'desc'
		for line in self.docs:
			if not line.startswith('@'):
				ret[name].append(line)
			else:
				name = line.strip('@: ')
				ret[name] = []

	def _type(self):
		typename = type(self.ctype).__name__
		if typename == 'type':
			return 'class'
		if typename == 'function':
			if isinstance(self.ctype, staticmethod):
				return 'staticmethod'
			return 'method'
		if typename == 'property':
			return 'property'

	def markdown(self, doclevel = 1):
		secs = self._docSecs()
		return self._type()


class Klass(Member):

	@staticmethod
	def allClasses():
		classes = [getattr(pyppl, klass) for klass in dir(pyppl)]
		classes.extend([Flowchart, Template, TemplateLiquid, TemplateJinja2])
		ret = []
		for klass in classes:
			if klass.__doc__ and klass.__doc__.startswith('@API'):
				if not inspect.isclass(klass):
					klass = klass.__class__
				ret.append(Klass(klass))
		return sorted(ret, key = lambda klass: klass.name != 'PyPPL')

	def members(self):
		return [Member(mem, name) for name, mem in inspect.getmembers(self.ctype)
			if mem.__doc__ and mem.__doc__.startswith('@API')]

	def markdown(self, doclevel = 1):
		ret = super().markdown() + '\n'
		for member in self.members():
			ret += member.markdown(doclevel + 1) + '\n'
		return ret

def main():
	for klass in Klass.allClasses():
		print(klass.markdown())

if __name__ == "__main__":
	main()