"""Provide some default values/objects"""
from pathlib import Path
from typing import ClassVar

from diot import Diot
from xqute import JobErrorStrategy
from xqute import logger as xqute_logger

# turn xqute's logger off
xqute_logger.setLevel(100)
xqute_logger.removeHandler(xqute_logger.handlers[0])

LOGGER_NAME = "main"
CONFIG_FILES = (
    Path("~/.pipen.toml"),
    "./.pipen.toml",
    "PIPEN.osenv",
)
CONFIG = Diot(
    loglevel="info",
    # The cache option, True/False/export
    cache=True,
    # Whether expand directory to check signature
    dirsig=1,
    # How to deal with the errors
    # retry, ignore, halt
    # halt to halt the whole pipeline, no submitting new jobs
    # terminate to just terminate the job itself
    error_strategy=JobErrorStrategy.IGNORE,
    # How many times to retry to jobs once error occurs
    num_retries=3,
    # The directory to export the output files
    forks=1,
    # Default shell/language
    lang="bash",
    # How many jobs to be submitted in a batch
    submission_batch=8,
    # The working directory for the pipeline
    workdir="./.pipen",
    # template engine
    template="liquid",
    # template options
    template_opts={},
    # scheduler
    scheduler="local",
    # scheduler options
    scheduler_opts={},
    # plugins
    plugins=None,
    # plugin opts
    plugin_opts={},
)

CONSOLE_WIDTH: int = 80
CONSOLE_WIDTH_SHIFT: int = 26
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
