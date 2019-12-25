import sys
import types
import inspect
from diot import OrderedDiot
from pathlib import Path

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

class Function:

	def __init__(self, docable, name = None):
		self.docable = docable
		self.name = name or docable.__name__
		self.docs = deindent(self.docable.__doc__.splitlines()[1:])

	def _doc_secs(self):
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
			args = tuple(inspect.getfullargspec(self.docable))
		except TypeError:
			args = ('', None, None)
		strargs  = args[0]
		if args[1] is not None:
			strargs.append("*" + str(args[1]))
		if args[2] is not None:
			strargs.append("**" + str(args[2]))

		secs   = self._doc_secs()
		prefix = '  ' * (doclevel - 1)
		ret    = []

		ret.append('\n%s!!! %s "%s: `%s%s`"\n' % (
			prefix,
			BLOCKMAP.get(type(self.docable).__name__, 'hint'),
			TYPEMAP.get(type(self.docable).__name__, 'function'),
			self.name,
			'(%s)' % ', '.join(strargs) if callable(self.docable) else ''))
		ret.extend([prefix + '  ' + x for x in secs.pop('desc')])
		for key, val in secs.items():
			ret.append('\n' + prefix + '  - **%s**' % key)
			val = deindent(val)
			for v in val:
				if (v and v[0] in ('\t', ' ')) or ':' not in v:
					ret.append('\n' + prefix + '      ' + v)
				else:
					name, desc = v.split(':', 1)
					ret.append('\n' + prefix + '    - `%s`: %s' % (name, desc))
		print('\n'.join(ret))

class Class (Function):

	def markdown(self, doclevel = 1):
		secs    = self._doc_secs()
		prefix  = '  ' * (doclevel - 1)
		ret     = []
		ret.append('\n%s!!! %s "%s: `%s`"\n' % (
			prefix,
			BLOCKMAP.get(type(self.docable).__name__, 'hint'),
			TYPEMAP.get(type(self.docable).__name__, 'class'),
			self.docable.__name__))
		ret.extend([prefix + '  ' + x for x in secs.pop('desc')])

		for key, val in secs.items():
			ret.append('\n' + prefix + '  - **%s**' % key)
			val = deindent(val)
			for v in val:
				if (v and v[0] in ('\t', ' ')) or ':' not in v:
					ret.append('\n' + prefix + '      ' + v)
				else:
					name, desc = v.split(':', 1)
					ret.append('\n' + prefix + '    - `%s`: %s' % (name, desc))
		print('\n'.join(ret))

		if self.docable.__init__.__doc__ and self.docable.__init__.__doc__[:4] == '@API':
			Function(self.docable.__init__).markdown(doclevel = doclevel + 1)

		members = [(getattr(self.docable, member), member)
			for member in dir(self.docable) if member[0] != '_']
		for mbobj, member in sorted(members, key = lambda x: type(x[0]).__name__ != 'property'):
			if not mbobj.__doc__ or mbobj.__doc__[:4] != '@API':
				continue
			Function(mbobj, name = member).markdown(doclevel = doclevel + 1)

class Module(Function):

	def __init__(self, docable):
		if docable.__doc__[:4] != '@API':
			docable.__doc__ = '@API\n' + docable.__doc__
		super().__init__(docable)

	def _all_docables(self):
		return [getattr(self.docable, dname) for dname in dir(self.docable) if dname[0] != '_']

	def doc(self):
		sys.stderr.write('\n')
		sys.stderr.write('>>> Dealing with module: %s\n' % self.docable.__name__)
		sys.stderr.write('-' * 80 + '\n')
		print('## ' + self.docable.__name__ + '\n')
		ret = []
		for key, val in self._doc_secs().items():
			ret.append('\n- **%s**' % key)
			val = deindent(val)
			for v in val:
				if (v and v[0] in ('\t', ' ')) or ':' not in v:
					ret.append('\n  ' + v)
				else:
					name, desc = v.split(':', 1)
					ret.append('\n  - `%s`: %s' % (name, desc))
		print('\n'.join(ret))

		for docable in sorted(
			self._all_docables(),
			key=lambda x: not isinstance(x, types.FunctionType)):
			if not hasattr(docable, '__module__') or not docable.__module__:
				continue
			if not docable.__module__.startswith(self.docable.__name__):
				continue
			if not hasattr(docable, '__doc__') or not docable.__doc__:
				continue
			if not docable.__doc__ or docable.__doc__[:4] != '@API':
				continue

			if isinstance(docable, types.FunctionType):
				Function(docable).markdown()
			elif type(docable).__name__ == 'type':
				Class(docable).markdown()

def all_modules(base):
	module = __import__(base)
	if base.count('.') > 1:
		raise ValueError('Only one-level submodules supported.')
	if '.' in base:
		module, sub = base.split('.', 1)
		submodules = [sub]
	else:
		submodules = [modfile.stem for modfile in Path(module.__file__).parent.glob('*.py')
			if modfile.stem[0] != '_']
		module = base
	module = __import__(module, fromlist = submodules)
	return module, submodules

def main(module):
	module, submodules = all_modules(base = module)
	for submod in submodules:
		submod = getattr(module, submod)
		if not hasattr(submod, '__name__'):
			continue
		Module(submod).doc()

if __name__ == '__main__':
	main('pyppl' if len(sys.argv) < 2 else sys.argv[1])
