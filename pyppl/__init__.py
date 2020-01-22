"""PyPPL - A Python PiPeLine framework."""

__version__ = "3.0.3"

from .config import load_config
from .plugin import config_plugins
from .pyppl import PyPPL, PROCESSES, PIPELINES
from .proc import Proc
from .procset import ProcSet
from .channel import Channel
from .runner import register_runner
