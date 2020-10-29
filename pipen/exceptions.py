"""Provide exception classes"""

class PipenException(Exception):
    """Base exception class for pipen"""

class ProcInputTypeError(PipenException, TypeError):
    """When an unsupported input type is provided"""

class ProcScriptFileNotFound(PipenException, FileNotFoundError):
    """When script file specified as 'file://' cannot be found"""

class ProcOutputNameError(PipenException, NameError):
    """When no name or malformatted output is provided"""

class ProcOutputTypeError(PipenException, TypeError):
    """When an unsupported output type is provided"""

class ProcDependencyError(PipenException):
    """When there is something wrong the process dependencies"""
