"""Provides PipenCliRun"""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, List

from pipen import Proc, Pipen, ProcGroup
from pipen.cli import AsyncCLIPlugin
from pipen.utils import importlib_metadata
from pipen_args import ProcGroup as ArgsProcGroup

from .version import __version__

if TYPE_CHECKING:  # pragma: no cover
    from argx import ArgumentParser, Namespace

ENTRY_POINT_GROUP = "pipen_cli_run"


def get_short_summary(
    docstring: str | None,
    varname: str | None = None,
    procname: str | None = None,
) -> str:
    """Get the short summary of a docstring"""
    if varname and procname and varname != procname:
        return f"Alias for `{procname}`"

    if not docstring:
        return ""
    lines = docstring.lstrip().splitlines()
    short_summary = lines[0]
    for line in lines[1:]:
        if not line.strip():
            break
        short_summary += line.strip() + " "
    return short_summary.rstrip()


class PipenCliRunPlugin(AsyncCLIPlugin):
    """Run a process or a pipeline"""

    version = __version__
    name = "run"  # type: ignore

    def __init__(
        self,
        parser: ArgumentParser,
        subparser: ArgumentParser,
    ) -> None:
        super().__init__(parser, subparser)
        self.entry_points = {}

        for dist in importlib_metadata.distributions():
            for epoint in dist.entry_points:
                if epoint.group != ENTRY_POINT_GROUP:
                    continue
                # don't load them yet for performance
                self.entry_points[epoint.name] = epoint  # pragma: no cover

        subparser.pre_parse = self._subparser_pre_parse  # type: ignore

    def _subparser_pre_parse(
        self,
        parser: ArgumentParser,
        args: List[str],
        namespace: Namespace,
    ) -> None:
        """Add processes to the namespace"""
        if parser._subparsers_action:
            return

        parser._subparsers_action = parser.add_subparsers(
            title='Process Namespaces',
            dest="PROC_NAMESPACE",
            required=True,
        )

        for ns, epoint in self.entry_points.items():
            parser._subparsers_action.add_parser(
                ns,
                help=get_short_summary(epoint.load().__doc__),
                pre_parse=self._subsubparser_pre_parse,
            )

    def _subsubparser_pre_parse(
        self,
        parser: ArgumentParser,
        args: List[str],
        namespace: Namespace,
    ) -> None:
        """Add processes to the namespace"""
        if parser._subparsers_action:
            return

        nsmod_name = [
            name
            for name, ps in (
                parser
                .parent  # type: ignore
                ._subparsers_action
                ._name_parser_map
                .items()
            )
            if ps is parser
        ][0]

        # isinstance doesn't work here
        if type(self.entry_points[nsmod_name]).__name__ == "EntryPoint":
            self.entry_points[nsmod_name] = (
                self.entry_points[nsmod_name].load()
            )

        nsmod = self.entry_points[nsmod_name]
        parser._subparsers_action = parser.add_subparsers(
            title='Processes / Pipelines',
            dest="PROCESS_OR_PIPELINE",
            required=True,
        )
        for attrname in dir(nsmod):
            attrval = getattr(nsmod, attrname)
            if not isinstance(attrval, type):
                continue
            # If it is a pipeline
            if (
                issubclass(attrval, ProcGroup)
                and attrval is not ProcGroup
                and attrval is not ArgsProcGroup
            ):
                doc = attrval.__doc__ or nsmod.__doc__
                parser._subparsers_action.add_parser(
                    attrname,
                    help=get_short_summary(doc),
                    usage="%(prog)s [-h|-h+] [pipeline_args ...]",
                    add_help=False,
                    prefix_chars="+",
                    exit_on_void=True,
                ).add_argument(
                    "pipeline_args",
                    nargs="*",
                    help=(
                        "Arguments for the process or pipeline (Use -h/--help "
                        "to see the arguments for the process or pipeline)"
                    )
                )
            elif issubclass(attrval, Proc) and attrval.input:  # type: ignore
                doc = attrval.__doc__
                parser._subparsers_action.add_parser(
                    attrname,  # type: ignore
                    help=get_short_summary(doc, attrname, attrval.name),
                    add_help=False,
                    usage="%(prog)s [-h|-h+] [pipeline_args ...]",
                    prefix_chars="+",
                    exit_on_void=True,
                ).add_argument(
                    "pipeline_args",
                    nargs="*",
                    help=(
                        "Arguments for the process or pipeline (Use -h/--help "
                        "to see the arguments for the process or pipeline)"
                    )
                )

    async def exec_command(self, args: Namespace) -> None:
        if not self.entry_points:
            print(
                "\n"
                "No entry points found for pipen_cli_run. \n"
                "Make sure you have installed a package that provides entry "
                "points for pipen_cli_run.\n"
            )
            sys.exit(1)

        from pipen_args import parser

        nsmod_name = args.PROC_NAMESPACE
        pname = args.PROCESS_OR_PIPELINE
        if (
            type(self.entry_points[nsmod_name]).__name__ == "EntryPoint"
        ):  # pragma: no cover
            self.entry_points[nsmod_name] = self.entry_points[nsmod_name].load()

        module = self.entry_points[nsmod_name]
        proc_or_group = getattr(module, pname)
        if (
            issubclass(proc_or_group, ProcGroup)
            and proc_or_group is not ProcGroup
            and proc_or_group is not ArgsProcGroup
        ):
            pipeline = proc_or_group().as_pipen(pname, desc="")
        else:
            pipeline = Pipen(pname, desc="").set_start(
                proc_or_group  # type: ignore
            )

        # Send the args to the pipeline argument parser
        parser.set_cli_args(args.pipeline_args)
        await pipeline.async_run()
