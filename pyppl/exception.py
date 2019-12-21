class PyPPLInvalidConfigurationKey(KeyError):
	"""When invalid configuration key passed"""

class PyPPLFindNoProcesses(Exception):
	"""When failed to find any processes with given pattern"""

class PyPPLResumeError(Exception):
	"""Try to resume when no start process has been specified"""

class PyPPLNameError(Exception):
	"""Pipeline name duplicated after transformed by utils.name2filename"""

class PyPPLPluginWrongPositionFunction(Exception):
	"""When a function specified in a plugin for pyppl at wrong position"""

class ProcessAlreadyRegistered(Exception):
	"""When a process is already registered with the same id and tag"""

class ProcessAttributeError(Exception):
	"""Process AttributeError"""

class ProcessInputError(Exception):
	"""Process Input error"""

class ProcessOutputError(Exception):
	"""Process Output error"""

class ProcessScriptError(Exception):
	"""Process script building error"""

class ProcessAlreadyRegistered(Exception):
	"""Process already registered with the same id and tag"""
	def __init__(self, message = '', proc1 = None, proc2 = None):
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
	"""Failed to parse job input"""

class JobOutputParseError(Exception):
	"""Failed to parse job output"""

class JobBuildingError(Exception):
	"""Failed to build the job"""

class JobFailError(Exception):
	"""Job results validation failed"""

class PluginConfigKeyError(Exception):
	"""When try to update plugin config from a dictionary with key not added"""

class PluginNoSuchPlugin(Exception):
	"""When try to find a plugin not existing"""

class PluginWrongPluginType(Exception):
	"""When use a class itself as a plugin"""

class RunnerNoSuchRunner(Exception):
	"""When no such runner is found"""

class RunnerMorethanOneRunnerEnabled(Exception):
	"""When more than one runners are enabled"""
	def __init__(self, message = ''):
		message += ', you may have to call runner.use_runner() first.'
		super().__init__(message)

class RunnerTypeError(Exception):
	"""Wrong type of runner"""

