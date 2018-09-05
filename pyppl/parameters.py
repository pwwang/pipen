import sys
import json
import re
from os import path
from six import string_types
from six.moves import configparser
from collections import OrderedDict
from .utils import Box
from .exception import ParameterNameError, ParameterTypeError, ParametersParseError, ParametersLoadError
from .logger import COLORS

class HelpAssembler(object):

	# the max width of the help page, not including the leading space
	MAXPAGEWIDTH = 98
	# the max width of the option name (include the type and placeholder, but not the leading space)
	MAXOPTWIDTH  = 40

	THEMES = dict(
		default = dict(
			error   = COLORS.red,
			warning = COLORS.yellow,
			title   = COLORS.bold + COLORS.underline + COLORS.cyan,
			prog    = COLORS.bold + COLORS.green,
			default = COLORS.magenta,
			optname = COLORS.bold + COLORS.green,
			opttype = COLORS.blue,
			optdesc = ''
		),

		blue = dict(
			error   = COLORS.red,
			warning = COLORS.yellow,
			title   = COLORS.bold + COLORS.underline + COLORS.green,
			prog    = COLORS.bold + COLORS.blue,
			default = COLORS.magenta,
			optname = COLORS.bold + COLORS.blue,
			opttype = COLORS.bold,
			optdesc = ''
		),

		plain = dict(
			error   = '',
			warning = '',
			title   = '',
			prog    = '',
			default = '',
			optname = '',
			opttype = '',
			optdesc = ''
		)
	)

	def __init__(self, prog = None, theme = 'default'):
		self.progname  = prog or path.basename(sys.argv[0])
		if isinstance(theme, dict):
			self.theme = theme
		else:
			self.theme = HelpAssembler.THEMES[theme]

	@staticmethod
	def _reallen( msg, progname):
		proglen   = len(progname)
		progcount = msg.count('{prog}')
		return len(msg) + (proglen - 4) * progcount

	@staticmethod
	def _calcwidth(helps, progname):
		# replace anything with the progname and get the width for each part
		pagewidth = HelpAssembler.MAXPAGEWIDTH
		optwidth  = HelpAssembler.MAXOPTWIDTH
		for key, val in helps.items():
			if not val:
				continue
			# descriptional
			if isinstance(val[0], tuple):
				optwidth     = max([len(v[0]) + len(v[1]) + 3  for v in val])
				optwidth     = max(optwidth, HelpAssembler.MAXOPTWIDTH)
				maxdescwidth = max([HelpAssembler._reallen(w, progname) for v in val for w in v[2]])
				maxdescwidth = max(maxdescwidth, HelpAssembler.MAXPAGEWIDTH - optwidth)
				pagewidth    = optwidth + maxdescwidth
			else:
				pagewidth = max([HelpAssembler._reallen(v, progname) for v in val])
				pagewidth = max(pagewidth, HelpAssembler.MAXPAGEWIDTH)
		return pagewidth, optwidth
				
	def error(self, msg):
		msg = msg.replace('{prog}', self.prog(self.progname))
		return '{colorstart}Error: {msg}{colorend}'.format(
			colorstart = self.theme['error'],
			msg        = msg,
			colorend   = COLORS.end
		)
	
	def warning(self, msg):
		msg = msg.replace('{prog}', self.prog(self.progname))
		return '{colorstart}Warning: {msg}{colorend}'.format(
			colorstart = self.theme['warning'],
			msg        = msg,
			colorend   = COLORS.end
		)

	def title(self, msg):
		return '{colorstart}{msg}{colorend}:'.format(
			colorstart = self.theme['title'],
			msg        = msg.upper(),
			colorend   = COLORS.end
		)

	def prog(self, prog = None):
		prog = prog or self.progname
		return '{colorstart}{prog}{colorend}'.format(
			colorstart = self.theme['prog'],
			prog       = prog,
			colorend   = COLORS.end
		)

	def optname(self, msg):
		return '{colorstart}  {msg}{colorend}'.format(
			colorstart = self.theme['optname'],
			msg        = msg,
			colorend   = COLORS.end
		)

	def opttype(self, msg):
		trimmedmsg = msg.rstrip().upper()
		if not trimmedmsg: 
			return msg
		return '{colorstart}{msg}{colorend}'.format(
			colorstart = self.theme['opttype'],
			msg        = ('({})' if trimmedmsg == 'BOOL' else '<{}>').format(trimmedmsg),
			colorend   = COLORS.end
		) + ' ' * (len(msg) - len(trimmedmsg))

	def optdesc(self, msg):
		msg = msg.replace('{prog}', self.prog(self.progname))
		if msg.startswith('DEFAULT: '):
			msg = '{colorstart}{msg}{colorend}'.format(
				colorstart = self.theme['default'],
				msg        = msg,
				colorend   = COLORS.end
			)
		return '{colorstart}{msg}{colorend}'.format(
			colorstart = self.theme['optdesc'],
			msg        = msg,
			colorend   = COLORS.end
		)

	def plain(self, msg):
		msg = msg.replace('{prog}', self.prog(self.progname))
		return '{colorstart}{msg}{colorend}'.format(
			colorstart = '',
			msg        = msg,
			colorend   = ''
		)

	def assemble(self, helps, progname = None):
		progname = progname or path.basename(sys.argv[0])
		pagewidth, optwidth = HelpAssembler._calcwidth(helps, progname)
		
		ret = []
		for title, helpitems in helps.items():
			if not helpitems:
				continue
			ret.append(self.title(title))
			if isinstance(helpitems[0], tuple):
				for optname, opttype, optdesc in helpitems:
					for i, od in enumerate(optdesc):
						if i == 0:
							line  = self.optname(optname) + ' '
							line += self.opttype(opttype.ljust(optwidth - len(optname) - 3)) if opttype else ' ' * (optwidth - len(optname) - 1)
							line += '- ' + self.optdesc(od.ljust(pagewidth - optwidth - 2))
							ret.append(line)
						else:
							ret.append(' ' * (optwidth + 2) + '  ' + self.optdesc(od.ljust(pagewidth - optwidth - 2)))
			else:
				for h in helpitems:
					ret.append('  ' + self.plain(h.ljust(pagewidth)))
			ret.append('')
		return ret


class Parameter (object):

	"""
	The class for a single parameter
	"""
	def __init__(self, name, value):
		"""
		Constructor
		@params:
			`name`:  The name of the parameter
			`value`: The initial value of the parameter
		"""
		self.__dict__['_props'] = dict(
			desc     = [],
			required = False,
			show     = True,
			type     = None,
			name     = name,
			value    = value
		)
		if not isinstance(name, string_types):
			raise ParameterNameError(name, 'Not a string')
		if not re.search(r'^[A-Za-z0-9_]{1,32}$', name):
			raise ParameterNameError(name, 'Expect a string with alphabetics and underlines in length 1~32, but we got')
		if value is not None:
			t = type(value).__name__
			if t in ['tuple', 'set']:
				t = 'list'
				self._props['value'] = list(value)
			elif t == 'unicode': # py2
				t = 'str'
				self._props['value'] = value.encode()
			elif not t in Parameters.ALLOWED_TYPES:
				raise ParameterTypeError('Unsupported parameter type: ' + t)
			self.setType(t)

	def __setattr__(self, name, value):
		if name.startswith('__') or name.startswith('_Parameter'):
			super(Parameter, self).__setattr__(name, value)
		else:
			getattr(self, 'set' + name.capitalize())(value)

	def __getattr__(self, name):
		if name.startswith('__') or name.startswith('_Parameter'): # pragma: no cover
			return super(Parameter, self).__getattr__(name)
		elif name == 'desc' and not self.required:
			if not self._props['desc'] or not self._props['desc'][-1].startswith('DEFAULT: '):
				self._props['desc'].append('DEFAULT: ' + repr(self.value))
		return self._props[name]

	def __repr__(self):
		return '<Parameter({}) @ {}>'.format(','.join([key+'='+repr(val) for key, val in self._props.items()]), hex(id(self)))

	def __str__(self):
		return str(self.value)

	def setDesc (self, d = ''):
		"""
		Set the description of the parameter
		@params:
			`d`: The description
		"""
		if not isinstance(d, list):
			d = d.splitlines()
		self._props['desc'] = d
		return self

	def setRequired (self, r = True):
		"""
		Set whether this parameter is required
		@params:
			`r`: True if required else False. Default: True
		"""
		if self._props['type'] == 'bool':
			raise ParameterTypeError(self.value, 'Bool option "%s" cannot be set as required' % self.name)
		self._props['required'] = r
		return self

	def setType (self, t = 'str'):
		"""
		Set the type of the parameter
		@params:
			`t`: The type of the value. Default: str
			- Note: str rather then 'str'
		"""
		if not isinstance(t, string_types):
			t = t.__name__
		tcolon = t if ':' in t else t + ':'
		t1, t2 = tcolon.split(':', 2)
		if t1 in Parameters.ARG_TYPES:
			t1 = Parameters.ARG_TYPES[t1]
		if t2 in Parameters.ARG_TYPES:
			t2 = Parameters.ARG_TYPES[t2]
		
		t2use = t1 + ':' + t2 if t2 else t1
		if t2use not in Parameters.ALLOWED_TYPES and not t2use.startswith('list'):
			raise ParameterTypeError(t, 'Unsupported type for option "%s"' % self.name)
		self._props['type'] = t2use
		if not self.value is None:
			self._forceType()
		return self

	def _forceType (self):
		"""
		Coerce the value to the type specified
		TypeError will be raised if error happens
		"""
		if self.type is None: return
		self.value = Parameters._coerceValue(self.value, self.type)

	def setShow (self, s = True):
		"""
		Set whether this parameter should be shown in help information
		@params:
			`s`: True if it shows else False. Default: True
		"""
		self._props['show'] = s
		return self

	def setValue (self, v):
		"""
		Set the value of the parameter
		@params:
			`v`: The value
		"""
		self._props['value'] = v
		return self

	def setName (self, n):
		"""
		Set the name of the parameter
		@params:
			`n`: The name
		"""
		self._props['name'] = n
		return self

class Parameters (object):
	"""
	A set of parameters
	"""

	ARG_TYPES = dict(
		a = 'auto',  auto  = 'auto',
		i = 'int',   int   = 'int',
		f = 'float', float = 'float',
		b = 'bool',  bool  = 'bool',
		s = 'str',   str   = 'str',
		o = 'one',   one   = 'one',
		p = 'py',    py    = 'py',    python = 'py',
		l = 'list',  list  = 'list',  array  = 'list'
	)

	ARG_NAME_PATTERN     = r'^([a-zA-Z][\w\._-]*)(?::(p|py|python|a|auto|i|int|f|float|b|bool|s|str|l|list|array|(?:array|l|list):(?:a|auto|i|int|f|float|b|bool|s|str|l|list|array|o|one|p|py|python)))?(?:=(.+))?$'
	ARG_VALINT_PATTERN   = r'^[+-]?\d+$'
	ARG_VALFLOAT_PATTERN = r'^[+-]?(?:\d*\.)?\d+(?:[Ee][+-]\d+)?$'
	ARG_VALBOOL_PATTERN  = r'^(t|T|True|TRUE|true|1|Y|y|Yes|YES|yes|on|ON|On|f|F|False|FALSE|false|0|N|n|No|NO|off|Off|OFF)$'
	ARG_VALPY_PATTERN    = r'^(?:py|expr):(.+)$'

	VAL_TRUES  = ['t', 'T', 'True' , 'TRUE' , 'true' , '1', 'Y', 'y', 'Yes', 'YES', 'yes', 'on' , 'ON' , 'On' ]
	VAL_FALSES = ['f', 'F', 'False', 'FALSE', 'false', '0', 'N', 'n', 'No' , 'NO' , 'no' , 'off', 'OFF', 'Off']

	POSITIONAL = '_'

	ALLOWED_TYPES = ['str', 'int', 'float', 'bool', 'list']

	def __init__(self, command = None, theme = 'default'):
		"""
		Constructor
		"""
		prog = path.basename(sys.argv[0])
		self.__dict__['_prog']  = prog + ' ' + command if command else prog
		self.__dict__['_props'] = dict(
			usage  = [],
			desc   = [],
			hopts  = ['-h', '--help', '-H', '-?'],
			prefix = '-',
			hbald  = True
		)
		self.__dict__['_params'] = {}
		self.__dict__['_assembler'] = HelpAssembler(self._prog, theme)

	def _setTheme(self, theme):
		self._assembler = HelpAssembler(self._prog, theme)
		return self
	
	def _setUsage(self, usage):
		self._props['usage'] = usage if isinstance(usage, list) else [usage]
		return self
	
	def _setDesc(self, desc):
		self._props['desc'] = desc if isinstance(desc, list) else [desc]
		return self

	def _setHopts(self, hopts):
		self._props['desc'] = desc if isinstance(desc, list) else [d.strip() for d in desc.split(',')]
		return self
	
	def _setPrefix(self, prefix):
		self._props['prefix'] = prefix
		return self
	
	def _setHbald(self, hbald = True):
		self._props['hbald'] = hbald
		return self

	def __setattr__(self, name, value):
		if name.startswith('__') or name.startswith('_Parameters'): # pragma: no cover
			super(Parameters, self).__setattr__(name, value)
		elif name in self.__dict__: # pragma: no cover
			self.__dict__[name] = value
		elif isinstance(value, Parameter):
			self._params[name] = value
		elif name in self._params:
			self._params[name].setValue(value)
		elif name in ['_usage', '_desc', '_prefix', '_hopts', '_hbald', '_theme']:
			getattr(self, '_set' + name[1:].capitalize())(value)
		else:
			self._params[name] = Parameter(name, value)

	def __getattr__(self, name):
		if name.startswith('__') or name.startswith('_Parameters'): # pragma: no cover
			return super(Parameters, self).__getattr__(name)
		elif not name in self._params:
			self._params[name] = Parameter(name, None)
		return self._params[name]

	def __call__(self, option, value):
		"""
		Set options values in `self._props`
		@params:
			`option`: The key of the option
			`value` : The value of the option
			`excl`  : The value is used to exclude (only for `hopts`)
		@returns:
			`self`
		"""
		setattr(self, '_' + option, value)
		return self

	def _parseName(self, argname):
		"""
		If `argname` is the name of an option
		@params:
			`argname`: The argname
		@returns:
			`an`: clean argument name
			`at`: normalized argument type
			`av`: the argument value, if `argname` is like: `-a=1`
		"""
		an, at, av = None, 'auto', None
		if not argname.startswith(self._props['prefix']):
			return an, at, av
		argname = argname[len(self._props['prefix']):]
		m = re.match(Parameters.ARG_NAME_PATTERN, argname)
		if not m: return an, at, av
		an = m.group(1)
		at = m.group(2) or 'auto'
		av = m.group(3)
		if ':' in at:
			at, att = at.split(':')
			at = Parameters.ARG_TYPES[at] + ':' + Parameters.ARG_TYPES[att]
		else:
			at = Parameters.ARG_TYPES[at]
		return an, at, av

	def _shouldPrintHelp(self, args):
		if self._props['hbald'] and not args:
			return True
		
		return any([arg in self._props['hopts'] for arg in args])

	@staticmethod
	def _coerceValue(value, t = 'auto'):
		try:
			if t == 'int' and not isinstance(value, int):
				return int(value)
			elif t == 'float' and not isinstance(value, float):
				return float(value)
			elif t == 'bool' and not isinstance(value, (int, bool)):
				if value in Parameters.VAL_TRUES:
					return True
				elif value in Parameters.VAL_FALSES:
					return False
				else:
					sys.stderr.write('WARNING: Unknown bool value, use True instead of {}.\n'.format(repr(value)))
					return True
			elif t == 'py':
				return eval(value)
			elif t == 'str':
				return str(value)
			elif t == 'auto':
				try:
					if re.match(Parameters.ARG_VALINT_PATTERN, value):
						t = 'int'
					elif re.match(Parameters.ARG_VALFLOAT_PATTERN, value):
						t = 'float'
					elif re.match(Parameters.ARG_VALBOOL_PATTERN, value):
						t = 'bool'
					else:
						t = None
						m = re.match(Parameters.ARG_VALPY_PATTERN, value)
						if m: 
							t = 'py'
							value = m.group(1)
					return Parameters._coerceValue(value, t)
				except TypeError: # value is not a string, cannot do re.match
					return value
			elif not t is None and t.startswith('list'):
				if isinstance(value, string_types):
					value = [value]
				else:
					try:
						value = list(value)
					except TypeError:
						value = [value]
				subtype = ':' in t and t.split(':')[1] or 'auto'
				if subtype == 'one':
					return [value]
				return [Parameters._coerceValue(x, subtype) for x in value]
			else:
				return value
		except (ValueError, TypeError):
			raise ParameterTypeError(t, 'Unable to coerce value %s to type' % (repr(value)))

	def _getType(self, argname, argtype):
		if argname not in self._params:
			sys.stderr.write ('WARNING: Unknown option {}{}.\n'.format(self._props['prefix'], argname))
			return False

		if argtype == 'auto' and self._params[argname].type:
			argtype = self._params[argname].type
		elif argtype != 'auto' and self._params[argname].type != argtype and self._params[argname].type is not None:
			sys.stderr.write (
				'WARNING: Decleared type "{dtype}" ignored, use "{ptype}" instead for option {prefix}{option}.\n'.format(
					dtype  = self._params[argname].type,
					ptype  = argtype,
					prefix = self._props['prefix'],
					option = argname
				)
			)
		if argtype == 'list':
			argtype = 'list:auto'

		return argtype or 'auto'

	def _putValue(self, argname, argtype, argval):
		atype = self._getType(argname, argtype)
		if atype is False:
			return False
		if atype.startswith('list'):
			if self._params[argname].value is None:
				self._params[argname].value = []
			subtype = atype.split(':')[1]
			if subtype == 'one':
				if not self._params[argname].value:
					self._params[argname].value.append([])
				self._params[argname].value[0].append(argval)
			else:
				self._params[argname].value.append(Parameters._coerceValue(argval, subtype))
			return True
		else:
			self._params[argname].value = Parameters._coerceValue(argval, atype)
			return False

	def parse (self, args = None):
		"""
		Parse the arguments from `sys.argv`
		"""
		args = args is None and sys.argv[1:] or args
		if self._shouldPrintHelp(args):
			self.help(printNexit = True)

		setattr(self, Parameters.POSITIONAL, [])
		# arbitrarily parse the arguments
		argname, argtype = None, 'auto'
		for arg in args:
			argname2, argtype2, argvalue = self._parseName(arg)
			if not argname: # argname not reached yet
				if argname2: # I am the first argname
					# it's not -a=1 format, just -a or it's list (-a:list=1)
					if argvalue is None or self._putValue(argname2, argtype2, argvalue): 
						argname, argtype = argname2, argtype2
				else: # argname not reached yet and I am not an argname, so I am positional
					self._putValue(Parameters.POSITIONAL, 'list', arg)
			else: # argname reached
				if argname2: # it's argname
					# type 'list' hasn't closed, so it should not be bool
					atype = self._getType(argname, argtype)
					if not atype or not atype.startswith('list'):
						self._putValue(argname, 'bool', 'True')
					# no value offered or it's a list option
					if argvalue is None or self._putValue(argname2, argtype2, argvalue):
						argname, argtype = argname2, argtype2
					# single-value option, reset
					else:
						argname, argtype = None, 'auto'
				else: # it's value
					if not self._putValue(argname, argtype, arg):
						argname, argtype = None, 'auto'

		if argname:
			atype = self._getType(argname, argtype)
			if not atype or not atype.startswith('list'):
				self._putValue(argname, 'bool', 'True')

		# check the types, values of the params
		for name in self._params:
			if self._params[name].required and self._params[name].value is None:
				self.help(error = 'ERROR: Option {}{} is required.'.format(self._props['prefix'], name), printNexit = True)

		return self.asDict()

	def help (self, error = '', printNexit = False):
		"""
		Calculate the help page
		@params:
			`error`: The error message to show before the help information. Default: `''`
			`printNexit`: Print the help page and exit the program? Default: `False` (return the help information)
		@return:
			The help information
		"""
		posopt = None
		if Parameters.POSITIONAL in self._params:
			posopt = self._params[Parameters.POSITIONAL]
			if len(posopt.desc) == 1 and posopt.desc[0].startswith('DEFAULT: '):
				posopt = None

		requiredOptions   = []
		optionalOptions   = []
		for val in self._params.values():
			# options not suppose to show
			if not val.show:
				continue
			if val.name == Parameters.POSITIONAL:
				continue
			else:
				option = (self._props['prefix'] + val.name, (val.type or '').upper(), val.desc)
			if val.required:
				requiredOptions.append(option)
			else:
				optionalOptions.append(option)
		
		if posopt:
			if posopt.required:
				requiredOptions.append(option)
			else:
				optionalOptions.append(option)			

		helpitems = OrderedDict()
		if self._props['desc']:
			helpitems['description'] = self._props['desc']
		
		if self._props['usage']:
			helpitems['usage'] = self._props['usage']
		else: # default usage
			defusage = ['{prog}']
			for optname, opttype, _ in requiredOptions:
				if optname == Parameters.POSITIONAL:
					continue
				defusage.append('<{} {}>'.format(optname, opttype or optname[len(self._props['prefix']):].upper()))
			if optionalOptions:
				defusage.append('[OPTIONS]')
			if posopt:
				defusage.append('POSITIONAL' if posopt.required else '[POSITIONAL]')

			helpitems['usage'] = [' '.join(defusage)]

		optionalOptions.append((', '.join(filter(None, self._props['hopts'])), '', ['Print this help information']))
		helpitems['required options'] = requiredOptions
		helpitems['optional options'] = optionalOptions

		ret = []
		if error:
			if not isinstance(error, list):
				error = [error]
			ret = [self._assembler.error(err.strip()) for err in error]
		
		ret += self._assembler.assemble(helpitems, self._prog)

		out = '\n'.join(ret) + '\n'
		if printNexit:
			sys.stderr.write(out)
			sys.exit(1)
		else:
			return out

	def loadDict (self, dictVar, show = False):
		"""
		Load parameters from a dict
		@params:
			`dictVar`: The dict variable.
			- Properties are set by "<param>.required", "<param>.show", ...
			`show`:    Whether these parameters should be shown in help information
				- Default: False (don't show parameter from config object in help page)
				- It'll be overwritten by the `show` property inside dict variable.
				- If it is None, will inherit the param's show value
		"""
		# load the param first
		for key, val in dictVar.items():
			if '.' in key: continue
			if not key in self._params:
				self._params[key] = Parameter(key, val)
			self._params[key].value = val
			if show is not None:
				self._params[key].show = show
		# then load property
		for key, val in dictVar.items():
			if '.' not in key: continue
			k, prop = key.split('.', 1)
			if not k in self._params:
				raise ParametersLoadError(key, 'Cannot set attribute of an undefined option %s' % repr(k))
			if not prop in ['desc', 'required', 'show', 'type']:
				raise ParametersLoadError(prop, 'Unknown attribute name for option %s' % repr(k))

			setattr (self._params[k], prop, val)
		return self

	def loadFile (self, cfgfile, show = False):
		"""
		Load parameters from a json/config file
		If the file name ends with '.json', `json.load` will be used,
		otherwise, `ConfigParser` will be used.
		For config file other than json, a section name is needed, whatever it is.
		@params:
			`cfgfile`: The config file
			`show`:    Whether these parameters should be shown in help information
				- Default: False (don't show parameter from config file in help page)
				- It'll be overwritten by the `show` property inside the config file.
		"""
		config = {}
		if cfgfile.endswith('.json'):
			with open(cfgfile) as f:
				config = json.load(f)
		elif cfgfile.endswith('yml') or cfgfile.endswith('yaml'):
			import yaml
			with open(cfgfile) as f:
				config = yaml.safe_load(f)
		else:
			cp = configparser.ConfigParser()
			cp.optionxform = str
			cp.read(cfgfile)
			sec = cp.sections()
			config = {}
			for s in sec:
				config.update(dict(cp.items(s)))

		for key, val in config.items():
			if key.endswith('.type'):
				config[key] = val
				if val.startswith('list') and key[:-5] in config and not isinstance(config[key[:-5]], list):
					config[key[:-5]] = config[key[:-5]].strip().splitlines()
			elif key.endswith('.show') or key.endswith('.required'):
				if isinstance(val, bool): continue
				config[key] = Parameters._coerceValue(val, 'bool')
		self.loadDict(config, show = show)
		return self

	def asDict (self):
		"""
		Convert the parameters to Box object
		@returns:
			The Box object
		"""
		ret = Box()
		for name in self._params:
			ret[name] = self._params[name].value
		return ret

class Commands(object):
	"""
	Support sub-command for command line argument parse.
	"""

	def __init__(self, theme = 'default'):
		self.__dict__['_desc']      = []
		self.__dict__['_hcmd']      = 'help'
		self.__dict__['_cmds']      = OrderedDict()
		self.__dict__['_assembler'] = HelpAssembler(None, theme)

	def _setDesc(self, desc):
		self.__dict__['_desc'] = desc if isinstance(desc, list) else [desc]
		return self

	def _setHcmd(self, hcmd):
		self.__dict__['_hcmd'] = hcmd
		return self
	
	def _setTheme(self, theme):
		self.__dict__['_assembler'] = HelpAssembler(None, theme)
		return self
	
	def __getattr__(self, name):
		if name.startswith('__') or name.startswith('_Commands'): # pragma: no cover
			return super(Commands, self).__getattr__(name)
		elif not name in self._cmds:
			self._cmds[name] = Parameters(name, self._assembler._theme)
		return self._cmds[name]

	def __setattr__(self, name, value):
		if name.startswith('__') or name.startswith('_Commands'): # pragma: no cover
			return super(Commands, self).__setattr__(name, value)
		elif name == '_desc':
			self._setDesc(value)
		elif name == '_theme':
			self._setTheme(value)
		elif name == '_hcmd':
			self._setHcmd(value)
		else:
			if not name in self._cmds:
				self._cmds[name] = Parameters(name, self._assembler.theme)
			self._cmds[name]('desc', value if isinstance(value, list) else [value])

	def __getitem__(self, name):
		return getattr(self, name)

	def parse(self, args = None):
		args = args or sys.argv[1:]
		if not args or (len(args) == 1 and args[0] == self._hcmd):
			self.help(printNexit = True)

		command = args.pop(0)
		if (command == self._hcmd and args[0] not in self._cmds) and \
			command not in self._cmds:
			self.help(
				error = 'Unknown command: {}'.format(args[0] if command == self._hcmd else command), 
				printNexit = True
			)
		if command == self._hcmd:
			self._cmds[args[0]].help(printNexit = True)
		
		return command, self._cmds[command].parse(args)

	def help(self, error = '', printNexit = False):

		helpitems = OrderedDict()

		if self._desc:
			helpitems['description'] = self._desc
		
		helpitems['commands'] = []
		for key, val in self._cmds.items():
			helpitems['commands'].append((key, '', val._props['desc']))
		helpitems['commands'].append((self._hcmd, 'command', ['Print help information for the command']))

		ret = []
		if error:
			ret = [self._assembler.error(error.strip())]
		ret += self._assembler.assemble(helpitems)

		out = '\n'.join(ret) + '\n'
		if printNexit:
			sys.stderr.write(out)
			sys.exit(1)
		else:
			return out

params   = Parameters()
commands = Commands()