import json
from os import path, readlink
from six import string_types
from ..utils import asStr

def _read(x):
	with open(x) as f:
		return f.read()

def _readlines(x, skipEmptyLines = True):
	ret = []
	with open(x) as f:
		for line in f:
			line = line.rstrip('\n\r')
			if not line and skipEmptyLines:
				continue
			ret.append(line)
	return ret

def _basename(x, orig = False):
	bn       = path.basename(x)
	if orig: return bn
	filename = path.splitext(bn)[0]
	if not filename.endswith(']'): return bn
	if not '[' in filename: return bn
	return filename.rpartition('[')[0] + path.splitext(bn)[1]

def _filename(x, orig = False):
	return path.splitext(_basename(x, orig))[0]

def _R(x):
	if x is True:
		return 'TRUE'
	if x is False:
		return 'FALSE'
	if x is None:
		return 'NULL'
	if isinstance(x, string_types):
		if x.upper() in ['+INF', 'INF']:
			return 'Inf'
		if x.upper() == '-INF':
			return '-Inf'
		if x.upper() == 'TRUE':
			return 'TRUE'
		if x.upper() == 'FALSE':
			return 'FALSE'
		if x.upper() == 'NA' or x.upper() == 'NULL':
			return x
		if x.startswith('r:') or x.startswith('R:'):
			return asStr(x)[2:]
		return repr(asStr(x))
	if isinstance(x, (list, tuple, set)):
		return 'c({})'.format(','.join([_R(i) for i in x]))
	if isinstance(x, dict):
		#                                                   list allow repeated names
		return 'list({})'.format(','.join([
			_R(v) if isinstance(k, int) else \
			'{0}={1}'.format(asStr(k).split('#')[0], _R(v)) for k, v in x.items()
		]))
	return repr(x)

def _Rlist(x):
	assert isinstance(x, (list, tuple, set, dict))
	if isinstance(x, dict):
		return _R(x)
	else:
		return 'as.list({})'.format(_R(x))

class Template(object):

	DEFAULT_ENVS = {
		'R'        : _R,
		'Rvec'     : _R, # will be deprecated!
		'Rlist'    : _Rlist,
		'realpath' : path.realpath,
		'readlink' : readlink,
		'dirname'  : path.dirname,
		# /a/b/c[1].txt => c.txt
		'basename' : _basename,
		'bn'       : _basename,
		'stem'     : _filename,
		'filename' : _filename,
		'fn'       : _filename,
		# /a/b/c.d.e.txt => c
		'filename2': lambda x, orig = False: _filename(x, orig).split('.')[0],
		'fn2'      : lambda x, orig = False: _filename(x, orig).split('.')[0],
		# /a/b/c.txt => .txt
		'ext'      : lambda x: path.splitext(x)[1],
		# /a/b/c[1].txt => /a/b/c
		'prefix'   : lambda x, orig = False: path.join(path.dirname(x), _filename(x, orig)),
		# /a/b/c.d.e.txt => /a/b/c
		'prefix2'  : lambda x, orig = False: path.join(path.dirname(x), _filename(x, orig).split('.')[0]),
		'quote'    : lambda x: json.dumps(str(x)),
		'squote'   : repr,
		'json'     : json.dumps,
		'read'     : _read,
		'readlines': _readlines
	}

	def __init__(self, source, **envs):
		self.source = source
		self.envs   = Template.DEFAULT_ENVS.copy()
		self.envs.update(envs)

	def registerEnvs(self, **envs):
		self.envs.update(envs)

	def render(self, data = None):
		data = data or {}
		return self._render(data)

	# in order to dump setting
	def __str__(self):
		lines = self.source.splitlines()
		if len(lines) <= 1:
			return '%s < %s >' % (self.__class__.__name__, ''.join(lines))

		ret  = ['%s <<<' % self.__class__.__name__]
		ret += ['\t' + line for line in self.source.splitlines()]
		ret += ['>>>']
		return '\n'.join(ret)

	def __repr__(self):
		return str(self)

	def _render(self, data):
		raise NotImplementedError()


Template.DEFAULT_ENVS.update({
	# array-space quote
	'asquote':  lambda x: '''%s''' % (" " .join([Template.DEFAULT_ENVS['quote'](e) for e in x])),
	# array-comma quote
	'acquote':  lambda x: '''%s''' % (", ".join([Template.DEFAULT_ENVS['quote'](e) for e in x]))
})
