"""Provide some default values/objects"""
from pathlib import Path
from typing import ClassVar

from diot import Diot
from xqute import JobErrorStrategy
from xqute.utils import logger as xqute_logger

# Remove the rich handler
_xqute_handlers = xqute_logger.handlers
if _xqute_handlers:
    # The very first handler is the rich handler
    xqute_logger.removeHandler(_xqute_handlers[0])

LOGGER_NAME = "core"
CONFIG_FILES = (
    Path("~/.pipen.toml").expanduser(),
    "./.pipen.toml",
    "PIPEN.osenv",
)
CONFIG = Diot(
    # pipeline level: The logging level
    loglevel="info",
    # process level: The cache option, True/False/export
    cache=True,
    # process level: Whether expand directory to check signature
    dirsig=1,
    # process level:
    # How to deal with the errors
    # retry, ignore, halt
    # halt to halt the whole pipeline, no submitting new jobs
    # terminate to just terminate the job itself
    error_strategy=JobErrorStrategy.IGNORE,
    # process level:
    # How many times to retry to jobs once error occurs
    num_retries=3,
    # process level:
    # The directory to export the output files
    forks=1,
    # process level: Default shell/language
    lang="bash",
    # process level:
    # How many jobs to be submitted in a batch
    submission_batch=8,
    # pipeline level:
    # The working directory for the pipeline
    workdir="./.pipen",
    # process level: template engine
    template="liquid",
    # process level: template options
    template_opts={},
    # process level: scheduler
    scheduler="local",
    # process level: scheduler options
    scheduler_opts={},
    # pipeline level: plugins
    plugins=None,
    # pipeline level: plugin opts
    plugin_opts={},
)

# Just the total width of the terminal
# when logging with a rich.Panel()
CONSOLE_WIDTH_WITH_PANEL = 100
# The width of the terminal when the width cannot be detected,
# we are probably logging into a file
CONSOLE_DEFAULT_WIDTH = 2048
# [05/16/22 11:46:40] I
# v0.3.4:
# 05-16 11:11:11 I
# The markup code is included
# Don't modify this unless the logger formatter is changed
CONSOLE_WIDTH_SHIFT = 25
# For pipen scheduler plugins
SCHEDULER_ENTRY_GROUP = "pipen_sched"
# For pipen template plugins
TEMPLATE_ENTRY_GROUP = "pipen_tpl"
# For pipen template cli plugins
CLI_ENTRY_GROUP = "pipen_cli"


class ProcInputType:
    """Types for process inputs"""

    VAR: ClassVar[str] = "var"
    FILE: ClassVar[str] = "file"
    DIR: ClassVar[str] = "dir"
    FILES: ClassVar[str] = "files"
    DIRS: ClassVar[str] = "dirs"


class ProcOutputType:
    """Types for process outputs"""

    VAR: ClassVar[str] = "var"
    DIR: ClassVar[str] = "dir"
    FILE: ClassVar[str] = "file"
