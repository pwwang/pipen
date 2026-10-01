#!/usr/bin/env bash
# Exact signatures of the mcp 2.2.0 client entry points
set -u
"$HOME/aidemo/.venv/bin/python" - <<'PY'
import inspect
from mcp import ClientSession, StdioServerParameters
from mcp import stdio_client
print("stdio_client:", inspect.signature(stdio_client))
print("StdioServerParameters fields:", list(StdioServerParameters.model_fields))
print("ClientSession.__init__:", inspect.signature(ClientSession.__init__))
print("ClientSession.call_tool:", inspect.signature(ClientSession.call_tool))
print("ClientSession.list_tools:", inspect.signature(ClientSession.list_tools))
print("ClientSession.initialize:", inspect.signature(ClientSession.initialize))
from mcp.server.mcpserver import MCPServer
try:
    print("MCPServer.__init__:", inspect.signature(MCPServer.__init__))
except Exception as e:
    print("sig err", e)
print("run_stdio_async:", inspect.signature(MCPServer.run_stdio_async))
print("run_streamable_http_async:", inspect.signature(MCPServer.run_streamable_http_async))
PY
