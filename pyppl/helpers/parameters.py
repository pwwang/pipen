import sys
"""
Handling parameters
"""

class parameter (object):
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
		self.__dict__['props'] = {
			'desc'    : '',
			'required': False,
			'show'    : True,
			'type'    : None,
			'name'    : name,
			'value'   : value# if not isinstance(value, unicode) else value.encode('utf-8')
		}
		self.setType(type(self.value))
	
	def __setattr__(self, name, value):
		getattr(self, 'set' + name[0].upper() + name[1:])(value)
	
	def __getattr__(self, name):
		return self.props[name]
	
	def __repr__(self):
		return 'param({})[{}]'.format(','.join([key+'='+str(val) for key, val in self.props.items()]), hex(id(self)))
	
	def __str__(self):
		return str(self.value)
	
	def setDesc (self, d = ''):
		"""
		Set the description of the parameter
		@params:
			`d`: The description
		"""
		self.props['desc'] = d
		return self
		
	def setRequired (self, r = True):
		"""
		Set whether this parameter is required
		@params:
			`r`: True if required else False. Default: True
		"""
		if self.props['type'] == bool:
			raise ValueError('Bool option "{}" cannot be set as required.'.format(self.name))
		self.props['required'] = r
		return self
		
	def setType (self, t = str):
		"""
		Set the type of the parameter
		@params:
			`t`: The type of the value. Default: str
			- Note: str rather then 'str'
		"""
		if t not in [str, int, float, bool, list]:
			raise TypeError ('Unexpected type "{}", only support one of the types: [str, int, float, bool, list]'.format(t.__name__))
		self.props['type'] = t
		self._forceType()
		return self
	
	def setShow (self, s = True):
		"""
		Set whether this parameter should be shown in help information
		@params:
			`s`: True if it shows else False. Default: True
		"""
		self.props['show'] = s
		return self
		
	def setValue (self, v):
		"""
		Set the value of the parameter
		@params:
			`v`: The value
		"""
		self.props['value'] = v# if not isinstance(v, unicode) else v.encode('utf-8')
		return self
	
	def setName (self, n):
		"""
		Set the name of the parameter
		@params:
			`n`: The name
		"""
		self.props['name'] = n
		return self
		
	def _forceType (self):
		"""
		Coerce the value to the type specified
		TypeError will be raised if error happens
		"""
		try:
			self.value = self.type(self.value)
		except (ValueError, TypeError):
			sys.stderr.write('Cannot coerce value "{}" to type "{}" for {}'.format(str(self.value), self.type.__name__, repr(self)))
		
	def _printName (self, prefix):
		"""
		Get the print name with type for the parameter
		@params:
			`prefix`: The prefix of the option
		"""
		if self.type == bool:
			return prefix + self.name + ' (bool)'
			
		return prefix + self.name + ' <{}>'.format(self.type.__name__)

class parameters (object):
	
	def __init__(self):
		"""
		Constructor
		"""
		self.__dict__['props']  = {
			'_usage': '',
			'_example': '',
			'_desc': '',
			'_hopts': ['-h', '--help', '-H', '-?', ''],
			'_prefix': '--param-'
		}
		self.__dict__['params'] = {}
			
	def __setattr__(self, name, value):
		if name in self.params:
			self.params[name].setValue(value)
		self.params[name] = parameter(name, value)
		
	def __getattr__(self, name):
		if not name in self.params:
			self.params[name] = parameter(name, '')
		return self.params[name]
		
	def prefix (self, p):
		"""
		Set the prefix of options
		@params:
			`p`: The prefix. No default, but typically '--param-'
		"""
		self.props['_prefix'] = p
		return self
	
	def helpOpts (self, h):
		"""
		The options to popup help information
		An empty string '' implys help information pops up when no arguments specified
		@params:
			`h`: The options. It could be either list or comma separated.
		"""
		if not isinstance(h, list):
			h = map(strip, h.split(','))
		self.props['hopts'] = h
		return self
	
	def usage(self, u):
		"""
		Set the usage of the program. Otherwise it'll be automatically calculated.
		@params
			`u`: The usage, no program name needed. Multiple usages in multiple lines.
		"""
		self.props['_usage'] = u
		return self
		
	def example(self, e):
		"""
		Set the examples of the program
		@params:
			`e`: The examples. Multiple examples in multiple lines
		"""
		self.props['_example'] = e
		return self
		
	def desc(self, d):
		"""
		Set the description of the program
		@params:
			`d`: The description
		"""
		self.props['_desc'] = d
		return self
	
	def parse (self):
		"""
		Parse the arguments from `sys.argv`
		"""
		args = sys.argv[1:]
		if (not args and '' in self.props['_hopts']) or (set(filter(None, self.props['_hopts'])) & set(args)):
			sys.stderr.write (self._help())
			sys.exit (1)
		else:
			i = 0
			listKeysFirstHit = {}
			while i < len(args):
				arg  = args[i].split('=')
				karg = arg.pop(0)
				if karg.startswith(self.props['_prefix']):
					key = karg[len(self.props['_prefix']):]
					if key not in self.params:
						sys.stderr.write ('WARNING: Unkown option {}.\n'.format(karg))
					val = self.params[key]
					
					if val.type == bool:
						if arg or (i+1 < len(args) and not args[i+1].startswith(self.props['_prefix'])):
							val.value = arg[0] if arg else args[i+1]
							i += 1 if arg else 2
						else:
							val.value = True
							i += 1 if not arg else 2
					elif val.type == list:
						if key not in listKeysFirstHit:
							listKeysFirstHit[key] = True
							val.value = []
							
						if arg:
							val.value += arg
						j = i + 1
						while j < len(args) and not args[j].startswith(self.props['_prefix']):
							val.value.append (args[j])
							j += 1
						i = j 
					else:
						if arg:
							val.value = arg[0]
						else:
							if i+1 >= len(args) or args[i+1].startswith(self.props['_prefix']):
								raise ValueError('No value assigned for option: {}' % karg)
							val.value = args[i+1]
							i += 2				
						
				else:
					sys.stderr.write ('WARNING: Unused value found: {}.\n'.format(args[i]))
					i += 1
					
			for key, val in self.params.items():
				if val.required and not val.value:
					sys.stderr.write ('ERROR: Option {}{} is required.\n\n'.format(self.props['_prefix'], key))
					sys.stderr.write (self._help())
					sys.exit(1)
				if val.type == bool:
					if isinstance(val.value, bool):
						pass
					elif val.value.lower() in ['t', 'true', 'yes', 'y', '1', 'on', '']:
						val.value = True
					elif val.value.lower() in ['f', 'false', 'no', 'n', '0', 'off']:
						val.value = False
					else:
						raise ValueError('Cannot coerce "{}" to bool for option: {}, expect T[rue]/F[alse], Y[es]/N[o], 1/0 or on/off.'.format(val.value, val.name))
				try:
					val._forceType()
				except TypeError:
					sys.stderr.write('ERROR: Cannot coerce "{}" to {} for option: {}' % (val.value, val.type, karg))
				
		
	def _help (self):
		"""
		Calculate the help page
		@return:
			The help information
		"""
		ret = ''
		
		requiredOptions = {}
		optionalOptions = {}
		
		keylen = 40 # '--param-xxx'
		
		for key, val in self.params.items():
			if not val.show:
				continue
			if val.required:
				requiredOptions[key] = val
			else:
				optionalOptions[key] = val
			keylen = max(len(self.props['_prefix']) + 4 + len(key), keylen)
			
		keylen = max (4 + len(', '.join(filter(None, self.props['_hopts']))), keylen)
			
		if self.props['_desc']:
			ret += 'DESCRIPTION:\n'
			ret += '-----------\n'
			ret += '  ' + self.props['_desc'] + '\n\n'
		ret += 'USAGE:\n'
		ret += '-----\n'
		if self.props['_usage']:
			ret += '  ' + '\n	{}'.format(sys.argv[0]).join(list(self.props['_usage'])) + '\n\n'
		else:
			ret += '  ' + sys.argv[0]  \
				+ ('' if not requiredOptions else ' ' + ' '.join([val._printName(self.props['_prefix']) for key, val in requiredOptions.items()])) \
				+ ('' if not optionalOptions else ' [OPTIONS]') + '\n\n'
		if self.props['_example']:
			ret += 'EXAMPLE:\n'
			ret += '-------\n'
			ret += '  ' + '\n	'.join(list(self.props['_example'])) + '\n\n'
		
		if requiredOptions:
			ret += 'REQUIRED OPTIONS:\n'
			ret += '----------------\n'
			for key, val in requiredOptions.items():
				descs = val.desc.split("\n")
				ret  += '  {}'.format(val._printName(self.props['_prefix'])).ljust(keylen) + (descs.pop(0) if descs else '') + '\n'
				for desc in descs:
					ret += ''.ljust(keylen) + desc + '\n'
			ret += '\n'
		
		ret += 'OPTIONAL OPTIONS:\n'
		ret += '----------------\n'
		if optionalOptions:
			for key, val in optionalOptions.items():
				descs = (val.desc + ' ' if val.desc else '') + 'Default: ' + str(val)
				descs = descs.split("\n")
				ret  += '  {}'.format(val._printName(self.props['_prefix'])).ljust(keylen) \
					 + (descs.pop(0) if descs else '') + '\n'
				for desc in descs:
					ret += ''.ljust(keylen) + desc + '\n'
		ret += '  ' + ', '.join(filter(None, self.props['_hopts'])).ljust(keylen - 2) + 'Print this help information.\n\n'

		return ret
	
	def loadDict (self, dictVar, show = False):
		"""
		Load parameters from a dict
		@params:
			`dictVar`: The dict variable.
			- Properties are set by "<param>.required", "<param>.show", ...
			`show`:    Whether these parameters should be shown in help information
			- It'll be overwritten by the `show` property inside dict variable.
		"""
		for key, val in dictVar.items():
			if '.' in key: continue
			self.params[key] = parameter(key, val)
			self.params[key].show = show
		for key, val in dictVar.items():
			if '.' not in key: continue
			(k, _, prop) = key.rpartition('.')
			if not k in self.params:
				raise ValueError('Propterty set for undefined option: {}'.format(key))
			if not prop in ['desc', 'required', 'show', 'type']:
				raise ValueError('Unknown property "{}" for option: {}'.format(prop, k))
			
			setattr (self.params[k], prop, val)	
		return self
		
	def loadCfgfile (self, cfgfile, show = False):
		"""
		Load parameters from a json/config file
		If the file name ends with '.json', `json.load` will be used,
		otherwise, `ConfigParser` will be used.
		For config file other than json, a section name is needed, whatever it is.
		@params:
			`cfgfile`: The config file
			`show`:    Whether these parameters should be shown in help information
			- It'll be overwritten by the `show` property inside the config file.
		"""
		try:
			from ConfigParser import ConfigParser
		except ImportError:
			from configparser import ConfigParser
		from json import load
		config = {} 
		if cfgfile.endswith('.json'):
			with open(cfgfile) as f:
				config = load (f)
		else:
			cp = ConfigParser()
			cp.read(cfgfile)
			config = list(cp._sections.values())[0]
			for key, val in config.items():
				if key.endswith(".type"):
					config[key] = eval(val)
		self.loadDict(config, show = show)
		return self
		

params = parameters()