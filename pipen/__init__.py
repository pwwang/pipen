"""A pipeline framework for python"""
from .pipen import Pipen
from .proc import Proc
from .procgroup import ProcGroup

# Use from pipen.channel import Channel instead of
# from pipen import Channel
# This slows down import
# from .channel import Channel
from .pluginmgr import plugin
from .version import __version__
