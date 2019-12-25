"""PyPPL - A Python PiPeLine framework."""

__version__ = "3.0.0"

from .config import load_config
from .plugin import config_plugins
from .pyppl import PyPPL
from .proc import Proc
from .channel import Channel
from .runner import register_runner
