"""
parameters module for PyPPL
"""
import sys
import re
from os import path
from collections import OrderedDict
from .utils import Box, string_types, ConfigParser, jsonLoads
from .exceptions import ParameterNameError, ParameterTypeError, \
	ParametersParseError, ParametersLoadError
from colorama import Fore, Back, Style # pylint: disable=unused-import

class HelpAssembler(object):
	"""
	A helper class to help assembling the help information page.
	@staticvars
		`MAXPAGEWIDTH`: the max width of the help page, not including the leading space
		`MAXOPTWIDTH` : the max width of the option name
			- (include the type and placeholder, but not the leading space)
		`THEMES`      : the themes
	"""

	# the max width of the help page, not including the leading space
	MAXPAGEWIDTH = 98
	# the max width of the option name (include the type and placeholder, but not the leading space)
	MAXOPTWIDTH  = 38

	THEMES = dict(
		default = dict(
			error   = Fore.RED,
			warning = Fore.YELLOW,
			title   = Style.BRIGHT + Fore.CYAN,
			prog    = Style.BRIGHT + Fore.GREEN,
			default = Fore.MAGENTA,
			optname = Style.BRIGHT + Fore.GREEN,
			opttype = Fore.BLUE,
			optdesc = ''
		),

		blue = dict(
			error   = Fore.RED,
			warning = Fore.YELLOW,
			title   = Style.BRIGHT + Fore.GREEN,
			prog    = Style.BRIGHT + Fore.BLUE,
			default = Fore.MAGENTA,
			optname = Style.BRIGHT + Fore.BLUE,
			opttype = Style.BRIGHT,
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
		"""
		Constructor
		@params:
			`prog`: The program name
			`theme`: The theme. Could be a name of `THEMES`, or a dict of a custom theme.
		"""
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
		for val in helps.values():
			if not val:
				continue
			# descriptional
			if isinstance(val[0], tuple):
				optwidth     = max([len(valitem[0]) + len(valitem[1]) + 3  for valitem in val])
				optwidth     = max(optwidth, HelpAssembler.MAXOPTWIDTH)
				maxdescwidth = max([
					HelpAssembler._reallen(w, progname)
					for valitem in val
					for w in (valitem[2] if isinstance(valitem[2], list) else [valitem[2]])
				] or [0])
				maxdescwidth = max(maxdescwidth, HelpAssembler.MAXPAGEWIDTH - optwidth)
				pagewidth    = optwidth + maxdescwidth
			else:
				pagewidth = max([HelpAssembler._reallen(valitem, progname) for valitem in val])
				pagewidth = max(pagewidth, HelpAssembler.MAXPAGEWIDTH)
		return pagewidth, optwidth

	def error(self, msg, with_prefix = True):
		"""
		Render an error message
		@params:
			`msg`: The error message
		"""
		msg = msg.replace('{prog}', self.prog(self.progname))
		return '{colorstart}{prefix}{msg}{colorend}'.format(
			colorstart = self.theme['error'],
			prefix     = 'Error: ' if with_prefix else '',
			msg        = msg,
			colorend   = Style.RESET_ALL
		)

	def warning(self, msg, with_prefix = True):
		"""
		Render an warning message
		@params:
			`msg`: The warning message
		"""
		msg = msg.replace('{prog}', self.prog(self.progname))
		return '{colorstart}{prefix}{msg}{colorend}'.format(
			colorstart = self.theme['warning'],
			prefix     = 'Warning: ' if with_prefix else '',
			msg        = msg,
			colorend   = Style.RESET_ALL
		)

	def title(self, msg):
		"""
		Render an section title
		@params:
			`msg`: The section title
		"""
		return '{colorstart}{msg}{colorend}:'.format(
			colorstart = self.theme['title'],
			msg        = msg.upper(),
			colorend   = Style.RESET_ALL
		)

	def prog(self, prog = None):
		"""
		Render the program name
		@params:
			`msg`: The program name
		"""
		prog = prog or self.progname
		return '{colorstart}{prog}{colorend}'.format(
			colorstart = self.theme['prog'],
			prog       = prog,
			colorend   = Style.RESET_ALL
		)

	def optname(self, msg):
		"""
		Render the option name
		@params:
			`msg`: The option name
		"""
		return '{colorstart}  {msg}{colorend}'.format(
			colorstart = self.theme['optname'],
			msg        = msg,
			colorend   = Style.RESET_ALL
		)

	def opttype(self, msg):
		"""
		Render the option type or placeholder
		@params:
			`msg`: the option type or placeholder
		"""
		trimmedmsg = msg.rstrip().upper()
		if not trimmedmsg:
			return msg
		return '{colorstart}{msg}{colorend}'.format(
			colorstart = self.theme['opttype'],
			msg        = ('({})' if trimmedmsg == 'BOOL' else '<{}>').format(trimmedmsg),
			colorend   = Style.RESET_ALL
		) + ' ' * (len(msg) - len(trimmedmsg))

	def optdesc(self, msg):
		"""
		Render the option descriptions
		@params:
			`msg`: the option descriptions
		"""
		msg = msg.replace('{prog}', self.prog(self.progname))
		if msg.startswith('DEFAULT: ') or msg.startswith('Default: '):
			msg = '{colorstart}{msg}{colorend}'.format(
				colorstart = self.theme['default'],
				msg        = msg,
				colorend   = Style.RESET_ALL
			)
		return '{colorstart}{msg}{colorend}'.format(
			colorstart = self.theme['optdesc'],
			msg        = msg,
			colorend   = Style.RESET_ALL
		)

	def plain(self, msg):
		"""
		Render a plain message
		@params:
			`msg`: the message
		"""
		msg = msg.replace('{prog}', self.prog(self.progname))
		return '{colorstart}{msg}{colorend}'.format(
			colorstart = '',
			msg        = msg,
			colorend   = Style.RESET_ALL
		)

	def assemble(self, helps, progname = None):
		"""
		Assemble the whole help page.
		@params:
			`helps`: The help items. A list with plain strings or tuples of 3 elements, which
				will be treated as option name, option type/placeholder and option descriptions.
			`progname`: The program name used to replace '{prog}' with.
		@returns:
			lines (`list`) of the help information.
		"""
		progname = progname or path.basename(sys.argv[0])
		pagewidth, optwidth = HelpAssembler._calcwidth(helps, progname)

		ret = []
		for title, helpitems in helps.items():
			if not helpitems:
				continue
			ret.append(self.title(title))
			if isinstance(helpitems[0], tuple):
				for optname, opttype, optdesc in helpitems:
					opttype = opttype.strip()
					if not optdesc:
						optdesc = ['[ No description. ]']
					if not isinstance(optdesc, list):
						optdesc = [optdesc]
					for i, optd in enumerate(optdesc):
						if i == 0:
							line  = self.optname(optname) + ' '
							line += self.opttype(opttype.ljust(optwidth - len(optname) - 3)) \
								if opttype else ' ' * (optwidth - len(optname) - 1)
							line += '- ' + self.optdesc(optd.ljust(pagewidth - optwidth - 2))
							ret.append(line)
						else:
							ret.append(
								' ' * (optwidth + 2) + '  ' +
								self.optdesc(optd.ljust(pagewidth - optwidth - 2)))
			else:
				for hitem in helpitems:
					ret.append('  ' + self.plain(hitem.ljust(pagewidth)))
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
			value    = value,
			callback = None
		)
		if not isinstance(name, string_types):
			raise ParameterNameError(name, 'Not a string')
		if not re.search(r'^[A-Za-z0-9_,\-.]{1,255}$', name):
			raise ParameterNameError(
				name,
				'Expect a string with comma, alphabetics ' +
				'and/or underlines in length 1~255, but we got')
		if value is not None:
			typename = type(value).__name__
			if typename in ['tuple', 'set']:
				typename = 'list'
				self._props['value'] = list(value)
			elif typename == 'unicode': # py2
				typename = 'str'
				self._props['value'] = value.encode()
			elif not typename in Parameters.ALLOWED_TYPES:
				raise ParameterTypeError('Unsupported parameter type: ' + typename)
			self.setType(typename)

	def __setattr__(self, name, value):
		"""
		Set the value of the attribute
		@params:
			`name` : The name of the attribute
			`value`: The value of the attribute
		"""
		if name.startswith('__') or name.startswith('_Parameter'):
			super(Parameter, self).__setattr__(name, value)
		else:
			getattr(self, 'set' + name.capitalize())(value)

	def __getattr__(self, name):
		"""
		Get the value of the attribute
		@params:
			`name` : The name of the attribute
		@returns:
			The value of the attribute
		"""
		if name.startswith('__') or name.startswith('_Parameter'): # pragma: no cover
			return getattr(super(Parameter, self), name)
		elif name == 'desc' and not self.required:
			if not self._props['desc'] or not (
				self._props['desc'][-1].startswith('DEFAULT: ') or \
				self._props['desc'][-1].startswith('Default: ')
			):
				self._props['desc'].append('Default: ' + repr(self.value))
		return self._props[name]

	def __repr__(self):
		return '<Parameter({}) @ {}>'.format(','.join([
			key+'='+repr(val) for key, val in self._props.items()]), hex(id(self)))

	def __str__(self):
		return str(self.value)

	def str(self):
		"""Get the value in str"""
		return str(self)

	def int(self):
		"""Coerce value to integer"""
		return int(self.value)

	def float(self):
		"""Coerce value to float"""
		return float(self.value)

	def __add__(self, other):
		return str(self) + str(other)

	def __contains__(self, other):
		return other in str(self)

	def __eq__(self, other):
		return str(self) == str(other)

	def __ne__(self, other):
		return not self.__eq__(other)

	def __bool__(self):
		return bool(self.value)

	def setDesc (self, desc = ''):
		"""
		Set the description of the parameter
		@params:
			`desc`: The description
		"""
		if not isinstance(desc, list):
			desc = desc.splitlines()
		self._props['desc'] = desc
		return self

	def setRequired (self, req = True):
		"""
		Set whether this parameter is required
		@params:
			`req`: True if required else False. Default: True
		"""
		if self._props['type'] == 'bool':
			raise ParameterTypeError(
				self.value, 'Bool option "%s" cannot be set as required' % self.name)
		self._props['required'] = req
		return self

	def setType (self, typename = 'str'):
		"""
		Set the type of the parameter
		@params:
			`typename`: The type of the value. Default: str
			- Note: str rather then 'str'
		"""
		if not isinstance(typename, string_types):
			typename = typename.__name__
		tcolon = typename if ':' in typename else typename + ':'
		type1, type2 = tcolon.split(':', 1)
		if type1 in Parameters.ARG_TYPES:
			type1 = Parameters.ARG_TYPES[type1]
		if type2 in Parameters.ARG_TYPES:
			type2 = Parameters.ARG_TYPES[type2]

		t2use = type1 + ':' + type2 if type2 else type1
		if t2use not in Parameters.ALLOWED_TYPES and not t2use.startswith('list'):
			raise ParameterTypeError(typename, 'Unsupported type for option "%s"' % self.name)
		self._props['type'] = t2use
		if not self.value is None:
			self._forceType()
		return self

	def setCallback(self, callback):
		"""
		Set callback
		@params:
			`callback`: The callback
		"""
		if not callable(callback):
			raise TypeError('Callback for parameter must be callable')
		self._props['callback'] = callback

	def _forceType (self):
		"""
		Coerce the value to the type specified
		TypeError will be raised if error happens
		"""
		if self.type is None:
			return
		self.value = Parameters._coerceValue(self.value, self.type)

	def setShow (self, show = True):
		"""
		Set whether this parameter should be shown in help information
		@params:
			`show`: True if it shows else False. Default: True
		"""
		self._props['show'] = show
		return self

	def setValue (self, val):
		"""
		Set the value of the parameter
		@params:
			`val`: The value
		"""
		self._props['value'] = val
		return self

	def setName (self, name):
		"""
		Set the name of the parameter
		@params:
			`name`: The name
		"""
		self._props['name'] = name
		return self

	def __hash__(self):
		return id(self)


class Parameters (object):
	"""
	A set of parameters

	@static variables:
		`ARG_TYPES`           : shortcuts for argument types
		`ARG_NAME_PATTERN`    : A pattern to recognize an argument name
		`ARG_VALINT_PATTERN`  : An integer argument pattern
		`ARG_VALFLOAT_PATTERN`: A float argument pattern
		`ARG_VALBOOL_PATTERN` : A bool argument pattern
		`ARG_VALPY_PATTERN`   : A python expression argument pattern

		`VAL_TRUES` : Values translated to `True`
		`VAL_FALSES`: Values translated to `False`

		`POSITIONAL`   : Flag for positional arguments
		`ALLOWED_TYPES`: All allowed argument types
	"""
	ARG_TYPES = dict(
		a = 'auto',  auto  = 'auto',  i = 'int',   int   = 'int',
		f = 'float', float = 'float', b = 'bool',  bool  = 'bool',
		s = 'str',   str   = 'str',   o = 'one',   one   = 'one',
		p = 'py',    py    = 'py',    python = 'py',
		l = 'list',  list  = 'list',  array  = 'list'
	)

	ARG_NAME_PATTERN     = r"^([a-zA-Z][\w,\._-]*)" + \
		r'(?::(p|py|python|a|auto|i|int|f|float|b|bool|s|str|l|list|array|(?:array|l|list):' + \
		r'(?:a|auto|i|int|f|float|b|bool|s|str|l|list|array|o|one|p|py|python)))?(?:=(.+))?$'
	ARG_VALINT_PATTERN   = r'^[+-]?\d+$'
	ARG_VALFLOAT_PATTERN = r'^[+-]?(?:\d*\.)?\d+(?:[Ee][+-]\d+)?$'
	ARG_VALBOOL_PATTERN  = r'^(t|T|True|TRUE|true|1|Y|y|Yes|YES|yes|on|ON|On|f|F|False' + \
		r'|FALSE|false|0|N|n|No|NO|off|Off|OFF)$'
	ARG_VALPY_PATTERN    = r'^(?:py|expr):(.+)$'

	VAL_TRUES  = [
		't', 'T', 'True' , 'TRUE' , 'true' , '1', 'Y', 'y', 'Yes',
		'YES', 'yes', 'on' , 'ON' , 'On' ]
	VAL_FALSES = ['f', 'F', 'False', 'FALSE', 'false', '0', 'N',
		'n', 'No' , 'NO' , 'no' , 'off', 'OFF', 'Off']

	POSITIONAL = '_'

	ALLOWED_TYPES = ['str', 'int', 'float', 'bool', 'list', 'py']

	def __init__(self, command = None, theme = 'default'):
		"""
		Constructor
		@params:
			`command`: The sub-command
			`theme`: The theme
		"""
		prog = path.basename(sys.argv[0])
		self.__dict__['_prog']  = prog + ' ' + command if command else prog
		self.__dict__['_props'] = dict(
			usage  = [],
			desc   = [],
			hopts  = ['-h', '--help', '-H'],
			prefix = '-',
			hbald  = True
		)
		self.__dict__['_params']    = OrderedDict()
		self.__dict__['_assembler'] = HelpAssembler(self._prog, theme)
		self.__dict__['_helpx']     = None

	def _setTheme(self, theme):
		"""
		Set the theme
		@params:
			`theme`: The theme
		"""
		self._assembler = HelpAssembler(self._prog, theme)
		return self

	def _setUsage(self, usage):
		"""
		Set the usage
		@params:
			`usage`: The usage
		"""
		self._props['usage'] = usage if isinstance(usage, list) else [usage]
		return self

	def _setDesc(self, desc):
		"""
		Set the description
		@params:
			`desc`: The description
		"""
		self._props['desc'] = desc if isinstance(desc, list) else [desc]
		return self

	def _setHopts(self, hopts):
		"""
		Set the help options
		@params:
			`hopts`: The help options
		"""
		self._props['hopts'] = hopts if isinstance(hopts, list) else \
			[ho.strip() for ho in hopts.split(',')]
		return self

	def __repr__(self):
		return '<Parameters({}) @ {}>'.format(','.join(
			p.name+':'+str(p.type) for p in self._params.values()
		), hex(id(self)))

	def __hash__(self):
		return id(self)

	def __eq__(self, other):
		return id(self) == id(other)

	def __ne__(self, other):
		return not self.__eq__(other)

	def _setPrefix(self, prefix):
		"""
		Set the option prefix
		@params:
			`prefix`: The prefix
		"""
		if not prefix:
			raise ParametersParseError('Empty prefix.')
		self._props['prefix'] = prefix
		return self

	def _setHbald(self, hbald = True):
		"""
		Set if we should show help information if no arguments passed.
		@params:
			`hbald`: The flag. show if True else hide. Default: `True`
		"""
		self._props['hbald'] = hbald
		return self

	def __setattr__(self, name, value):
		"""
		Change the value of an existing `Parameter` or create a `Parameter`
		using the `name` and `value`. If `name` is an attribute, return its value.
		@params:
			`name` : The name of the Parameter
			`value`: The value of the Parameter
		"""
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
		"""
		Get a `Parameter` instance if possible, otherwise return an attribute value
		@params:
			`name`: The name of the `Parameter` or the attribute
		@returns:
			A `Parameter` instance if `name` exists in `self._params`, otherwise,
			the value of the attribute `name`
		"""
		if name.startswith('__') or name.startswith('_Parameters'): # pragma: no cover
			return super(Parameters, self).__getattr__(name)
		elif not name in self._params:
			self._params[name] = Parameter(name, None)
		return self._params[name]

	def __setitem__(self, name, value):
		"""
		Compose a `Parameter` using the `name` and `value`
		@params:
			`name` : The name of the `Parameter`
			`value`: The value of the `Parameter`
		"""
		self._params[name] = Parameter(name, value)

	def __getitem__(self, name):
		"""
		Alias of `__getattr__`
		"""
		return getattr(self, name)

	def __call__(self, option, value):
		"""
		Set options values in `self._props`.
		Will be deprecated in the future!
		@params:
			`option`: The key of the option
			`value` : The value of the option
			`excl`  : The value is used to exclude (only for `hopts`)
		@returns:
			`self`
		"""
		setattr(self, '_' + option, value)
		return self

	def _parseName(self, argumentname):
		"""
		Parse an argument name
		@params:
			`argumentname`: The argumentname
		@returns:
			`argname`: clean argument name
			`argtype`: normalized argument type
			`subtype`: normalized subtype
			`argval`: the argument value, if `argumentname` is like: `-a=1`
		"""
		argname, argtype, subtype, argval = None, 'auto', 'auto', None
		if not argumentname.startswith(self._props['prefix']):
			# it's a value
			return argname, argtype, subtype, argval
		argumentname = argumentname[len(self._props['prefix']):]
		match = re.match(Parameters.ARG_NAME_PATTERN, argumentname)
		if not match:
			# it's not desired argument name
			return argname, argtype, subtype, argval
		argname = match.group(1)
		argtype = match.group(2)
		argval = match.group(3)
		if not argtype and argname in self._params and self._params[argname].type:
			argtype = self._params[argname].type
		argtype = argtype or 'auto'
		if ':' in argtype:
			# I have a subtype, n
			argtype, subtype = argtype.split(':', 1)
			argtype = Parameters.ARG_TYPES[argtype]
			subtype = Parameters.ARG_TYPES[subtype]
		else:
			argtype = Parameters.ARG_TYPES[argtype]

		if argname not in self._params:
			# return everything if argument is not defined
			return argname, argtype, subtype, argval

		# check if the parameter is defined and type is assigned
		if self._params[argname].type and self._params[argname].type.split(':', 1)[0] != argtype:
			# warn if type is different as definition
			sys.stderr.write(self._assembler.warning(
				('Decleared type "{dtype}" ignored, ' +
				'use "{ptype}" instead for option {prefix}{option}.\n').format(
					dtype  = self._params[argname].type,
					ptype  = argtype,
					prefix = self._props['prefix'],
					option = argname
				)
			))

		return argname, argtype, subtype, argval

	def _shouldPrintHelp(self, args):
		if self._props['hbald'] and not args:
			return True

		return any([arg in self._props['hopts'] for arg in args])

	@staticmethod
	def _coerceValue(value, typename = 'auto'):
		"""
		Coerce a value to another type.
		@params:
			`value`: The value
			`typename`: The type
		"""
		try:
			if typename == 'int' and not isinstance(value, int):
				return int(value)
			elif typename == 'float' and not isinstance(value, float):
				return float(value)
			elif typename == 'bool' and not isinstance(value, (int, bool)):
				if value in Parameters.VAL_TRUES:
					return True
				elif value in Parameters.VAL_FALSES:
					return False
				else:
					raise ParameterTypeError(
						typename, 'Unable to coerce value %s to bool' % (repr(value)))
			elif typename == 'py':
				return eval(value)
			elif typename == 'str':
				return str(value)
			elif typename == 'auto':
				try:
					if re.match(Parameters.ARG_VALINT_PATTERN, value):
						typename = 'int'
					elif re.match(Parameters.ARG_VALFLOAT_PATTERN, value):
						typename = 'float'
					elif re.match(Parameters.ARG_VALBOOL_PATTERN, value):
						typename = 'bool'
					else:
						typename = None
						match = re.match(Parameters.ARG_VALPY_PATTERN, value)
						if match:
							typename = 'py'
							value = match.group(1)
					return Parameters._coerceValue(value, typename)
				except TypeError: # value is not a string, cannot do re.match
					return value
			elif not typename is None and typename.startswith('list'):
				if isinstance(value, string_types):
					value = [value]
				else:
					try:
						value = list(value)
					except TypeError:
						value = [value]
				subtype = typename.split(':')[1] if ':' in typename else 'auto'
				if subtype == 'one':
					return [value]
				return [Parameters._coerceValue(x, subtype) for x in value]
			else:
				return value
		except (ValueError, TypeError):
			raise ParameterTypeError(
				typename, 'Unable to coerce value %s to type' % (repr(value)))

	def _putValue(self, argname, argtype, subtype, argval, arbi = False):
		"""
		Save the values.
		@params:
			`argname`: The option name
			`argtype`: The parsed type
			`argval`:  The option value
			`subtype`: The subtype of a list argument
			`arbi`:    Whether allow pass options arbitrarily (without definition)
		@return:
			`True` if value append to a list option successfully, otherwise `False`
		"""
		if argname not in self._params:
			if not arbi:
				sys.stderr.write(self._assembler.warning(
					'No such option: {}{}\n'.format(self._props['prefix'], argname)
				))
				return False
			else:
				# create an argument
				newparam = getattr(self, argname)
				if argtype != 'auto':
					newparam.type = argtype

		if argtype == 'list':
			if subtype is None or not self._params[argname].value:
				# reset the list
				self._params[argname].value = []
			if not isinstance(argval, list):
				argval = [argval]
			if subtype == 'one':
				if not self._params[argname].value:
					self._params[argname].value.append([])
				self._params[argname].value[0].extend(argval)
			elif subtype:
				self._params[argname].value.extend(
					[Parameters._coerceValue(aval, subtype) for aval in argval])
		else:
			self._params[argname].value = Parameters._coerceValue(argval, argtype)

	def parse (self, args = None, arbi = False):
		"""
		Parse the arguments.
		@params:
			`args`: The arguments (list). `sys.argv[1:]` will be used if it is `None`.
			`arbi`: Whether do an arbitrary parse.
				If True, options don'typename need to be defined. Default: `False`
		@returns:
			A `Box`/`dict` object containing all option names and values.
		"""
		args = sys.argv[1:] if args is None else args

		if self._shouldPrintHelp(args) and not arbi:
			self.help(print_and_exit = True)

		# split args in groups
		groups = [[]]
		for arg in args:
			if arg.startswith(self._props['prefix']):
				groups.append([])
			groups[-1].append(arg)

		setattr(self, Parameters.POSITIONAL, [])
		for group in groups:
			if not group:
				continue
			maybename = group.pop(0)
			argname, argtype, subtype, argvalue = self._parseName(maybename)
			if argname:
				if argvalue:
					group.insert(0, argvalue)

				if argtype == 'list':
					# reset list
					if not group:
						self._putValue(argname, argtype, None, None, arbi)
					else:
						self._putValue(argname, argtype, subtype, group, arbi)
				else:
					if not group and argtype and argtype != 'auto' and argtype != 'bool':
						# ignore argument without values
						continue
					# group or argtype == 'bool'
					if not group:
						self._putValue(argname, argtype, subtype, 'True', arbi)
					else:
						self._putValue(argname, argtype, subtype, group.pop(0), arbi)

					if group and self._params[Parameters.POSITIONAL].value:
						sys.stderr.write(self._assembler.warning(
							'Unexpected value(s): {}.\n'.format(', '.join(group))
						))
					elif group:
						self._putValue(Parameters.POSITIONAL, 'list', 'auto', group, arbi)
			else:
				self._putValue(Parameters.POSITIONAL, 'list', 'auto', [maybename] + group, arbi)

		# check the types, values of the params
		errors = []
		for name in self._params:
			if self._params[name].required and self._params[name].value is None:
				errors.append('Option {}{} is required.'.format(self._props['prefix'], name))
				continue
			if callable(self._params[name].callback):
				try:
					ret = self._params[name].callback(self._params[name])
				except TypeError as ex: # wrong # arguments
					if 'argument' not in str(ex):
						raise
					ret = self._params[name].callback(self._params[name], self)
				if ret is True or ret is None or isinstance(ret, Parameter):
					continue
				errors.extend([ret] if not isinstance(ret, list) else ret)
		if errors:
			self.help(error = errors, print_and_exit = True)

		return self.asDict()

	def help (self, error = '', print_and_exit = False):
		"""
		Calculate the help page
		@params:
			`error`: The error message to show before the help information. Default: `''`
			`print_and_exit`: Print the help page and exit the program?
				Default: `False` (return the help information)
		@return:
			The help information
		"""
		revparams = {}
		for key, val in self._params.items():
			if not val in revparams:
				revparams[val] = []
			revparams[val].append(key)

		posopt = None
		if Parameters.POSITIONAL in self._params:
			posopt = self._params[Parameters.POSITIONAL]
			if len(posopt.desc) == 1 and posopt.desc[0].startswith('Default: '):
				posopt = None

		required_options   = []
		optional_options   = []

		for val in revparams.keys():
			# options not suppose to show
			if not val.show or val.name == Parameters.POSITIONAL:
				continue
			option = (
				', '.join([self._props['prefix'] + k
					for k in sorted(revparams[val], key = len)]),
				(val.type or '').upper(),
				val.desc
			)
			if val.required:
				required_options.append(option)
			else:
				optional_options.append(option)

		if isinstance(posopt, Parameter):
			if posopt.required:
				required_options.append(('POSITIONAL', '', posopt.desc))
			else:
				optional_options.append(('POSITIONAL', '', posopt.desc))

		helpitems = OrderedDict()
		if self._props['desc']:
			helpitems['description'] = self._props['desc']

		if self._props['usage']:
			helpitems['usage'] = self._props['usage']
		else: # default usage
			defusage = ['{prog}']
			for optname, opttype, _ in required_options:
				if optname == 'POSITIONAL':
					continue
				defusage.append('<{} {}>'.format(
					optname,
					opttype or optname[len(self._props['prefix']):].upper())
				)
			if optional_options:
				defusage.append('[OPTIONS]')
			if isinstance(posopt, Parameter):
				defusage.append('POSITIONAL' if posopt.required else '[POSITIONAL]')

			helpitems['usage'] = [' '.join(defusage)]

		optional_options.append((
			', '.join(filter(None, self._props['hopts'])),
			'', ['Print this help information']))
		helpitems['required options'] = required_options
		helpitems['optional options'] = optional_options

		if callable(self._helpx):
			helpitems = self._helpx(helpitems)

		ret = []
		if error:
			if not isinstance(error, list):
				error = [error]
			ret = [self._assembler.error(err.strip()) for err in error]
		ret += self._assembler.assemble(helpitems, self._prog)

		if print_and_exit:
			sys.stderr.write('\n'.join(ret) + '\n')
			sys.exit(1)
		else:
			return '\n'.join(ret) + '\n'

	def loadDict (self, dict_var, show = False):
		"""
		Load parameters from a dict
		@params:
			`dict_var`: The dict variable.
			- Properties are set by "<param>.required", "<param>.show", ...
			`show`:    Whether these parameters should be shown in help information
				- Default: False (don'typename show parameter from config object in help page)
				- It'll be overwritten by the `show` property inside dict variable.
				- If it is None, will inherit the param's show value
		"""
		# load the param first
		for key, val in dict_var.items():
			if '.' in key: continue
			if not key in self._params:
				self._params[key] = Parameter(key, val)
			self._params[key].value = val
			if show is not None:
				self._params[key].show = show
		# then load property
		for key, val in dict_var.items():
			if '.' not in key: continue
			k, prop = key.split('.', 1)
			if not k in self._params:
				raise ParametersLoadError(
					key, 'Cannot set attribute of an undefined option %s' % repr(k))
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
				- Default: False (don'typename show parameter from config file in help page)
				- It'll be overwritten by the `show` property inside the config file.
		"""
		config = {}
		if cfgfile.endswith('.json'):
			with open(cfgfile) as fcfg:
				config = jsonLoads(fcfg.read())
		elif cfgfile.endswith('yml') or cfgfile.endswith('yaml'):
			import yaml
			with open(cfgfile) as fcfg:
				config = yaml.safe_load(fcfg)
		else:
			cparser = ConfigParser()
			cparser.optionxform = str
			cparser.read(cfgfile)
			sections = cparser.sections()
			config = {}
			for sec in sections:
				config.update(dict(cparser.items(sec)))

		for key, val in config.items():
			if key.endswith('.type'):
				config[key] = val
				if val.startswith('list') and \
					key[:-5] in config and \
					not isinstance(config[key[:-5]], list):

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
		"""
		Constructor
		@params:
			`theme`: The theme
		"""
		self.__dict__['_desc']      = []
		self.__dict__['_hcmd']      = 'help'
		self.__dict__['_cmds']      = OrderedDict()
		self.__dict__['_assembler'] = HelpAssembler(None, theme)
		self.__dict__['_helpx']     = None

	def _setDesc(self, desc):
		"""
		Set the description
		@params:
			`desc`: The description
		"""
		self.__dict__['_desc'] = desc if isinstance(desc, list) else [desc]
		return self

	def _setHcmd(self, hcmd):
		"""
		Set the help command
		@params:
			`hcmd`: The help command
		"""
		self.__dict__['_hcmd'] = hcmd
		return self

	def _setTheme(self, theme):
		"""
		Set the theme
		@params:
			`theme`: The theme
		"""
		self.__dict__['_assembler'] = HelpAssembler(None, theme)
		return self

	def __getattr__(self, name):
		"""
		Get the value of the attribute
		@params:
			`name` : The name of the attribute
		@returns:
			The value of the attribute
		"""
		if name.startswith('__') or name.startswith('_Commands'): # pragma: no cover
			return super(Commands, self).__getattr__(name)
		elif not name in self._cmds:
			self._cmds[name] = Parameters(name, self._assembler.theme)
		return self._cmds[name]

	def __setattr__(self, name, value):
		"""
		Set the value of the attribute
		@params:
			`name` : The name of the attribute
			`value`: The value of the attribute
		"""
		if name.startswith('__') or name.startswith('_Commands'): # pragma: no cover
			super(Commands, self).__setattr__(name, value)
		elif name == '_desc':
			self._setDesc(value)
		elif name == '_theme':
			self._setTheme(value)
		elif name == '_hcmd':
			self._setHcmd(value)
		elif name == '_helpx':
			self.__dict__['_helpx'] = value
		else:
			# alias
			if isinstance(value, Parameters):
				self._cmds[name] = value
				if name != value._prog.split()[-1]:
					value._prog += '|' + name
					value._assembler = HelpAssembler(value._prog, value._assembler.theme)
			else:
				if not name in self._cmds:
					self._cmds[name] = Parameters(name, self._assembler.theme)
				self._cmds[name]('desc', value if isinstance(value, list) else [value])

	def __getitem__(self, name):
		"""
		Alias of `__getattr__`
		"""
		return getattr(self, name)

	def parse(self, args = None, arbi = False):
		"""
		Parse the arguments.
		@params:
			`args`: The arguments (list). `sys.argv[1:]` will be used if it is `None`.
			`arbi`: Whether do an arbitrary parse.
				If True, options do not need to be defined. Default: `False`
		@returns:
			A `tuple` with first element the subcommand and second the parameters being parsed.
		"""
		args = sys.argv[1:] if args is None else args
		if arbi:
			if not args:
				return '', Box()
			else:
				command = args.pop(0)
				cmdps   = getattr(self, command)
				if isinstance(cmdps, Parameters):
					return command, cmdps.parse(args, arbi = True)
				return command, Box({Parameters.POSITIONAL: args})
		else:
			if not args or (len(args) == 1 and args[0] == self._hcmd):
				self.help(print_and_exit = True)

			command = args.pop(0)
			if (command == self._hcmd and args[0] not in self._cmds) or \
				(command != self._hcmd and command not in self._cmds):
				self.help(
					error = 'Unknown command: {}'.format(
						args[0] if command == self._hcmd else command),
					print_and_exit = True
				)
			if command == self._hcmd:
				self._cmds[args[0]].help(print_and_exit = True)

			return command, self._cmds[command].parse(args)

	def help(self, error = '', print_and_exit = False):
		"""
		Construct the help page
		@params:
			`error`: the error message
			`print_and_exit`: print the help page and exit instead of return the help information
		@returns:
			The help information if `print_and_exit` is `False`
		"""
		helpitems = OrderedDict()
		if self._desc:
			helpitems['description'] = self._desc

		helpitems['commands'] = []

		revcmds = OrderedDict()
		for key, val in self._cmds.items():
			if val not in revcmds:
				revcmds[val] = []
			revcmds[val].append(key)

		for key, val in revcmds.items():
			helpitems['commands'].append((' | '.join(val), '', key._props['desc']))
		helpitems['commands'].append(
			(self._hcmd, 'command', ['Print help information for the command']))

		if callable(self._helpx):
			helpitems = self._helpx(helpitems)

		ret = []
		if error:
			ret = [self._assembler.error(error.strip())]
		ret += self._assembler.assemble(helpitems)

		out = '\n'.join(ret) + '\n'
		if print_and_exit:
			sys.stderr.write(out)
			sys.exit(1)
		else:
			return out

# pylint: disable=invalid-name
params   = Parameters()
commands = Commands()
