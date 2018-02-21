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
		msg = msg or 'Error when parsing command line arguments'
		super(Exception, self).__init__(str(msg) + ': ' + repr(name))

class ParametersLoadError(Exception):
	"""
	Error loading dict to Parameters
	"""	
	def __init__(self, name, msg = None):
		msg = msg or 'Error loading dict to Parameters'
		super(Exception, self).__init__(str(msg) + ': ' + repr(name))

class ProcTreeProcExists(Exception):
	"""
	Raise when two Procs with same id and tag defined
	"""	
	def __init__(self, pn1, pn2):
		msg = [
			"There are two processes with id(%s) and tag(%s)" % (pn1.proc.id, pn1.proc.tag),
			">>> One is defined here:",
			''.join(pn1.defs),
			">>> The other is defined here:",
			''.join(pn2.defs)
		]
		super(Exception, self).__init__("\n".join(msg))

class ProcTreeParseError(Exception):
	"""
	Raise when failed to parse the tree
	"""
	def __init__(self, name, msg = None):
		msg = msg or 'Failed to parse the process tree'
		super(Exception, self).__init__(str(msg) + ': ' + repr(name))

class JobInputParseError(Exception):
	"""
	Raise when failed to parse the input data for jobs
	"""
	def __init__(self, name, msg = None):
		msg = msg or 'Failed to parse the input data'
		super(Exception, self).__init__(str(msg) + ': ' + repr(name))

class JobBringParseError(Exception):
	"""
	Raise when failed to parse the bring data for jobs
	"""
	def __init__(self, name, msg = None):
		msg = msg or 'Failed to parse the bring data'
		super(Exception, self).__init__(str(msg) + ': ' + repr(name))

class JobOutputParseError(Exception):
	"""
	Raise when failed to parse the output data for jobs
	"""
	def __init__(self, name, msg = None):
		msg = msg or 'Failed to parse the output data'
		super(Exception, self).__init__(str(msg) + ': ' + repr(name))

class RunnerSshError(Exception):
	"""
	Raise when failed to initiate RunnerSsh
	"""
	def __init__(self, msg = 'Failed to initiate RunnerSsh'):
		super(Exception, self).__init__(str(msg))