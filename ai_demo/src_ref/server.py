"""Builds an MCPServer from pipen Proc/ProcGroup entry points."""
from __future__ import annotations

import asyncio
from asyncio.subprocess import PIPE
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from .introspect import (
    format_process_detail,
    format_process_listing,
    get_eligible_items,
)


def _load_nsmod(entry_points: dict, ns: str) -> Any | None:
    """Return the loaded module for *ns*, or None if the namespace is unknown."""
    epoint = entry_points.get(ns)
    if epoint is None:
        return None
    if type(epoint).__name__ == "EntryPoint":
        return epoint.load()
    return epoint


def build_server(entry_points: dict) -> MCPServer:
    """Build an MCPServer with 4 static discovery + execution tools."""
    from pipen_cli_run.entry import get_short_summary

    mcp = MCPServer("pipen-mcp")

    # ------------------------------------------------------------------
    # Tool 1 — list namespaces
    # ------------------------------------------------------------------
    async def get_namespaces() -> str:
        """List all available namespaces registered with pipen."""
        if not entry_points:
            return "No namespaces registered."
        lines = ["Available namespaces:", ""]
        for ns in entry_points:
            nsmod = _load_nsmod(entry_points, ns)
            desc = (
                get_short_summary(getattr(nsmod, "__doc__", None))
                or f"Namespace {ns}"
            )
            lines.append(f"  {ns}: {desc}")
        lines += [
            "",
            "Use get_processes('<namespace>') to see available processes.",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Tool 2 — list processes in a namespace
    # ------------------------------------------------------------------
    async def get_processes(
        ns: Annotated[str, Field(description="The namespace name")],
    ) -> str:
        """List all processes/pipelines available in a namespace."""
        nsmod = _load_nsmod(entry_points, ns)
        if nsmod is None:
            known = ", ".join(entry_points) or "none"
            return f"Unknown namespace '{ns}'. Known namespaces: {known}"
        return format_process_listing(ns, nsmod)

    # ------------------------------------------------------------------
    # Tool 3 — show detailed schema for one process
    # ------------------------------------------------------------------
    async def get_process(
        ns: Annotated[str, Field(description="The namespace name")],
        proc: Annotated[str, Field(description="The process or pipeline name")],
    ) -> str:
        """Get the detailed argument schema for a specific process or pipeline."""
        nsmod = _load_nsmod(entry_points, ns)
        if nsmod is None:
            known = ", ".join(entry_points) or "none"
            return f"Unknown namespace '{ns}'. Known namespaces: {known}"

        items = get_eligible_items(nsmod)
        match = next((cls for name, cls, _kind in items if name == proc), None)
        if match is None:
            known = ", ".join(name for name, _, _ in items) or "none"
            return (
                f"Unknown process '{proc}' in namespace '{ns}'. "
                f"Known processes: {known}"
            )
        return format_process_detail(ns, proc, match)

    # ------------------------------------------------------------------
    # Tool 4 — execute a process
    # ------------------------------------------------------------------
    async def run_process(
        ns: Annotated[str, Field(description="The namespace containing the process")],
        proc: Annotated[str, Field(description="The process or pipeline name to run")],
        arguments: Annotated[
            list[str],
            Field(
                description=(
                    "CLI arguments as a flat list, e.g. "
                    '["--in.infile", "/path/to/file", "--outdir", "./out"]'
                )
            ),
        ],
    ) -> str:
        """Run a pipen process or pipeline via pipen-cli-run."""
        nsmod = _load_nsmod(entry_points, ns)
        if nsmod is None:
            known = ", ".join(entry_points) or "none"
            raise ValueError(
                f"Unknown namespace '{ns}'. Known namespaces: {known}"
            )

        items = get_eligible_items(nsmod)
        if not any(name == proc for name, _, _ in items):
            known = ", ".join(name for name, _, _ in items) or "none"
            raise ValueError(
                f"Unknown process '{proc}' in namespace '{ns}'. "
                f"Known processes: {known}"
            )

        child = await asyncio.create_subprocess_exec(
            "pipen", "run", ns, proc, *arguments,
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout, stderr = await child.communicate()
        output = stdout.decode() + stderr.decode()
        if child.returncode != 0:
            raise RuntimeError(
                f"pipen run {ns} {proc} exited {child.returncode}:\n{output}"
            )
        return output

    mcp.add_tool(
        get_namespaces,
        name="get_namespaces",
        description=(
            "List all available namespaces registered with pipen. "
            "Start here to discover what is available."
        ),
    )
    mcp.add_tool(
        get_processes,
        name="get_processes",
        description="List all processes/pipelines available in a namespace.",
    )
    mcp.add_tool(
        get_process,
        name="get_process",
        description=(
            "Get the detailed argument schema for a specific process or pipeline, "
            "including required and optional CLI arguments."
        ),
    )
    mcp.add_tool(
        run_process,
        name="run_process",
        description=(
            "Run a pipen process or pipeline. "
            "Build the arguments list from the schema returned by get_process."
        ),
    )

    return mcp
