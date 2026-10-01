#!/usr/bin/env bash
# Step 6: third-party generalisation check in a SEPARATE venv (keeps the demo venv pristine).
# Installs the released biopipen (25 pipen_cli_run namespaces) alongside pipen + pipen-cli-run
# + pipen-mcp + the two demo namespace packages, then queries the namespace union.
set -u
SRC=/mnt/f/E/hermes-workspace/pipen/ai_demo
DEMO=$HOME/aidemo
BIO=$HOME/aidemo_bio
VPY="$BIO/.venv/bin/python"
mkdir -p "$BIO"

echo "### creating venv $BIO/.venv"
rm -rf "$BIO/.venv"
python3 -m venv "$BIO/.venv"

echo "### installing pipen==1.2.3 pipen-cli-run pipen-annotate pipen-mcp + biopipen (PyPI)"
"$VPY" -m pip install --quiet --upgrade pip 2>&1 | tail -2
timeout 900 "$VPY" -m pip install "pipen==1.2.3" pipen-cli-run pipen-annotate pipen-mcp biopipen 2>&1 | tail -25
echo "INSTALL_RC=${PIPESTATUS[0]}"

echo
echo "### versions in the biopipen venv"
"$VPY" -m pip freeze 2>&1 | grep -i -E '^(pipen|biopipen|datar|mcp)' | sort

echo
echo "### namespace entry points visible to pipen-cli-run"
"$VPY" - <<'PY'
from importlib.metadata import distributions
groups = {}
for dist in distributions():
    for ep in dist.entry_points:
        if ep.group == "pipen_cli_run":
            groups[ep.name] = dist.metadata["Name"]
print(f"total namespaces: {len(groups)}")
for ns in sorted(groups):
    print(f"  {ns}  <- {groups[ns]}")
PY

echo
echo "############ pipen run --help  (does discovery reflect installed dists?)"
"$BIO/.venv/bin/pipen" run --help 2>&1 | sed -e 's/\x1b\[[0-9;]*m//g'
echo "RC=$?"

echo
echo "############ pipen run delim --help  (a REAL third-party namespace)"
"$BIO/.venv/bin/pipen" run delim --help 2>&1 | sed -e 's/\x1b\[[0-9;]*m//g'
echo "RC=$?"

echo
echo "############ pipen run misc --help"
"$BIO/.venv/bin/pipen" run misc --help 2>&1 | sed -e 's/\x1b\[[0-9;]*m//g' | head -40
echo "RC=$?"

echo
echo "############ pipen run delim RowsBinder --help  (third-party process schema)"
"$BIO/.venv/bin/pipen" run delim RowsBinder --help 2>&1 | sed -e 's/\x1b\[[0-9;]*m//g'
echo "RC=$?"

echo
echo "############ MCP server in the biopipen venv: get_namespaces / get_processes(delim)"
export PIPEN_BIN="$BIO/.venv/bin/pipen"
export RAW_DIR="$SRC/raw"
export TESTDATA="$DEMO/testdata"
export OUTDIR="$BIO/out_mcp"
PATH="$BIO/.venv/bin:$PATH" "$VPY" - <<'PY' 2>&1 | head -80
import asyncio, json, os
from mcp import ClientSession, StdioServerParameters, stdio_client

async def main():
    params = StdioServerParameters(command=os.environ["PIPEN_BIN"], args=["mcp"])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            ns = await s.call_tool("get_namespaces", {})
            text = ns.content[0].text
            print("namespaces reported by the MCP server:", text.count(":") and len(text.splitlines()) - 3)
            print(text)
            d = await s.call_tool("get_processes", {"ns": "delim"})
            print("\n--- get_processes('delim') (third-party namespace) ---")
            print(d.content[0].text[:1200])
            p = await s.call_tool("get_process", {"ns": "delim", "proc": "RowsBinder"})
            print("\n--- get_process('delim','RowsBinder') ---")
            print(p.content[0].text[:1500])

asyncio.run(main())
PY
echo "MCP_BIO_RC=$?"
