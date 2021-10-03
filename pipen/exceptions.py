"""Provide exception classes"""


class PipenException(Exception):
    """Base exception class for pipen"""


class PipenSetDataError(PipenException, ValueError):
    """When trying to set input data to processes with input_data already set
    using Pipen.set_data()."""


class ProcInputTypeError(PipenException, TypeError):
    """When an unsupported input type is provided"""


class ProcInputKeyError(PipenException, KeyError):
    """When an unsupported input value is provided"""


class ProcScriptFileNotFound(PipenException, FileNotFoundError):
    """When script file specified as 'file://' cannot be found"""


class ProcOutputNameError(PipenException, NameError):
    """When no name or malformatted output is provided"""


class ProcOutputTypeError(PipenException, TypeError):
    """When an unsupported output type is provided"""


class ProcOutputValueError(PipenException, ValueError):
    """When a malformatted output value is provided"""


class ProcDependencyError(PipenException):
    """When there is something wrong the process dependencies"""


class NoSuchSchedulerError(PipenException):
    """When specified scheduler cannot be found"""


class WrongSchedulerTypeError(PipenException, TypeError):
    """When specified scheduler is not a subclass of Scheduler"""


class NoSuchTemplateEngineError(PipenException):
    """When specified template engine cannot be found"""


class WrongTemplateEnginTypeError(PipenException, TypeError):
    """When specified tempalte engine is not a subclass of Scheduler"""


class TemplateRenderingError(PipenException):
    """Failed to render a template"""


class ConfigurationError(PipenException):
    """When something wrong set as configuration"""


class ProcWorkdirConflictException(PipenException):
    """ "When more than one processes are sharing the same workdir"""
