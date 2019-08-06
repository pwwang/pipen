"""
A set of exceptions used by PyPPL
"""
class ProcTreeProcExists(Exception):
	"""Raise when two Procs with same id and tag defined"""
	def __init__(self, pn1, pn2):
		msg = [
			"There are two processes with id(%s) and tag(%s)" % (pn1.proc.id, pn1.proc.tag),
			"",
			">>> One is defined here:",
			''.join(pn1.defs),
			">>> The other is defined here:",
			''.join(pn2.defs)
		]
		super(ProcTreeProcExists, self).__init__("\n".join(msg))

class ProcTreeParseError(Exception):
	"""Raise when failed to parse the tree"""
	def __init__(self, name, msg = None):
		msg = msg or 'Failed to parse the process tree'
		super(ProcTreeParseError, self).__init__(str(msg) + ': ' + repr(name))

class JobInputParseError(Exception):
	"""Raise when failed to parse the input data for jobs"""
	def __init__(self, name, msg = None):
		msg = msg or 'Failed to parse the input data'
		super(JobInputParseError, self).__init__(str(msg) + ': ' + str(name))

class JobOutputParseError(Exception):
	"""Raise when failed to parse the output data for jobs"""
	def __init__(self, name, msg = None):
		msg = msg or 'Failed to parse the output data'
		super(JobOutputParseError, self).__init__(str(msg) + ': ' + repr(name))

class RunnerSshError(Exception):
	"""Raise when failed to initiate RunnerSsh"""
	def __init__(self, msg = 'Failed to initiate RunnerSsh'):
		super(RunnerSshError, self).__init__(str(msg))

class ProcTagError(Exception):
	"""Raise when malformed tag is assigned to a process"""
	def __init__(self, msg = 'Failed to specify tag for process.'):
		super(ProcTagError, self).__init__(str(msg))

class ProcAttributeError(AttributeError):
	"""Raise when set/get process' attributes"""
	def __init__(self, name, msg = 'No such attribute'):
		super(ProcAttributeError, self).__init__(str(msg) + ': ' + repr(name))

class ProcInputError(Exception):
	"""Raise when failed to parse process input"""
	def __init__(self, name, msg = 'Failed to parse input'):
		super(ProcInputError, self).__init__(str(msg) + ': ' + repr(name))

class ProcOutputError(Exception):
	"""Raise when failed to parse process output"""
	def __init__(self, name, msg = 'Failed to parse output'):
		super(ProcOutputError, self).__init__(str(msg) + ': ' + repr(name))

class ProcScriptError(Exception):
	"""Raise when failed to parse process script"""
	def __init__(self, name, msg = 'Failed to parse process script'):
		super(ProcScriptError, self).__init__(str(msg) + ': ' + repr(name))

class ProcRunCmdError(Exception):
	"""Raise when failed to run before/after cmds for process"""
	def __init__(self, cmd, key, ex = ''):
		msg = 'Failed to run <%s>: %s\n\n' % (key, str(ex))
		msg += cmd
		super(ProcRunCmdError, self).__init__(msg)

class PyPPLProcRelationError(Exception):
	"""Raise when failed to parse the relation of processes"""
	def __init__(self, p, msg):
		super(PyPPLProcRelationError, self).__init__(str(msg) + ': ' + repr(p))

class JobFailException(Exception):
	"""Raise when a job failed to run"""

class JobSubmissionException(Exception):
	"""Raise when a job failed to submit"""

class JobBuildingException(Exception):
	"""Raise when a job failed to build"""

class RunnerClassNameError(Exception):
	"""Raise when a runner class is not like 'RunnerXXX'"""

class PyPPLFuncWrongPositionError(Exception):
	"""raises when the function put in wrong position"""
