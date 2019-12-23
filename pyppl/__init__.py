"""PyPPL - A Python PiPeLine framework."""
__version__ = "3.0.0"
from .pyppl import PyPPL
from .proc import Proc
from .channel import Channel
from .plugin import config_plugins
from .runner import register_runner
from .config import config, load_config
