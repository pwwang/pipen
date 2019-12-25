"""Exceptions for PyPPL"""

class PyPPLInvalidConfigurationKey(KeyError):
	"""@API\nWhen invalid configuration key passed"""

class PyPPLFindNoProcesses(Exception):
	"""@API\nWhen failed to find any processes with given pattern"""

class PyPPLResumeError(Exception):
	"""@API\nTry to resume when no start process has been specified"""

class PyPPLNameError(Exception):
	"""@API\nPipeline name duplicated after transformed by utils.name2filename"""

class PyPPLWrongPositionMethod(Exception):
	"""@API\nWrong position for plugin-added method"""

class PyPPLMethodExists(Exception):
	"""@API\nMethod has already been registered"""

class ProcessAttributeError(Exception):
	"""@API\nProcess AttributeError"""

class ProcessInputError(Exception):
	"""@API\nProcess Input error"""

class ProcessOutputError(Exception):
	"""@API\nProcess Output error"""

class ProcessScriptError(Exception):
	"""@API\nProcess script building error"""

class ProcessAlreadyRegistered(Exception):
	"""@API\nProcess already registered with the same id and tag"""
	def __init__(self, message = '', proc1 = None, proc2 = None):
		"""@API
		Construct for ProcessAlreadyRegistered
		@params:
			message (str): The message, make the class to be compatible with Exception
			proc1 (Proc): the first Proc
			proc2 (Proc): the second Proc
		"""
		if not message and not proc1 and not proc2: # pragma: no cover
			message = 'There are two processes with the same id and tag.'
		elif not message and proc1 and proc2:
			message = '\n'.join([
				"There are two processes with id({}) and tag({})".format(proc1.id, proc1.tag),
				"",
				">>> One is defined here:",
				proc1._defs,
				">>> The other is defined here:",
				proc2._defs
			])
		super().__init__(message)

class JobInputParseError(Exception):
	"""@API\nFailed to parse job input"""

class JobOutputParseError(Exception):
	"""@API\nFailed to parse job output"""

class JobBuildingError(Exception):
	"""@API\nFailed to build the job"""

class JobFailError(Exception):
	"""@API\nJob results validation failed"""

class PluginConfigKeyError(Exception):
	"""@API\nWhen try to update plugin config from a dictionary with key not added"""

class PluginNoSuchPlugin(Exception):
	"""@API\nWhen try to find a plugin not existing"""

class RunnerNoSuchRunner(Exception):
	"""@API\nWhen no such runner is found"""

class RunnerMorethanOneRunnerEnabled(Exception):
	"""@API\nWhen more than one runners are enabled"""
	def __init__(self, message = ''):
		message += ', you may have to call runner.use_runner() first.'
		super().__init__(message)

class RunnerTypeError(Exception):
	"""@API\nWrong type of runner"""
