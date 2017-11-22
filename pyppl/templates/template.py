import json
from os import path, readlink
from six import string_types

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

class Template(object):

	DEFAULT_ENVS = {
		'R': lambda x: 'TRUE' if (isinstance(x, string_types) and str(x).upper() == 'TRUE') or (isinstance(x, bool) and x) \
			else 'FALSE' if (isinstance(x, string_types) and str(x).upper() == 'FALSE') or (isinstance(x, bool) and not x) \
			else 'NA'	if isinstance(x, string_types) and str(x).upper() == 'NA'	\
			else 'NULL'  if isinstance(x, string_types) and str(x).upper() == 'NULL'  \
			else str(x)  if isinstance(x, int) or isinstance(x, float) \
			else str(x)[2:] if isinstance(x, string_types) and (x.startswith('r:') or x.startswith('R:'))  \
			else json.dumps(str(x)) if isinstance(x, string_types) else str(x),
		'realpath': path.realpath,
		'readlink': readlink,
		'dirname':  path.dirname,
		# /a/b/c[1].txt => c.txt
		'basename': _basename,
		'bn':       _basename,
		'filename': _filename,
		'fn':       _filename,
		# /a/b/c.txt => .txt
		'ext':      lambda x: path.splitext(x)[1],
		# /a/b/c[1].txt => /a/b/c
		'prefix':   lambda x, orig = False: path.join(path.dirname(x), _filename(x, orig)),
		'quote':    lambda x: json.dumps(str(x)),
		'json':     json.dumps,
		'read':     _read,
		'readlines':_readlines

	}

	def __init__(self, source, **envs):
		self.source = source
		self.envs   = {k:v for k, v in Template.DEFAULT_ENVS.items()}
		self.envs.update(envs)

	def registerEnvs(self, **envs):
		self.envs.update(envs)

	def render(self, data = None):
		data = {} if data is None else data
		data.update(self.envs)
		return self._render(data)

	# in order to dump setting
	def __str__(self):
		raise NotImplementedError()

	def _render(self, data):
		raise NotImplementedError()


Template.DEFAULT_ENVS.update({
	# array-space quote
	'asquote':  lambda x: '''%s''' % (" " .join([Template.DEFAULT_ENVS['quote'](e) for e in x])),
	# array-comma quote
	'acquote':  lambda x: '''%s''' % (", ".join([Template.DEFAULT_ENVS['quote'](e) for e in x])),
	'squote':   lambda x: "'" + Template.DEFAULT_ENVS['quote'](x)[1:-1] + "'",
	'Rvec':     lambda x: 'c(' + ','.join([Template.DEFAULT_ENVS['R'](e) for e in x]) + ')',
	'Rlist':    lambda x: 'list(' + ','.join([k + '=' + Template.DEFAULT_ENVS['R'](x[k]) for k in sorted(x.keys())]) + ')' if isinstance(x, dict) else \
						  'list(' + ','.join([          Template.DEFAULT_ENVS['R'](k) for k in list(x)]) + ')',
})

