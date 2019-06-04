"""
parameters module for PyPPL
"""
import sys
import re
import ast
import textwrap
from os import path
from collections import OrderedDict
import colorama
from simpleconf import Config
from cmdy import _Valuable
from .utils import Box, OBox, Hashable
from .exceptions import ParameterNameError, ParameterTypeError, \
	ParametersParseError, ParametersLoadError

# the max width of the help page, not including the leading space
MAX_PAGE_WIDTH = 100
# the max width of the option name (include the type and placeholder, but not the leading space)
MAX_OPT_WIDTH  = 36
# the min gap between optname/opttype and option description
MIN_OPT_GAP    = 5

THEMES = dict(
	default = dict(
		error   = colorama.Fore.RED,
		warning = colorama.Fore.YELLOW,
		title   = colorama.Style.BRIGHT + colorama.Fore.CYAN,  # section title
		prog    = colorama.Style.BRIGHT + colorama.Fore.GREEN, # program name
		default = colorama.Fore.MAGENTA,              # default values
		optname = colorama.Style.BRIGHT + colorama.Fore.GREEN,
		opttype = colorama.Fore.BLUE,
		optdesc = ''),

	blue = dict(
		error   = colorama.Fore.RED,
		warning = colorama.Fore.YELLOW,
		title   = colorama.Style.BRIGHT + colorama.Fore.GREEN,
		prog    = colorama.Style.BRIGHT + colorama.Fore.BLUE,
		default = colorama.Fore.MAGENTA,
		optname = colorama.Style.BRIGHT + colorama.Fore.BLUE,
		opttype = colorama.Style.BRIGHT,
		optdesc = ''),

	plain = dict(
		error   = '', warning = '', title   = '', prog    = '',
		default = '', optname = '', opttype = '', optdesc = '')
)

ALLOWED_OPT_TYPES = ('str', 'int', 'float', 'bool', 'list', 'py', 'none', 'dict')

OPT_TYPE_MAPPINGS = dict(
	a = 'auto',  auto  = 'auto',  i = 'int',   int   = 'int',  n = 'none', none = 'none',
	f = 'float', float = 'float', b = 'bool',  bool  = 'bool', d = 'dict', dict = 'dict',
	s = 'str',   str   = 'str',   o = 'one',   one   = 'one',  box = 'dict',
	p = 'py',    py    = 'py',    python = 'py',
	l = 'list',  list  = 'list',  array  = 'list',
)

OPT_BOOL_TRUES  = [True , 1, 't', 'T', 'True' , 'TRUE' , 'true' , '1', 'Y', 'y', 'Yes',
	'YES', 'yes', 'on' , 'ON' , 'On' ]

OPT_BOOL_FALSES = [False, 0, 'f', 'F', 'False', 'FALSE', 'false', '0', 'N', 'n', 'No' ,
	'NO' , 'no' , 'off', 'OFF', 'Off', None]

OPT_NONES = [None, 'none', 'None']

OPT_PATTERN       = r"^([a-zA-Z][\w,\._-]*)(?::([\w:]+))?(?:=(.*))?$"
OPT_INT_PATTERN   = r'^[+-]?\d+$'
OPT_FLOAT_PATTERN = r'^[+-]?(?:\d*\.)?\d+(?:[Ee][+-]\d+)?$'
OPT_NONE_PATTERN  = r'^none|None$'
OPT_BOOL_PATTERN  = r'^(t|T|True|TRUE|true|1|Y|y|Yes|YES|yes|on|ON|On|f|F|False' + \
	r'|FALSE|false|0|N|n|No|NO|off|Off|OFF|None|none)$'
OPT_PY_PATTERN    = r'^(?:py|repr):(.+)$'

OPT_POSITIONAL_KEY = '_'

class HelpAssembler:
	"""A helper class to help assembling the help information page."""
	def __init__(self, prog = None, theme = 'default'):
		"""
		Constructor
		@params:
			`prog`: The program name
			`theme`: The theme. Could be a name of `THEMES`, or a dict of a custom theme.
		"""
		self.progname = prog or path.basename(sys.argv[0])
		self.theme    = theme if isinstance(theme, dict) else THEMES[theme]

	def error(self, msg, with_prefix = True):
		"""
		Render an error message
		@params:
			`msg`: The error message
		"""
		msg = msg.format(prog = self.prog(self.progname))
		return '{colorstart}{prefix}{msg}{colorend}'.format(
			colorstart = self.theme['error'],
			prefix     = 'Error: ' if with_prefix else '',
			msg        = msg,
			colorend   = colorama.Style.RESET_ALL
		)

	def warning(self, msg, with_prefix = True):
		"""
		Render an warning message
		@params:
			`msg`: The warning message
		"""
		msg = msg.format(prog = self.prog(self.progname))
		return '{colorstart}{prefix}{msg}{colorend}'.format(
			colorstart = self.theme['warning'],
			prefix     = 'Warning: ' if with_prefix else '',
			msg        = msg,
			colorend   = colorama.Style.RESET_ALL
		)

	def title(self, msg, with_colon = True):
		"""
		Render an section title
		@params:
			`msg`: The section title
		"""
		return '{colorstart}{msg}{colorend}{colon}'.format(
			colorstart = self.theme['title'],
			msg        = msg.upper(),
			colorend   = colorama.Style.RESET_ALL,
			colon      = ':' if with_colon else ''
		)

	def prog(self, prog = None):
		"""
		Render the program name
		@params:
			`msg`: The program name
		"""
		if prog is None:
			prog = self.progname
		return '{colorstart}{prog}{colorend}'.format(
			colorstart = self.theme['prog'],
			prog       = prog,
			colorend   = colorama.Style.RESET_ALL
		)

	def plain(self, msg):
		"""
		Render a plain message
		@params:
			`msg`: the message
		"""
		return msg.format(prog = self.prog(self.progname))

	def optname(self, msg, prefix = '  '):
		"""
		Render the option name
		@params:
			`msg`: The option name
		"""
		return '{colorstart}{prefix}{msg}{colorend}'.format(
			colorstart = self.theme['optname'],
			prefix     = prefix,
			msg        = msg,
			colorend   = colorama.Style.RESET_ALL
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
			colorend   = colorama.Style.RESET_ALL
		) + ' ' * (len(msg) - len(trimmedmsg))

	def optdesc(self, msg, first = False):
		"""
		Render the option descriptions
		@params:
			`msg`: the option descriptions
		"""
		msg = msg.format(prog = self.prog(self.progname))

		default_index = msg.rfind('DEFAULT: ')
		if default_index == -1:
			default_index = msg.rfind('Default: ')

		if default_index != -1:
			defaults = '{colorstart}{defaults}{colorend}'.format(
				colorstart = self.theme['default'],
				defaults   = msg[default_index:],
				colorend   = colorama.Style.RESET_ALL
			)
			msg = msg[:default_index] + defaults

		return '{prefix}{colorstart}{msg}{colorend}'.format(
			prefix     = '- ' if first else '  ',
			colorstart = self.theme['optdesc'],
			msg        = msg,
			colorend   = colorama.Style.RESET_ALL
		)

	def assemble(self, helps):
		"""
		Assemble the whole help page.
		@params:
			`helps`: The help items. A list with plain strings or tuples of 3 elements, which
				will be treated as option name, option type/placeholder and option descriptions.
			`progname`: The program name used to replace '{prog}' with.
		@returns:
			lines (`list`) of the help information.
		"""

		ret = []
		for title, helpitems in helps.items():
			ret.append(self.title(title))
			if not any(isinstance(item, tuple) for item in helpitems):
				for item in helpitems:
					ret.extend('  ' + self.plain(it)
							   for it in textwrap.wrap(item, MAX_PAGE_WIDTH - 2))
				continue

			helpitems = [item if isinstance(item, tuple) else ('', '', item)
						 for item in helpitems]
			# 5 = <first 2 spaces: 2> +
			#     <gap between name and type: 1> +
			#     <brackts around type: 2>
			maxoptwidth = max(len(item[0] + item[1]) + MIN_OPT_GAP + 5
							  for item in helpitems
							  if len(item[0] + item[1]) + MIN_OPT_GAP + 5 <= MAX_OPT_WIDTH)

			for optname, opttype, optdesc in helpitems:
				descs = sum((textwrap.wrap(desc, MAX_PAGE_WIDTH - maxoptwidth)
							for desc in optdesc), [])
				optlen = len(optname + opttype) + MIN_OPT_GAP + 5
				if optlen > MAX_OPT_WIDTH:
					ret.append(
						self.optname(optname, prefix = '  ') + ' ' + self.opttype(opttype))
					if descs:
						ret.append(' ' * maxoptwidth + self.optdesc(descs.pop(0), True))
				else:
					to_append = self.optname(optname, prefix = '  ') + ' ' + \
								self.opttype(opttype.ljust(maxoptwidth - len(optname) - 5))
					if descs:
						to_append += self.optdesc(descs.pop(0), True)
					ret.append(to_append)
				if descs:
					ret.extend(' ' * maxoptwidth + self.optdesc(desc) for desc in descs)
		ret.append('')
		return ret

class Parameter(Hashable, _Valuable):
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
		self._desc     = []
		self._required = False
		self.show      = True
		self.type      = None
		self.name      = name
		self.value     = None
		self.tstack    = []
		self.vstack    = []
		self.callback  = None

		# We cannot change name later on
		if not isinstance(name, str):
			raise ParameterNameError(name, 'Not a string')
		if not re.search(r'^[A-Za-z0-9_,\-.]{1,255}$', name):
			raise ParameterNameError(name,
				'Expect a string with comma, alphabetics ' +
				'and/or underlines in length 1~255, but we got')

		self.parse()

	def parse(self):
		pass

	@property
	def desc(self):
		return self._desc

	@desc.setter
	def desc(self, description):
		assert isinstance(description, (list, str))
		if isinstance(description, str):
			description = description.splitlines()
		if not description:
			description.append('')
		if not self.required and not 'DEFAULT: ' in description[-1] and \
			'Default: ' not in description[-1]:
			if description[-1]:
				description[-1] += ' '
			description[-1] += 'Default: ' + repr(self.value)
		self._desc = description

	@property
	def required(self):
		return self._required

	@required.setter
	def required(self, req):
		if self.type == 'bool':
			raise ParameterTypeError(
				self.value, 'Bool option %r cannot be set as required' % self.name)
		self._required = req

	@property
	def type(self):
		return self._props.type

	@type.setter
	def type(self, typename):
		if not isinstance(typename, str):
			typename = typename.__name__
		tcolon = typename if ':' in typename else typename + ':'
		type1, type2 = tcolon.split(':', 1)
		type1 = OPT_TYPE_MAPPINGS.get(type1, type1)
		type2 = OPT_TYPE_MAPPINGS.get(type2, type2)

		t2use = type1 + ':' + type2 if type2 else type1
		if t2use not in ALLOWED_OPT_TYPES and not t2use.startswith('list'):
			raise ParameterTypeError(typename, 'Unsupported type for option %r' % self.name)

		self._props.type = t2use
		if self.value is not None:
			self.value = Parameter.forceType(self.value, t2use)

	@staticmethod
	def forceType(value, typename):
		if not typename:
			return value
		try:
			if typename in ('int', 'float', 'str'):
				return __builtins__[typename](value)

			if typename == 'bool':
				if value in OPT_BOOL_TRUES:
					return True
				if value in OPT_BOOL_FALSES:
					return False
				raise ParameterTypeError(typename, 'Unable to coerce value %r to bool' % value)

			if typename == 'none':
				if not value in OPT_NONES:
					raise ParameterTypeError(typename, 'Unexpected value %r for NoneType' % value)
				return None

			if typename == 'py':
				value = value[3:] if value.startswith('py:') else \
						value[5:] if value.startswith('repr:') else value
				return ast.literal_eval(value)

			if typename == 'dict':
				if not isinstance(value, dict):
					if not value:
						value = {}
					try:
						value = dict(value)
					except TypeError:
						raise ParameterTypeError(typename, 'Cannot coerce %r to dict.' % value)
				return OBox(value.items())

			if typename == 'auto':
				try:
					if re.match(OPT_NONE_PATTERN, value):
						typename = 'none'
					elif re.match(OPT_INT_PATTERN, value):
						typename = 'int'
					elif re.match(OPT_FLOAT_PATTERN, value):
						typename = 'float'
					elif re.match(OPT_BOOL_PATTERN, value):
						typename = 'bool'
					elif re.match(OPT_PY_PATTERN, value):
						typename = 'py'
					else:
						typename = 'str'
					return Parameter.forceType(value, typename)
				except TypeError: # value is not a string, cannot do re.match
					return value

			if typename.startswith('list'):
				if isinstance(value, str):
					value = [value]
				try:
					value = list(value)
				except TypeError:
					value = [value]
				subtype = typename[5:] or 'auto'
				if subtype == 'one':
					return [value]
				return [Parameter.forceType(x, subtype) for x in value]

			raise TypeError
		except (ValueError, TypeError):
			raise ParameterTypeError(typename, 'Unable to coerce value %r to type' % value)


	def __repr__(self):
		return '<Parameter({}) @ {}>'.format(
			','.join('%s=%r' % (key, val) for key,val in sorted(self._props.items())),
			hex(id(self)))

	def setDesc (self, desc):
		"""
		Set the description of the parameter
		@params:
			`desc`: The description
		"""
		self.desc = desc
		return self

	def setRequired (self, req = True):
		"""
		Set whether this parameter is required
		@params:
			`req`: True if required else False. Default: True
		"""
		self.required = req
		return self

	def setType (self, typename = 'str'):
		"""
		Set the type of the parameter
		@params:
			`typename`: The type of the value. Default: str
			- Note: str rather then 'str'
		"""
		self.type = typename
		return self

	def setCallback(self, callback):
		"""
		Set callback
		@params:
			`callback`: The callback
		"""
		self.callback = callback
		return self

	def setShow (self, show = True):
		"""
		Set whether this parameter should be shown in help information
		@params:
			`show`: True if it shows else False. Default: True
		"""
		self.show = show
		return self

	def setValue(self, val):
		"""
		Set the value of the parameter
		@params:
			`val`: The value
		"""
		self.value = val
		return self

	def isList(self):
		return self.type in ('l', 'list', 'array')

class Parameters (Hashable):
	"""
	A set of parameters
	"""

	def __init__(self, command = None, theme = 'default'):
		"""
		Constructor
		@params:
			`command`: The sub-command
			`theme`: The theme
		"""
		prog = path.basename(sys.argv[0])
		prog = prog + ' ' + command if command else prog
		self.__dict__['_props'] = Box(
			prog      = prog,
			usage     = [],
			desc      = [],
			hopts     = ['-h', '--help', '-H'],
			prefix    = '-',
			hbald     = True,
			assembler = HelpAssembler(prog, theme),
			helpx     = None
		)
		self.__dict__['_params']    = OBox()

	def __setattr__(self, name, value):
		"""
		Change the value of an existing `Parameter` or create a `Parameter`
		using the `name` and `value`. If `name` is an attribute, return its value.
		@params:
			`name` : The name of the Parameter
			`value`: The value of the Parameter
		"""
		if name.startswith('__') or name.startswith('_Parameters'):
			super(Parameters, self).__setattr__(name, value)
		elif isinstance(value, Parameter):
			self._params[name] = value
		elif name in self._params:
			self._params[name].value = value
		elif name in ['_' + key for key in self._props.keys()
					  if key not in ('prog', 'assembler', 'helpx')] + ['_theme']:
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
		if name.startswith('__') or name.startswith('_Parameters'):
			return super(Parameters, self).__getattr__(name)
		elif name in ['_' + key for key in self._props.keys()]:
			return self._props[name[1:]]
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

	def _setTheme(self, theme):
		"""
		Set the theme
		@params:
			`theme`: The theme
		"""
		self._props.assembler = HelpAssembler(self._prog, theme)
		return self

	def _setUsage(self, usage):
		"""
		Set the usage
		@params:
			`usage`: The usage
		"""
		assert isinstance(usage, (list, str))
		self._props.usage = usage if isinstance(usage, list) else usage.splitlines()
		return self

	def _setDesc(self, desc):
		"""
		Set the description
		@params:
			`desc`: The description
		"""
		assert isinstance(desc, (list, str))
		self._props.desc = desc if isinstance(desc, list) else desc.splitlines()
		return self

	def _setHopts(self, hopts):
		"""
		Set the help options
		@params:
			`hopts`: The help options
		"""
		assert isinstance(hopts, (list, str))
		self._props.hopts = hopts if isinstance(hopts, list) else \
			[ho.strip() for ho in hopts.split(',')]
		return self

	def _setPrefix(self, prefix):
		"""
		Set the option prefix
		@params:
			`prefix`: The prefix
		"""
		if not prefix:
			raise ParametersParseError('Empty prefix.')
		self._props.prefix = prefix
		return self

	def _setHbald(self, hbald = True):
		"""
		Set if we should show help information if no arguments passed.
		@params:
			`hbald`: The flag. show if True else hide. Default: `True`
		"""
		self._props.hbald = hbald
		return self

	def __repr__(self):
		return '<Parameters({}) @ {}>'.format(','.join(
			'{p.name}:{p.type}'.format(p = param) for param in self._params.values()
		), hex(id(self)))

	def _preParse(self, args):
		"""
		Parse the arguments from command line
		Don't coerce the types and values yet.
		"""
		parsed   = OBox()
		pendings = []
		lastopt  = None
		for arg in args:
			if arg.startswith(self._prefix):
				argtoparse = arg[len(self._preParse):]
				matches = re.match(OPT_PATTERN, argtoparse)
				if not matches:
					raise ParametersParseError('Unable to parse option: %r' % arg)
				argname = matches.group(1)
				argtype = matches.group(2)
				argval  = matches.group(3)

				if argname not in parsed:
					opt = Parameter(argname, None)
					opt._props.type = []
					opt._props.value = []
					parsed[argname] = opt
				opt = parsed[argname]

				if argtype and argtype not in opt._props.type:
					opt._props.type.append(argtype)
				if argval:
					opt._props.value.append(argval)

				lastopt = opt

			elif not lastopt:
				pendings.append(arg)
			else:
				lastopt._props.value.append(arg)

	@staticmethod
	def _computeParam(param):
		warns = []
		if len(param.type) > 1:
			warns.append('Type %r set earlier for option %r will be overwritten by %r' % (
				', '.join(param.type[:-1]),
				param.name, param.type[-1]))
			param._props.type = param.type[-1]

		if param.type:
			if not param.type.startswith('list'):
				param.value = param.value[-1]
			# trigger type conversion

			param.type  = param.type
		return warns

	def parse(self, args = None, arbi = False):
		args = sys.argv[1:] if args is None else args
		try:
			parsed, pendings = self._preParse(args)
			if pendings:
				if not parsed:
					parsed[OPT_POSITIONAL_KEY] = Parameter(OPT_POSITIONAL_KEY, pendings)
				else:
					for pend in pendings:
						sys.stderr.write(self._assembler.warn('Unexpected value: %r' % pend) + "\n")

			for name, param in parsed.items():
				if not arbi and name not in self._params:
					sys.stderr.write(self._assembler.warn('Unexpected option: %r' % name) + "\n")
				elif name in self._params:
					if not param.type:


					if len(param.type) > 1:
						warn = 'Type %r set earlier for option %r will be overwritten by %r' % (
							', '.join(param.type[:-1]),
							name, param.type[-1])
						argtype = param.type[-1]




			return self.asDict()
		except ParametersParseError as ex:
			self.help(str(ex), print_and_exit = True)





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
		OPTch = re.match(Parameters.ARG_NAME_PATTERN, argumentname)
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
			argtype = OPT_TYPE_MAPPINGS[argtype]
			subtype = OPT_TYPE_MAPPINGS[subtype]
		else:
			argtype = OPT_TYPE_MAPPINGS[argtype]

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
		return Parameter.forceType(value, typename)

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
			if '.' in key:
				continue
			if not key in self._params:
				self._params[key] = Parameter(key, val)
			self._params[key].value = val
			if show is not None:
				self._params[key].show = show
		# then load property
		for key, val in dict_var.items():
			if '.' not in key:
				continue
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
		config = Config(with_profile = False)
		config._load(cfgfile)

		for key, val in config.items():
			if key.endswith('.type'):
				conf[key] = val
				if val.startswith('list') and \
					key[:-5] in config and \
					not isinstance(config[key[:-5]], list):

					config[key[:-5]] = config[key[:-5]].strip().splitlines()

			elif key.endswith('.show') or key.endswith('.required'):
				if isinstance(val, bool):
					continue
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
