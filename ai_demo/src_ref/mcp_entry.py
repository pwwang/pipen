"""Provides PipenMcpPlugin"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pipen.cli import AsyncCLIPlugin  # type: ignore
from pipen.utils import importlib_metadata
from pipen_cli_run.entry import ENTRY_POINT_GROUP

from .version import __version__

if TYPE_CHECKING:  # pragma: no cover
    from argx import ArgumentParser, Namespace


class PipenMcpPlugin(AsyncCLIPlugin):
    """Expose pipen processes/pipelines as MCP tools"""

    version = __version__
    name = "mcp"  # type: ignore

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
                self.entry_points[epoint.name] = epoint  # pragma: no cover

        subparser.add_argument(
            "--transport",
            choices=["stdio", "sse", "streamable-http"],
            default="stdio",
            help="MCP transport to use [default: stdio]",
        )
        subparser.add_argument(
            "--host",
            default="127.0.0.1",
            help="Host to bind to for sse/streamable-http [default: 127.0.0.1]",
        )
        subparser.add_argument(
            "--port",
            type=int,
            default=8520,
            help="Port to listen on for sse/streamable-http [default: 8520]",
        )

    async def exec_command(self, args: Namespace) -> None:
        from .server import build_server

        if not self.entry_points:
            self.subparser.print_help()
            return

        loaded = {}
        for ns, epoint in self.entry_points.items():
            if type(epoint).__name__ == "EntryPoint":
                loaded[ns] = epoint.load()
            else:
                loaded[ns] = epoint

        server = build_server(loaded)

        transport = args.transport
        if transport == "stdio":
            await server.run_stdio_async()
        elif transport == "sse":
            await server.run_sse_async(host=args.host, port=args.port)
        else:
            await server.run_streamable_http_async(host=args.host, port=args.port)
