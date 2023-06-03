"""Process group that contains a set of processes.

It can be easily used to create a pipeline that runs independently or
integrated into a larger pipeline.

Runs directly:
>>> proc_group = ProcGroup(<options>)
>>> proc_group.as_pipen(<pipeline options>).set_data(<data>).run()

Integrated into a larger pipeline
>>> proc_group = ProcGroup(<options>)
>>> # proc could be a process within the larger pipeline
>>> proc.requires = prog_group.<proc>

To add a process to the proc group, use the `add_proc` method:
>>> class MyProcGroup(ProcGroup):
>>>     ...
>>>
>>> proc_group = MyProcGroup(...)
>>> @proc_group.add_proc
>>> class MyProc(Proc):
>>>     ...

Or add a process at runtime:
>>> class MyProcGroup(ProcGroup):
>>>     ...
>>>
>>>     @ProcGroup.add_proc
>>>     def my_proc(self):
>>>         class MyProc(Proc):
>>>             # You may use self.options here
>>>             ...
>>>         return MyProc
>>> proc_group = MyProcGroup(...)
"""
from __future__ import annotations

from os import PathLike
from functools import wraps, cached_property
from typing import Any, Callable, Mapping, Type, List
from abc import ABC, ABCMeta
from diot import Diot

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
    __meta__: Mapping[str, Any] = {}
    DEFAULTS = Diot()
    PRESERVED = {
        "opts",
        "name",
        "add_proc",
        "as_pipen",
        "procs",
        "starts",
        "DEFAULTS",
        "PRESERVED",
        "_INST",
    }

    def __init_subclass__(cls) -> None:
        # Clear the meta
        cls.__meta__ = {}

    def __init__(self, **opts) -> None:
        self.opts = Diot(self.__class__.DEFAULTS or {}) | (opts or {})
        self.name = self.__class__.name or self.__class__.__name__
        self.starts: List[Type[Proc]] = []
        self.procs = Diot()

        self._load_runtime_procs()

    def _load_runtime_procs(self):
        """Load all processes that are added at runtime"""
        # Load all processes if they are decorated by ProcGroup.add_proc
        for name, attr in self.__class__.__dict__.items():
            if isinstance(attr, cached_property):
                getattr(self, name)
            elif isinstance(attr, type) and issubclass(attr, Proc):
                self.add_proc(attr)

    def add_proc(
        self_or_method: ProcGroup | Callable[[ProcGroup], Type[Proc]],
        proc: Type[Proc] | None = None,
    ) -> Type[Proc] | cached_property:
        """Add a process to the proc group

        It works either as a decorator to the process directly or as a
        decorator to a method that returns the process.

        Args:
            self_or_method: The proc group instance or a method that
                returns the process
            proc: The process class if `self_or_method` is the proc group

        Returns:
            The process class if `self_or_method` is the proc group, or
            a cached property that returns the process class
        """
        if isinstance(self_or_method, ProcGroup):
            # Called as self.add_proc or pg.add_proc
            if proc is None:
                return self_or_method.add_proc  # type: ignore

            if proc.name in self_or_method.__class__.PRESERVED:
                raise ValueError(
                    f"Process name `{proc.name}` is reserved for ProcGroup"
                )

            setattr(self_or_method, proc.name, proc)
            proc.__meta__["procgroup"] = self_or_method  # type: ignore
            if not proc.requires:
                self_or_method.starts.append(proc)
            self_or_method.procs[proc.name] = proc
            return proc

        @wraps(self_or_method)
        def wrapper(self):
            proc = self_or_method(self)

            if proc is None:
                return None

            if (not isinstance(proc, type) or not issubclass(proc, Proc)):
                raise ValueError(f"`{proc}` is not a Proc subclass")

            proc.__meta__["procgroup"] = self
            if not proc.requires:
                self.starts.append(proc)
            self.procs[proc.name] = proc
            return proc

        return cached_property(wrapper)

    def as_pipen(
        self,
        name: str | None = None,
        desc: str | None = None,
        outdir: str | PathLike | None = None,
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
        pipe.set_start(self.starts)
        return pipe
