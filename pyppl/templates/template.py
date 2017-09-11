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
			else '"' + str(x) + '"' if isinstance(x, string_types) else str(x),

		'Rbool':    lambda x: str(bool(x)).upper(),
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
		'quote':    lambda x: '''"%s"''' % str(x),
		# array-space quote
		'asquote':  lambda x: '''%s''' % (" ".join(['"' + str(e) + '"' for e in x])),
		# array-comma quote
		'acquote':  lambda x: '''%s''' % (", ".join(['"' + str(e) + '"' for e in x])),
		'squote':   lambda x: """'%s'""" % str(x),
		'json':     __import__('json').dumps,
		'read':     _read,
		'readlines':_readlines

	}

	def __init__(self, source, **envs):
		self.source = source
		self.isfile = False
		self.envs   = {k:v for k, v in Template.DEFAULT_ENVS.items()}
		self.envs.update(envs)
		if source.startswith('file:') and path.exists(source[5:]):
			self.source = self.source[5:]
			self.isfile = True

	def registerEnvs(self, **envs):
		self.envs.update(envs)

	def render(self, data = None):
		data = {} if data is None else data
		data.update(self.envs)
		if self.isfile:
			return self._renderFile(data)
		else:
			return self._render(data)

	# in order to dump setting
	def __str__(self):
		raise NotImplementedError()

	def _render(self, data):
		raise NotImplementedError()

	def _renderFile(self, data):
		with open(self.source) as fs:
			self.source = fs.read()
			return self._render(data)

Template.DEFAULT_ENVS.update({
	'Rvec':     lambda x: 'c(' + ','.join([Template.DEFAULT_ENVS['R'](e) for e in x]) + ')',
	'Rlist':    lambda x: 'list(' + ','.join([k + '=' + Template.DEFAULT_ENVS['R'](x[k]) for k in sorted(x.keys())]) + ')',
})
