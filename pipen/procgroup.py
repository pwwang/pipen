"""Process group that contains a set of processes.

It can be easily used to create a pipeline that runs independently or
integrated into a larger pipeline.

Runs directly:
>>> proc_group = ProcGroup(<options>)
>>> proc_group.as_pipen(<pipeline options>).set_data(<data>).run()

Integrated into a larger pipeline
>>> proc_group = ProcGroup(<options>)
>>> # proc could be a process within the larger pipeline
>>> proc.requires = prog_group.build()

To add a process to the proc group, use the `add_proc` method:
>>> class MyProcGroup(ProcGroup):
>>>     def build(self):
>>>         return [self.MyProc]
>>>
>>> proc_group = MyProcGroup(...)
>>> @proc_group.add_proc
>>> class MyProc(Proc):
>>>     ...

Or use the define_proc decorator:
>>> class MyProcGroup(ProcGroup):
>>>     def build(self):
>>>         return [self.MyProc]
>>>
>>>     @define_proc
>>>     def my_proc(self):
>>>         class MyProc(Proc):
>>>             # You may use self.options here
>>>             ...
>>>         return MyProc
>>> proc_group = MyProcGroup(...)

You should define the relationship between processes in the `build` method:
>>> class MyProcGroup(ProcGroup):
>>>     def build(self):
>>>         self.MyProc1.requires = [self.MyProc2]
>>>         return [self.MyProc1]

When run directly, the `build` method will be called automatically. But
when integrated into a larger pipeline, you should call it manually:
>>> proc_group = MyProcGroup(...)
>>> # proc could be a process within the larger pipeline
>>> proc.requires = proc_group.build()
"""
from __future__ import annotations
from functools import wraps

from os import PathLike
from types import MethodType
from typing import Callable, Type, List
from abc import ABC, ABCMeta
from diot import Diot

from .utils import cached_property
from .pipen import Pipen
from .proc import Proc


class ProcGropuMeta(ABCMeta):
    """Meta class for ProcGroup"""

    _INST = None

    def __call__(cls, *args, **kwds):
        """Make sure Proc subclasses are singletons

        Args:
            *args: and
            **kwds: Arguments for the constructor

        Returns:
            The Proc instance
        """
        if cls._INST is None:
            cls._INST = super().__call__(*args, **kwds)

        return cls._INST


class ProcGroup(ABC, metaclass=ProcGropuMeta):
    """A group of processes that can be run independently or
    integrated into a larger pipeline.
    """

    name: str | None = None
    DEFAULTS = Diot()
    PRESERVED = {
        "opts",
        "name",
        "build",
        "add_proc",
        "as_pipen",
        "procs",
    }

    def __init__(self, **opts) -> None:
        self.opts = Diot(self.__class__.DEFAULTS or {}) | (opts or {})
        self.name = self.__class__.name or self.__class__.__name__

    def build(self) -> List[Type[Proc]] | Type[Proc]:
        """Build the pipeline"""

    @property
    def procs(self) -> Diot:
        """Get all processes"""
        return Diot(
            {
                k: v
                for k, v in
                self.__dict__.items()
                if isinstance(v, Proc) or (
                    isinstance(v, type) and issubclass(v, Proc)
                )
            }
        )

    def add_proc(
        self,
        proc: Type[Proc] | None = None,
    ) -> Type[Proc] | Callable[[Type[Proc]], Type[Proc]]:
        """Add a process to the proc group

        Args:
            proc: The process to add
            start: Whether the process is a start process
            end: Whether the process is an end process

        Returns:
            The process added
        """
        if proc is None:
            return self.add_proc  # type: ignore

        if proc.name in self.__class__.PRESERVED:
            raise ValueError(
                f"Process name `{proc.name}` is reserved for ProcGroup"
            )
        setattr(self, proc.name, proc)
        proc.__procgroup__ = self
        return proc

    def as_pipen(
        self,
        name: str = None,
        desc: str = None,
        outdir: PathLike = None,
        **kwargs,
    ) -> Pipen:
        """Convert the pipeline to a Pipen instance

        Args:
            name: The name of the pipeline
            desc: The description of the pipeline
            outdir: The output directory of the pipeline
            **kwargs: The keyword arguments to pass to Pipen

        Returns:
            The Pipen instance
        """
        name = name or self.__class__.__name__
        if self.__doc__:
            desc = desc or self.__doc__.lstrip().splitlines()[0]

        pipe = Pipen(name=name, desc=desc, outdir=outdir, **kwargs)
        pipe.set_start(self.build())
        return pipe

    def define_proc(
        method: MethodType | None = None,
    ) -> property | Callable[[MethodType], property]:
        """Define a process by a method of ProcGroup and add it to the
        proc group

        This is used to decorate a method of ProcGroup that returns a process.
        Different from procgroup.add_proc(), this allows you to create the
        process at runtime.

        Args:
            method: The method to define the process. It will finally work as a
                property, so it should not have any arguments.

        Returns:
            The process defined
        """
        if method is None:
            return ProcGroup.define_proc  # type: ignore

        @wraps(method)
        def wrapper(self):
            proc = method(self)
            proc.__procgroup__ = self
            return proc

        return cached_property(wrapper)
