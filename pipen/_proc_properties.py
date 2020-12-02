"""Provide ProcProperties class"""
import inspect
import textwrap
from typing import Any, ClassVar, Dict, Iterable, List, Optional, Type, Union
from pathlib import Path
from functools import lru_cache

from diot import OrderedDiot, Diot
from xqute import Scheduler
from simpleconf import Config
import pandas

from .defaults import ProcInputType
from .utils import is_subclass, get_shebang
from .channel import Channel
from .template import Template, get_template_engine
from .scheduler import get_scheduler
from .exceptions import (
    ProcInputTypeError, ProcScriptFileNotFound, ProcInputKeyError
)

ProcType = Union["Proc", Type["Proc"]]

class ProcMeta(type):
    """The metaclass for Proc class

    We need it to invoke _compute_requires so that the class variable
    requires can chain the processes.
    """
    def __new__(cls, name, bases, dct):
        proc_class = super().__new__(cls, name, bases, dct)
        if proc_class.requires:
            inst = proc_class()
            inst.requires = inst._compute_requires(
                proc_class.requires
            )
        return proc_class

class ProcProperties:
    """Initiate proc properties and update them from configuration if necessary
    """
    # pylint: disable=redefined-builtin

    args: ClassVar[Dict[str, Any]] = {}
    cache: ClassVar[bool] = None
    dirsig: ClassVar[int] = None
    envs: ClassVar[Dict[str, Any]] = {}
    forks: ClassVar[int] = None
    input_keys: ClassVar[Union[List[str], str]] = None
    input: ClassVar[Any] = None
    lang: ClassVar[str] = None
    output: ClassVar[Any] = None
    profile: ClassVar[str] = None
    requires: ClassVar[Union[ProcType, Iterable[ProcType]]] = None
    scheduler: ClassVar[str] = None
    scheduler_opts: ClassVar[Dict[str, Any]] = {}
    plugin_opts: ClassVar[Dict[str, Any]] = {}
    script: ClassVar[str] = None
    template: ClassVar[str] = None
    end: ClassVar[bool] = None

    def __init__(self, # pylint: disable=too-many-locals
                 end: Optional[bool] = None,
                 input_keys: Union[List[str], str] = None,
                 input: Optional[Union[str, Iterable[str]]] = None,
                 output: Optional[Union[str, Iterable[str]]] = None,
                 lang: Optional[str] = None,
                 script: Optional[str] = None,
                 forks: Optional[int] = None,
                 requires: Optional[Union[ProcType, Iterable[ProcType]]] = None,
                 args: Optional[Dict[str, Any]] = None,
                 envs: Optional[Dict[str, Any]] = None,
                 cache: Optional[bool] = None,
                 dirsig: Optional[int] = None,
                 profile: Optional[str] = None,
                 template: Optional[Union[str, Type[Template]]] = None,
                 scheduler: Optional[Union[str, Scheduler]] = None,
                 scheduler_opts: Optional[Dict[str, Any]] = None,
                 plugin_opts: Optional[Dict[str, Any]] = None) -> None:
        self.end = self.__class__.end if end is None else end
        self.args = Diot(self.__class__.args.copy())
        self.args |= args or {}
        self.cache = self.__class__.cache if cache is None else cache
        self.dirsig = self.__class__.dirsig if dirsig is None else dirsig
        self.envs = Diot(self.__class__.envs.copy())
        self.envs |= envs or {}
        self.forks = forks or self.__class__.forks
        self.input_keys = input_keys or self.__class__.input_keys
        self.input = input or self.__class__.input
        self.lang = lang or self.__class__.lang
        self.output = output or self.__class__.output
        self.profile = profile or self.__class__.profile
        if self is not self.__class__.SELF:
            self.requires = self._compute_requires(
                requires or self.__class__.requires
            )
        self.scheduler = scheduler or self.__class__.scheduler
        self.scheduler_opts = Diot(self.__class__.scheduler_opts.copy())
        self.scheduler_opts |= scheduler_opts or {}
        self.plugin_opts = Diot(self.__class__.plugin_opts.copy())
        self.plugin_opts |= plugin_opts or {}
        self.script = script or self.__class__.script
        self.template = template or self.__class__.template

    def properties_from_config(self, config: Config) -> None:
        """Inherit properties from configuration if they are not set in
        the class variables or constructor

        Args:
            config: The configuration
        """
        self.lang = self.lang or config.lang
        self.forks = self.forks or config.forks
        self.scheduler = self.scheduler or config.scheduler
        self.template = self.template or config.template

        if self.cache is None:
            self.cache = config.cache

        if self.dirsig is None:
            self.dirsig = config.dirsig

        envs = Diot((config.envs or {}).copy())
        self.envs = envs | self.envs

        scheduler_opts = Diot(config.scheduler_opts.copy())
        self.scheduler_opts = scheduler_opts | self.scheduler_opts

        plugin_opts = Diot(config.plugin_opts.copy())
        self.plugin_opts = plugin_opts | self.plugin_opts

    def compute_properties(self):
        """Compute some properties"""
        self.template = get_template_engine(self.template)
        self.input = self._compute_input()
        self.output = self._compute_output()
        self.scheduler = get_scheduler(self.scheduler)
        self.script = self._compute_script()

    @lru_cache()
    def _compute_input(self) -> Dict[str, Dict[str, Any]]:
        """Calculate the input based on input_keys and input data"""
        # split input keys into keys and types
        input_keys = self.input_keys
        if isinstance(input_keys, str):
            input_keys = [input_key.strip()
                          for input_key in input_keys.split(',')]
        if not input_keys:
            raise ProcInputKeyError(f'[{self.name}] No input_keys provided')

        ret = OrderedDiot(type={})
        for input_key_type in input_keys:
            if ':' not in input_key_type:
                input_key_type = f'{input_key_type}:{ProcInputType.VAR}'
            input_key, input_type = input_key_type.split(':', 1)
            if input_type not in ProcInputType.__dict__.values():
                raise ProcInputTypeError(
                    f'Unsupported input type: {input_type}'
                )
            ret.type[input_key] = input_type

        # get the data
        if not self.requires:
            ret.data = Channel.create(self.input)
        else:
            ret.data = pandas.concat(
                (req.out_channel for req in self.requires),
                axis=1
            )
            if callable(self.input):
                ret.data = self.input(ret.data)
            elif self.input:
                self.log('warning',
                         'Ignoring input data, '
                         'as process depends on other processes.')
        n_keys = len(ret.type)
        # key names
        input_keys = list(ret.type.keys())
        if ret.data.shape[1] > n_keys:
            # // TODO: match the column names?
            self.log('warning',
                     'Wasted %s column(s) of input data.',
                     ret.data.shape[1] - n_keys)
            ret.data = ret.data.iloc[:, :n_keys]
            ret.data.columns = input_keys
        elif ret.data.shape[1] < n_keys:
            self.log('warning',
                     'No data columns for input: %s, using None.',
                     input_keys[ret.data.shape[1]:])
            for input_key in input_keys[ret.data.shape[1]:]:
                ret.data.insert(ret.data.shape[1], input_key, None, True)
            ret.data.columns = input_keys
        else:
            ret.data.columns = input_keys
        return ret

    @lru_cache()
    def _compute_output(self):
        """Compute the output for jobs to render"""
        output = self.output
        if not output:
            return None
        if isinstance(output, (list, tuple)):
            return [self.template(oput, **self.envs)
                    for oput in output]
        return self.template(output, **self.envs)

    @lru_cache()
    def _compute_script(self) -> Optional[Template]:
        """Compute the script for jobs to render"""
        if not self.script:
            self.log('warning', 'No script specified.')
            return None

        script = self.script
        if script.startswith('file://'):
            script_file = Path(script[7:])
            if not script_file.is_absolute():
                dirname = Path(inspect.getfile(self.__class__)).parent
                script_file = dirname / script_file
            if not script_file.is_file():
                raise ProcScriptFileNotFound(
                    f'No such script file: {script_file}'
                )
            script = script_file.read_text()

        script = textwrap.dedent(script)
        self.lang = get_shebang(script) or self.lang

        return self.template(script, **self.envs)

    def _compute_requires(
            self,
            requires: Optional[Union[ProcType, Iterable[ProcType]]]
    ) -> List["Proc"]:
        """Prepare the requirements for a process.

        We need to add the process to nexts of the requirements for easy
        runing sequence detection in pipen.

        Args:
            proc: The process
            requires: The requirements of the process

        Returns:
            A list of Proc instances as requirements.
        """
        from .proc import Proc
        ret = []
        if not requires:
            return ret

        if not isinstance(requires, (tuple, list)):
            requires = [requires]

        for require in requires:
            if is_subclass(require, Proc):
                require = require()
            require.nexts.append(self)
            ret.append(require)
        return ret
