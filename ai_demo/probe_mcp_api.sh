#!/usr/bin/env bash
# Inspect the installed mcp SDK 2.2.0 so the client script uses the right API
set -u
V=$HOME/aidemo/.venv/lib/python3.12/site-packages
echo "=== mcp package top level ==="
ls "$V"/mcp
echo
echo "=== mcp/client ==="
ls "$V"/mcp/client 2>/dev/null
echo
echo "=== mcp/server ==="
ls "$V"/mcp/server 2>/dev/null
echo
echo "=== exports of mcp (dir) ==="
"$HOME/aidemo/.venv/bin/python" - <<'PY'
import mcp, inspect
print("mcp version:", getattr(mcp, "__version__", "?"))
print("mcp file:", mcp.__file__)
print("public:", sorted(n for n in dir(mcp) if not n.startswith("_")))
import mcp.client
print("mcp.client public:", sorted(n for n in dir(mcp.client) if not n.startswith("_")))
try:
    import mcp.client.stdio as s
    print("stdio params:", getattr(s, "StdioServerParameters", None))
except Exception as e:
    print("stdio import err:", e)
try:
    from mcp import ClientSession
    print("ClientSession:", ClientSession)
    print("session methods:", sorted(n for n in dir(ClientSession) if not n.startswith("_")))
except Exception as e:
    print("ClientSession import err:", type(e).__name__, e)
try:
    from mcp.server.mcpserver import MCPServer
    print("MCPServer methods:", sorted(n for n in dir(MCPServer) if not n.startswith("_")))
except Exception as e:
    print("MCPServer import err:", type(e).__name__, e)
PY
echo
echo "=== mcp CLI: mcp --help ==="
"$HOME/aidemo/.venv/bin/mcp" --help 2>&1
echo "RC=$?"
echo
echo "=== pipen mcp --help ==="
"$HOME/aidemo/.venv/bin/pipen" mcp --help 2>&1
echo "RC=$?"
