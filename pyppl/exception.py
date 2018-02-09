"""
A set of exceptions used by PyPPL
"""

class TemplatePyPPLSyntaxUnclosedTag(Exception):
	"""
	Raised when a template has an unmatched tag syntax error.
	"""
	def __init__(self, tag):
		super(Exception, self).__init__('Unclosed template tag: ' + tag)

class TemplatePyPPLSyntaxMalformKeyword(Exception):
	"""
	Raised when a template has a malformed keyword syntax error.
	"""
	def __init__(self, keyword, src):
		super(Exception, self).__init__('Cannot understand "%s" in %s' % (keyword, src))

class TemplatePyPPLSyntaxDotError(Exception):
	"""
	Raised when a template has a dot syntax error.
	"""
	def __init__(self, var, dot):
		super(Exception, self).__init__('Cannot find an attribute/subscribe/index named "%s" for "%s"' % (dot, var))

class TemplatePyPPLSyntaxNameError(Exception):
	"""
	Raised when a template has a name syntax error.
	"""
	def __init__(self, name, src):
		super(Exception, self).__init__('Invalid variable name "%s" in "%s"' % (name, src))

class TemplatePyPPLSyntaxNewline(Exception):
	"""
	No new line is allowed in a template block
	"""
	def __init__(self, token):
		super(Exception, self).__init__('No newline is allowed in block: ' + token)

class TemplatePyPPLRenderError(Exception):
	"""
	Failed to render a template
	"""
	def __init__(self, stack, src):
		super(Exception, self).__init__(stack + ', ' + src)