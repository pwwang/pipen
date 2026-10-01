"""Third-party end-to-end (retry): BioPipen `misc` -> `Shell` discovered and run over MCP.

Run after `pipen report update` installed pipen-report's npm frontend in this venv.
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

            t = await session.list_tools()
            (RAW / "17a_bio_list_tools.json").write_text(
                json.dumps(t.model_dump(mode="json", exclude_none=True), indent=2), encoding="utf-8"
            )

            r1 = await session.call_tool("get_process", {"ns": "misc", "proc": "Shell"})
            dump("17b_bio_get_process_shell.json", r1.model_dump(mode="json", exclude_none=True))

            args = [
                "--in.infile", str(infile),
                "--envs.cmd", "cp $infile $outfile",
                "--outdir", str(outdir),
            ]
            print(f"\n$ run_process(ns='misc', proc='Shell', arguments={args!r})")
            sys.stdout.flush()
            r2 = await session.call_tool(
                "run_process",
                {"ns": "misc", "proc": "Shell", "arguments": args},
            )
            dump("17c_bio_run_process_shell.json", r2.model_dump(mode="json", exclude_none=True))

    produced = outdir / "Shell" / "input.txt"
    print(f"\nproduced file: {produced} exists={produced.exists()}")
    if produced.exists():
        print("contents: " + repr(produced.read_text()))
    else:
        for p in sorted(outdir.rglob("*")):
            print(" ", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
