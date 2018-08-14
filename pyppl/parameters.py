import sys
import json
import re
from os import path
from six import string_types
from six.moves import configparser
from .utils import Box
from .exception import ParameterNameError, ParameterTypeError, ParametersParseError, ParametersLoadError

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

	def _printName (self, prefix, keylen = 0):
		"""
		Get the print name with type for the parameter
		@params:
			`prefix`: The prefix of the option
		"""
		if self.name == Parameters.POSITIONAL:
			return '<POSITIONAL>'.ljust(keylen)
		name = (prefix + self.name).ljust(keylen)
		if self.type == 'bool':
			return name + ' (bool)'
		elif self.type is None:
			return name
		else:
			return (prefix + self.name).ljust(keylen) + ' <{}>'.format(self.type)

class Parameters (object):
	"""
	A set of parameters
	"""

	ARG_TYPES = dict(
		a       = 'auto',
		auto    = 'auto',
		i       = 'int',
		int     = 'int',
		f       = 'float',
		float   = 'float',
		b       = 'bool',
		bool    = 'bool',
		s       = 'str',
		str     = 'str',
		l       = 'list',
		list    = 'list',
		array   = 'list',
		o       = 'one',
		one     = 'one',
		p       = 'py',
		py      = 'py',
		python  = 'py'
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

	def __init__(self):
		"""
		Constructor
		"""
		self.__dict__['_props'] = dict(
			usage   = [],
			example = [],
			desc    = [],
			hopts   = ['-h', '--help', '-H', '-?', ''],
			prefix  = '-'
		)
		self.__dict__['_params'] = {}

	def __setattr__(self, name, value):
		if name.startswith('__') or name.startswith('_Parameters'): # pragma: no cover
			super(Parameters, self).__setattr__(name, value)
		elif name in self.__dict__: # pragma: no cover
			self.__dict__[name] = value
		elif name in self._params:
			self._params[name].setValue(value)
		else:
			self._params[name] = Parameter(name, value)

	def __getattr__(self, name):
		if name.startswith('__') or name.startswith('_Parameters'): # pragma: no cover
			return super(Parameters, self).__getattr__(name)
		elif name in self.__dict__: # pragma: no cover
			return self.__dict__[name]
		elif not name in self._params:
			self._params[name] = Parameter(name, None)
		return self._params[name]

	def __call__(self, option, value, excl = False):
		"""
		Set options values in `self._props`
		@params:
			`option`: The key of the option
			`value` : The value of the option
			`excl`  : The value is used to exclude (only for `hopts`)
		@returns:
			`self`
		"""
		if option == 'prefix':
			if len(value) == 0:
				raise ParametersParseError('prefix cannot be empty.')
			self._props['prefix'] = value
		elif option == 'hopts':
			if not isinstance(value, list):
				value = [x.strip() for x in value.split(',')]
			if excl:
				self._props['hopts'] = list(set(self._props['hopts']) - set(value))
			else:
				self._props['hopts'] = value
		elif option in ['usage', 'example', 'desc']:
			if not isinstance(value, list):
				value = value.splitlines()
			self._props[option] = [v.strip() for v in value]
		else:
			raise AttributeError('No such option for Parameters: {}'.format(option))
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
		if not args and '' in self._props['hopts']:
			return True
		
		return any([arg and arg in self._props['hopts'] for arg in args])

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
		error = error.strip()
		ret   = error + '\n\n' if error else ''
		prog  = path.basename(sys.argv[0])

		requiredOptions = {}
		optionalOptions = {}

		##
		# REQUIRED OPTIONS:
		#   --param-key    <str>          - description
		# |----------- keylen -----------|
		#   |----- keylen2 ----|
		##
		keylen  = 40 # '--param-xxx <str> ..........'
		keylen2 = 0  # '--param-xxx'

		for key, val in self._params.items():
			# options not suppose to show
			if not val.show:
				continue
			if val.required:
				requiredOptions[key] = val
			else:
				optionalOptions[key] = val

			keylen  = max(len(self._props['prefix']) + 4 + len(key), keylen)
			keylen2 = max(len(self._props['prefix']) + len(key), keylen2)

		keylen = max (4 + len(', '.join(filter(None, self._props['hopts']))), keylen)

		if self._props['desc']:
			ret += 'DESCRIPTION:\n'
			ret += '\n'.join('  ' + d for d in self._props['desc']) + '\n\n'

		ret += 'USAGE:\n'
		if self._props['usage']:
			ret += '\n'.join(
				'  ' + d.replace('{prog}', prog).replace('{program}', prog)
				for d in self._props['usage']
			) + '\n\n'
		else:
			ret += '  ' + prog
			if requiredOptions:
				reqopts = ' '.join(
					val._printName(self._props['prefix']) + \
					('' if not val.type is None else ' <{}>'.format(key.upper()))
					for key, val in requiredOptions.items()
					if key != Parameters.POSITIONAL
				)
				if reqopts:
					ret += ' ' + reqopts
			if optionalOptions:
				ret += ' [OPTIONS]'
			if Parameters.POSITIONAL in self._params and self._params[Parameters.POSITIONAL].required:
				ret += ' <POSITIONAL>'
			ret += '\n\n'

		if self._props['example']:
			ret += 'EXAMPLE:\n'
			ret += '\n'.join(
				'  ' + d.replace('{prog}', prog).replace('{program}', prog) 
				for d in self._props['example']
			) + '\n\n'

		if requiredOptions:
			ret += 'REQUIRED OPTIONS:\n'
			keys = [key for key in sorted(requiredOptions.keys()) if key != Parameters.POSITIONAL]
			if Parameters.POSITIONAL in requiredOptions:
				keys.append(Parameters.POSITIONAL)
			for key in keys:
				val = requiredOptions[key]
				ret  += '  {optitem}{optdesc}'.format(
					optitem = val._printName(self._props['prefix'], keylen2).ljust(keylen - 2),
					optdesc = '- ' + val.desc[0] if val.desc else '- No description.'
				) + '\n'
				for d in val.desc[1:]:
					ret += ' ' * (keylen + 2) + d + '\n' 
			ret += '\n'

		ret += 'OPTIONAL OPTIONS:\n'
		if optionalOptions:
			keys = [key for key in sorted(optionalOptions.keys()) if key != Parameters.POSITIONAL]
			if Parameters.POSITIONAL in optionalOptions:
				keys.append(Parameters.POSITIONAL)
			for key in keys:
				val = optionalOptions[key]
				if key == Parameters.POSITIONAL: continue
				ret  += '  {optitem}{optdesc}'.format(
					optitem = val._printName(self._props['prefix'], keylen2).ljust(keylen - 2),
					optdesc = '- ' + val.desc[0]
				) + '\n'
				for d in val.desc[1:]:
					ret += ' ' * (keylen + 2) + d + '\n' 

		ret += '  ' + ', '.join(filter(None, self._props['hopts'])).ljust(keylen - 2) + '- Print this help information.\n\n'

		if printNexit:
			sys.stderr.write(ret)
			sys.exit(1)
		return ret

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

params = Parameters()
