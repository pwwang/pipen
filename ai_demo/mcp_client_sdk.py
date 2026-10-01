"""MCP client driver using the official `mcp` SDK (2.2.0).

Starts `pipen mcp` (stdio transport) as a real MCP server subprocess and drives
the full discovery -> schema -> execution loop an LLM agent would perform.
Every protocol response is dumped as raw JSON next to this file.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys

from mcp import ClientSession, StdioServerParameters, stdio_client

PIPEN = os.environ["PIPEN_BIN"]
RAW = pathlib.Path(os.environ["RAW_DIR"])
TESTDATA = pathlib.Path(os.environ["TESTDATA"])
OUTDIR = pathlib.Path(os.environ["OUTDIR"])


def dump(name: str, obj: object) -> None:
    text = json.dumps(obj, indent=2, default=str, ensure_ascii=False)
    (RAW / name).write_text(text, encoding="utf-8")
    print(f"\n===== {name} =====")
    print(text)
    sys.stdout.flush()


async def main() -> int:
    params = StdioServerParameters(command=PIPEN, args=["mcp"])
    print(f"$ {PIPEN} mcp            # transport default = stdio")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            dump("05a_initialize.json", init.model_dump(mode="json", exclude_none=True))

            tools = await session.list_tools()
            dump("05b_list_tools.json", tools.model_dump(mode="json", exclude_none=True))

            r1 = await session.call_tool("get_namespaces", {})
            dump("05c_call_get_namespaces.json", r1.model_dump(mode="json", exclude_none=True))

            r2 = await session.call_tool("get_processes", {"ns": "demo_ns"})
            dump("05d_call_get_processes.json", r2.model_dump(mode="json", exclude_none=True))

            r3 = await session.call_tool("get_process", {"ns": "demo_ns", "proc": "FastqStats"})
            dump("05e_call_get_process.json", r3.model_dump(mode="json", exclude_none=True))

            r3b = await session.call_tool(
                "get_processes", {"ns": "demo_extra_ns"}
            )
            dump("05f_call_get_processes_extra_ns.json", r3b.model_dump(mode="json", exclude_none=True))

            # the unknown-namespace path: schema/contract behaviour an agent sees
            rbad = await session.call_tool("get_processes", {"ns": "no_such_ns"})
            dump("05g_call_get_processes_unknown.json", rbad.model_dump(mode="json", exclude_none=True))

            args = [
                "--in.r1", str(TESTDATA / "s1_R1.fastq.gz"),
                "--in.r2", str(TESTDATA / "s1_R2.fastq.gz"),
                "--envs.min_length", "50",
                "--envs.sample_id", "mcp_s1",
                "--outdir", str(OUTDIR),
            ]
            print(f"\n$ run_process(ns='demo_ns', proc='FastqStats', arguments={args!r})")
            sys.stdout.flush()
            r4 = await session.call_tool(
                "run_process",
                {"ns": "demo_ns", "proc": "FastqStats", "arguments": args},
            )
            dump("05h_call_run_process.json", r4.model_dump(mode="json", exclude_none=True))

            # resources/prompts surface (expect empty - static tool server)
            try:
                res = await session.list_resources()
                dump("05i_list_resources.json", res.model_dump(mode="json", exclude_none=True))
            except Exception as exc:  # pragma: no cover
                print("list_resources failed:", type(exc).__name__, exc)
            try:
                pr = await session.list_prompts()
                dump("05j_list_prompts.json", pr.model_dump(mode="json", exclude_none=True))
            except Exception as exc:  # pragma: no cover
                print("list_prompts failed:", type(exc).__name__, exc)

    produced = OUTDIR / "FastqStats" / "read_stats.tsv"
    print(f"\nproduced file: {produced} exists={produced.exists()}")
    if produced.exists():
        print("contents: " + repr(produced.read_text()))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
