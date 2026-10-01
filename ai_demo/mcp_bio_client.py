"""Third-party end-to-end: discover + run a BioPipen process over MCP.

Uses the biopipen venv (biopipen 1.5.1 installed from PyPI) and the third-party
namespace `misc` -> process `Shell` (a bash-only process, so no R needed).
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
WORK = pathlib.Path(os.environ["WORK"])


def dump(name: str, obj: object) -> None:
    text = json.dumps(obj, indent=2, default=str, ensure_ascii=False)
    (RAW / name).write_text(text, encoding="utf-8")
    print(f"\n===== {name} =====")
    print(text)
    sys.stdout.flush()


async def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    infile = WORK / "input.txt"
    infile.write_text("agent-provided input\nsecond line\n")
    outdir = WORK / "out"

    params = StdioServerParameters(command=PIPEN, args=["mcp"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            r0 = await session.call_tool("get_namespaces", {})
            dump("13a_bio_get_namespaces.json", r0.model_dump(mode="json", exclude_none=True))

            r1 = await session.call_tool("get_process", {"ns": "misc", "proc": "Shell"})
            dump("13b_bio_get_process_shell.json", r1.model_dump(mode="json", exclude_none=True))

            args = [
                "--in.infile", str(infile),
                "--envs.cmd", "cp $infile $outfile",
                "--out.outfile", "shell_out.txt",
                "--outdir", str(outdir),
            ]
            print(f"\n$ run_process(ns='misc', proc='Shell', arguments={args!r})")
            sys.stdout.flush()
            r2 = await session.call_tool(
                "run_process",
                {"ns": "misc", "proc": "Shell", "arguments": args},
            )
            dump("13c_bio_run_process_shell.json", r2.model_dump(mode="json", exclude_none=True))

    produced = outdir / "Shell" / "shell_out.txt"
    print(f"\nproduced file: {produced} exists={produced.exists()}")
    if produced.exists():
        print("contents: " + repr(produced.read_text()))
    else:
        print("--- workdir listing ---")
        for p in sorted(outdir.rglob("*")):
            print(" ", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
