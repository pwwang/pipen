"""Provide some default values/objects"""
from pathlib import Path
from typing import ClassVar
from diot import Diot
from simpleconf import Config
import uvloop
from xqute import logger as xqute_logger, JobErrorStrategy

# turn xqute's logger off
xqute_logger.setLevel(100)
xqute_logger.removeHandler(xqute_logger.handlers[0])

uvloop.install()

LOGGER_NAME = 'main'
DEFAULT_CONFIG_FILES = (Path('~/.pipen.toml'), './.pipen.toml', 'PIPEN.osenv')
DEFAULT_CONFIG = Diot(
    loglevel='debug',
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
    lang='bash',
    # How many jobs to be submitted in a batch
    submission_batch=8,
    # The working directory for the pipeline
    workdir='./.pipen',
    # template engine
    template='liquid',
    # template envs
    envs={},
    # scheduler
    scheduler='local',
    # scheduler options
    scheduler_opts={},
    # plugins
    plugins=None,
    # plugin opts
    plugin_opts={}
)

DEFAULT_CONSOLE_WIDTH: int = 80
DEFAULT_CONSOLE_WIDTH_SHIFT: int = 26
SCHEDULER_ENTRY_GROUP = 'pipen-sched'
TEMPLATE_ENTRY_GROUP = 'pipen-tpl'

class ProcInputType:
    """Types for process inputs"""
    VAR: ClassVar[str] = 'var'
    FILE: ClassVar[str] = 'file'
    FILES: ClassVar[str] = 'files'

class ProcOutputType:
    """Types for process outputs"""
    VAR: ClassVar[str] = 'var'
    FILE: ClassVar[str] = 'file'

config = Config() # pylint: disable=invalid-name
