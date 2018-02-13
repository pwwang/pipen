"""
A set of exceptions used by PyPPL
"""

class TemplatePyPPLSyntaxError(Exception):
	"""
	Raised when a template has a syntax error.
	"""
	def __init__(self, name = None, src = None, msg = None):
		name = ': ' + repr(name) if name else ''
		src  = ' in "%s"' % src if src else ''
		msg  = msg or 'Template syntax error'
		super(Exception, self).__init__(str(msg) + src + name)

class TemplatePyPPLRenderError(Exception):
	"""
	Failed to render a template
	"""
	def __init__(self, stack, src = None):
		src = ' in ' + repr(src) if src else ''
		super(Exception, self).__init__(stack + src)

class LoggerThemeError(Exception):
	"""
	Theme errors for logger
	"""
	def __init__(self, name, msg = None):
		msg = msg or "Logger theme error"
		super(Exception, self).__init__(str(msg) + ': ' + repr(name))

class ParameterNameError(Exception):
	"""
	Malformat name not allowed
	"""
	def __init__(self, name, msg = None):
		msg = msg or "Parameter name error"
		super(Exception, self).__init__(str(msg) + ': ' + repr(name))

class ParameterTypeError(Exception):
	"""
	Unable to set type
	"""
	def __init__(self, name, msg = None):
		msg = msg or "Parameter type error"
		super(Exception, self).__init__(str(msg) + ': ' + repr(name))

class ParametersParseError(Exception):
	"""
	Error when parsing the parameters
	"""	
	def __init__(self, name, msg = None):
		msg = msg or 'Error when parsing command line arguments.'
		super(Exception, self).__init__(str(msg) + ': ' + repr(name))

class ParametersLoadError(Exception):
	"""
	Error loading dict to Parameters
	"""	
	def __init__(self, name, msg = None):
		msg = msg or 'Error loading dict to Parameters.'
		super(Exception, self).__init__(str(msg) + ': ' + repr(name))
