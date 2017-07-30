import sys

class parameter (object):
	def __init__(self, name, value):
		self.__dict__['props'] = {
			'desc'    : '',
			'required': False,
			'show'    : True,
			'type'    : None,
			'name'    : name,
			'value'   : value
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
		self.props['desc'] = d
		return self
		
	def setRequired (self, r = True):
		if self.props['type'] == bool:
			raise ValueError('Bool option "{}" cannot be set as required.'.format(self.name))
		self.props['required'] = r
		return self
		
	def setType (self, t = str):
		if t not in [str, int, float, bool, list]:
			raise TypeError ('Unexpected type "{}", only support one of the types: [str, int, float, bool, list]'.format(t.__name__))
		self.props['type'] = t
		self._forceType()
		return self
	
	def setShow (self, s = True):
		self.props['show'] = s
		return self
		
	def setValue (self, v):
		self.props['value'] = v
		self.props['type']  = type(v)
	
	def setName (self, n):
		self.props['name'] = n
		
	def _forceType (self):
		self.value = self.type(self.value)
		
	def _printName (self):
		if self.type == bool:
			return parameters.prefix + self.name + ' (bool)'
			
		return parameters.prefix + self.name + ' <{}>'.format(self.type.__name__)

class parameters (object):
	
	helpOpts = ['-h', '--help', '-H', '-?']
	prefix   = '--param-'
	
	def __init__(self):
		self.__dict__['props']  = {
			'_usage': '',
			'_example': '',
			'_desc': ''
		}
		self.__dict__['params'] = {}
			
	def __setattr__(self, name, value):
		self.params[name] = parameter(name, value)
		
	def __getattr__(self, name):
		if not name in self.params:
			self.params[name] = parameter(name, '')
		return self.params[name]
	
	def usage(self, u):
		self.props['_usage'] = u
		return self
		
	def example(self, e):
		self.props['_example'] = e
		return self
		
	def desc(self, d):
		self.props['_desc'] = d
		return self
	
	def parse (self):
		args = sys.argv[1:]
		if not args or (set(self.helpOpts) & set(args)):
			sys.stderr.write (self._help())
			sys.exit (1)
		else:
			i = 0
			while i < len(args):
				arg  = args[i].split('=')
				karg = arg.pop(0)
				if karg.startswith('--param-'):
					key = karg[8:]
					if key not in self.params:
						sys.stderr.write ('WARNING: Unkown option {}.\n'.format(karg))
					val = self.params[key]
					
					if val.type == bool:
						if arg or (i+1 < len(args) and not args[i+1].startswith('--param-')):
							val.value = arg[0] if arg else args[i+1]
							i += 1 if arg else 2
						else:
							val.value = True
							i += 1 if not arg else 2
					elif val.type == list:
						if arg:
							val.value += arg
						j = i + 1
						while j < len(args) and not args[j].startswith('--param-'):
							val.value.append (args[j])
							j += 1
						i = j 
					else:
						if arg:
							val.value = arg[0]
						else:
							if i+1 >= len(args) or args[i+1].startswith('--param-'):
								raise ValueError('No value assigned for option: {}' % karg)
							val.value = args[i+1]
							i += 1				
						
				else:
					sys.stderr.write ('WARNING: Unused value found: {}.\n'.format(args[i]))
					i += 1
					
			for key, val in self.params.items():
				if val.required and not val.value:
					sys.stderr.write ('ERROR: Option --param-{} is required.\n\n'.format(key))
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
			keylen = max(11 + len(key), keylen)
			
		if self.props['_desc']:
			ret += 'DESCRIPTION:\n'
			ret += '-----------\n'
			ret += '  ' + self.props['_desc'] + '\n\n'
		ret += 'USAGE:\n'
		ret += '-----\n'
		if self.props['_usage']:
			ret += '  ' + sys.argv[0] + ' ' + self.props['_usage'] + '\n\n'
		else:
			ret += '  ' + sys.argv[0] + ' ' \
				+ ('' if not requiredOptions else ' '.join([val._printName() for key, val in requiredOptions.items()])) \
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
				ret  += '  {}:'.format(val._printName()).ljust(keylen) + (descs.pop(0) if descs else '') + '\n'
				for desc in descs:
					ret += ''.ljust(keylen) + desc + '\n'
			ret += '\n'
		
		if optionalOptions:
			ret += 'OPTIONAL OPTIONS:\n'
			ret += '----------------\n'
			for key, val in optionalOptions.items():
				descs = (val.desc + ' ' if val.desc else '') + 'Default: ' + str(val)
				descs = descs.split("\n")
				ret  += '  {}:'.format(val._printName()).ljust(keylen) \
					 + (descs.pop(0) if descs else '') + '\n'
				for desc in descs:
					ret += ''.ljust(keylen) + desc + '\n'
			ret += '\n'
				
		return ret
	
	def loadDict (self, dictVar, show = False):
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
		
	def loadCfgfile (self, cfgfile, show = False):
		from ConfigParser import ConfigParser
		from json import load
		config = {} 
		if cfgfile.endswith('.json'):
			config = load (open(cfgfile))
		else:
			cp = ConfigParser()
			cp.read(cfgfile)
			config = cp._sections['Params']
		self.loadDict(config, show = show)
		

params = parameters()