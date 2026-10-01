import asyncio
import json
import subprocess
import sys
import textwrap
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import simplug
from pipen.cli import main
from pipen_mcp import PipenMcpPlugin
from . import example_procs, example_pipeline
from .utils import plugin_to_entrypoint

pipen_mcp_plugin_init = PipenMcpPlugin.__init__


def init(self, parser, subparser):
    pipen_mcp_plugin_init(self, parser, subparser)
    self.entry_points["exm_procs"] = plugin_to_entrypoint(example_procs)
    self.entry_points["exm_pipes"] = plugin_to_entrypoint(example_pipeline)


@pytest.fixture
def patch_init():
    PipenMcpPlugin.__init__ = init
    yield
    PipenMcpPlugin.__init__ = pipen_mcp_plugin_init


@contextmanager
def with_argv(argv):
    old = sys.argv[:]
    sys.argv = argv
    yield
    sys.argv = old


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

@pytest.mark.forked
def test_plugin_added(capsys):
    with with_argv(["pipen"]), pytest.raises(SystemExit):
        main()
    assert "mcp" in capsys.readouterr().err


@pytest.mark.forked
def test_mcp_help(capsys, patch_init):
    with with_argv(["pipen", "mcp", "--help"]), pytest.raises(SystemExit):
        main()
    out = capsys.readouterr().out
    assert "--transport" in out
    assert "--host" in out
    assert "--port" in out


# ---------------------------------------------------------------------------
# Schema introspection tests
# ---------------------------------------------------------------------------

@pytest.mark.forked
def test_proc_schema_input_channels():
    from pipen_mcp.introspect import get_proc_schema
    from tests.example_procs import P1

    fields = get_proc_schema(P1)
    names = [f.name for f in fields]
    cli_args = [f.cli_arg for f in fields]

    # P1 has input = "infile:file"
    assert "in_infile" in names
    assert "--in.infile" in cli_args

    # Standard params always present
    assert "outdir" in names
    assert "forks" in names


@pytest.mark.forked
def test_proc_schema_undescribed_proc():
    from pipen_mcp.introspect import get_proc_schema
    from tests.example_procs import UndescribedProc

    fields = get_proc_schema(UndescribedProc)
    names = [f.name for f in fields]
    # input = "a"
    assert "in_a" in names


@pytest.mark.forked
def test_group_schema_defaults():
    from pipen_mcp.introspect import get_group_schema
    from tests.example_pipeline import ExampleProcGroup

    fields = get_group_schema(ExampleProcGroup)
    names = [f.name for f in fields]
    cli_args = [f.cli_arg for f in fields]

    # ExampleProcGroup has DEFAULTS = {"input": ["100"]}
    assert "input" in names
    assert "--ExampleProcGroup.input" in cli_args

    # Standard params
    assert "outdir" in names


@pytest.mark.forked
def test_group_schema_input_default():
    from inspect import Parameter
    from pipen_mcp.introspect import get_group_schema
    from tests.example_pipeline import ExampleProcGroup

    fields = get_group_schema(ExampleProcGroup)
    input_field = next(f for f in fields if f.name == "input")

    # Default comes from DEFAULTS
    assert input_field.default == ["100"]
    # Not required
    assert input_field.default is not Parameter.empty


# ---------------------------------------------------------------------------
# Server build tests
# ---------------------------------------------------------------------------

@pytest.mark.forked
def test_build_server_tool_names():
    from pipen_mcp.server import build_server

    loaded = {
        "exm_procs": example_procs,
        "exm_pipes": example_pipeline,
    }
    server = build_server(loaded)
    tool_names = [t.name for t in server._tool_manager.list_tools()]

    # Exactly the 4 static tools
    assert "get_namespaces" in tool_names
    assert "get_processes" in tool_names
    assert "get_process" in tool_names
    assert "run_process" in tool_names

    # No per-process dynamic tools
    assert not any("exm_procs__" in n or "exm_pipes__" in n for n in tool_names)


# ---------------------------------------------------------------------------
# Discovery tool tests
# ---------------------------------------------------------------------------

@pytest.mark.forked
def test_get_namespaces():
    from pipen_mcp.server import build_server

    loaded = {
        "exm_procs": example_procs,
        "exm_pipes": example_pipeline,
    }
    server = build_server(loaded)
    fn = next(t for t in server._tool_manager.list_tools() if t.name == "get_namespaces").fn
    result = asyncio.run(fn())

    assert "exm_procs" in result
    assert "exm_pipes" in result
    assert "get_processes" in result  # usage hint


@pytest.mark.forked
def test_get_processes():
    from pipen_mcp.server import build_server

    loaded = {"exm_procs": example_procs}
    server = build_server(loaded)
    fn = next(t for t in server._tool_manager.list_tools() if t.name == "get_processes").fn
    result = asyncio.run(fn(ns="exm_procs"))

    assert "P1" in result
    assert "P2" in result
    assert "UndescribedProc" in result
    assert "get_process" in result  # usage hint


@pytest.mark.forked
def test_get_processes_unknown_ns():
    from pipen_mcp.server import build_server

    loaded = {"exm_procs": example_procs}
    server = build_server(loaded)
    fn = next(t for t in server._tool_manager.list_tools() if t.name == "get_processes").fn
    result = asyncio.run(fn(ns="nonexistent"))

    assert "Unknown namespace" in result
    assert "nonexistent" in result


@pytest.mark.forked
def test_get_process():
    from pipen_mcp.server import build_server

    loaded = {"exm_procs": example_procs}
    server = build_server(loaded)
    fn = next(t for t in server._tool_manager.list_tools() if t.name == "get_process").fn
    result = asyncio.run(fn(ns="exm_procs", proc="P1"))

    assert "--in.infile" in result
    assert "run_process" in result  # example in output


@pytest.mark.forked
def test_get_process_unknown():
    from pipen_mcp.server import build_server

    loaded = {"exm_procs": example_procs}
    server = build_server(loaded)
    fn = next(t for t in server._tool_manager.list_tools() if t.name == "get_process").fn
    result = asyncio.run(fn(ns="exm_procs", proc="Nonexistent"))

    assert "Unknown process" in result


# ---------------------------------------------------------------------------
# run_process invocation tests
# ---------------------------------------------------------------------------

def _get_run_fn(loaded):
    from pipen_mcp.server import build_server
    server = build_server(loaded)
    return next(t for t in server._tool_manager.list_tools() if t.name == "run_process").fn


@pytest.mark.forked
def test_run_process_builds_correct_cli_args():
    mock_child = MagicMock()
    mock_child.returncode = 0
    mock_child.communicate = AsyncMock(return_value=(b"done\n", b""))

    loaded = {"exm_procs": example_procs}
    fn = _get_run_fn(loaded)

    with patch("pipen_mcp.server.asyncio.create_subprocess_exec",
               new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_child
        result = asyncio.run(fn(
            ns="exm_procs",
            proc="P1",
            arguments=["--in.infile", "/data/input.txt"],
        ))

    assert result == "done\n"
    call_args = mock_exec.call_args[0]
    assert call_args[0] == "pipen"
    assert call_args[1] == "run"
    assert call_args[2] == "exm_procs"
    assert call_args[3] == "P1"
    assert "--in.infile" in call_args
    assert "/data/input.txt" in call_args


@pytest.mark.forked
def test_run_process_raises_on_nonzero_exit():
    mock_child = MagicMock()
    mock_child.returncode = 1
    mock_child.communicate = AsyncMock(return_value=(b"", b"error output"))

    loaded = {"exm_procs": example_procs}
    fn = _get_run_fn(loaded)

    with patch("pipen_mcp.server.asyncio.create_subprocess_exec",
               new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_child
        with pytest.raises(RuntimeError, match="exited 1"):
            asyncio.run(fn(ns="exm_procs", proc="P1", arguments=["--in.infile", "/f.txt"]))


@pytest.mark.forked
def test_run_process_list_args_passed_through():
    mock_child = MagicMock()
    mock_child.returncode = 0
    mock_child.communicate = AsyncMock(return_value=(b"done", b""))

    loaded = {"exm_pipes": example_pipeline}
    fn = _get_run_fn(loaded)

    with patch("pipen_mcp.server.asyncio.create_subprocess_exec",
               new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_child
        asyncio.run(fn(
            ns="exm_pipes",
            proc="ExampleProcGroup",
            arguments=["--ExampleProcGroup.input", "a", "b", "c"],
        ))

    call_args = list(mock_exec.call_args[0])
    idx = call_args.index("--ExampleProcGroup.input")
    assert call_args[idx + 1] == "a"
    assert call_args[idx + 2] == "b"
    assert call_args[idx + 3] == "c"


@pytest.mark.forked
def test_run_process_unknown_ns_raises():
    loaded = {"exm_procs": example_procs}
    fn = _get_run_fn(loaded)

    with pytest.raises(ValueError, match="Unknown namespace"):
        asyncio.run(fn(ns="nope", proc="P1", arguments=[]))


@pytest.mark.forked
def test_run_process_unknown_proc_raises():
    loaded = {"exm_procs": example_procs}
    fn = _get_run_fn(loaded)

    with pytest.raises(ValueError, match="Unknown process"):
        asyncio.run(fn(ns="exm_procs", proc="Nope", arguments=[]))


# ---------------------------------------------------------------------------
# stdio integration tests — full server lifecycle via subprocess
# ---------------------------------------------------------------------------

# Script template run as a child process; patches the plugin so ONLY the test
# namespaces are registered — skipping the real distributions() scan so we
# don't accidentally import heavy third-party packages (e.g. biopipen).
_STDIO_WRAPPER = textwrap.dedent("""\
    import sys
    sys.path.insert(0, {workspace!r})
    from pipen_mcp import PipenMcpPlugin
    from tests import example_procs, example_pipeline
    from tests.utils import plugin_to_entrypoint
    _orig = PipenMcpPlugin.__init__
    def _patched(self, parser, subparser):
        # Call super().__init__ but bypass the distributions() scan
        from pipen.cli import AsyncCLIPlugin
        AsyncCLIPlugin.__init__(self, parser, subparser)
        self.entry_points = {{
            "exm_procs": plugin_to_entrypoint(example_procs),
            "exm_pipes": plugin_to_entrypoint(example_pipeline),
        }}
        from pipen_mcp.entry import PipenMcpPlugin as _Cls
        subparser = self.subparser
        subparser.add_argument(
            "--transport",
            choices=["stdio", "sse", "streamable-http"],
            default="stdio",
        )
        subparser.add_argument("--host", default="127.0.0.1")
        subparser.add_argument("--port", type=int, default=8520)
    PipenMcpPlugin.__init__ = _patched
    from pipen.cli import main
    main()
""")

# /home/pwwang/github/pipen-mcp
_WORKSPACE = str(__import__("pathlib").Path(__file__).parent.parent)


def _mcp_stdio(*tool_calls: dict, timeout: int = 30) -> dict[int, dict]:
    """Spin up pipen mcp stdio, send tool calls, return id→response dict.

    Uses interactive line-by-line I/O so the server does not shut down before
    it finishes processing every request (which happens when stdin reaches EOF).
    """
    import asyncio as _asyncio

    script = _STDIO_WRAPPER.format(workspace=_WORKSPACE)

    async def _run() -> dict[int, dict]:
        proc = await _asyncio.create_subprocess_exec(
            sys.executable, "-c", script, "mcp",
            stdin=_asyncio.subprocess.PIPE,
            stdout=_asyncio.subprocess.PIPE,
            stderr=_asyncio.subprocess.DEVNULL,
        )

        async def _send(msg: dict) -> None:
            line = json.dumps(msg) + "\n"
            proc.stdin.write(line.encode())
            await proc.stdin.drain()

        async def _read_response(expected_id: int) -> dict:
            while True:
                raw = await _asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
                if not raw:
                    return {}
                try:
                    obj = json.loads(raw.decode())
                    if obj.get("id") == expected_id:
                        return obj
                except json.JSONDecodeError:
                    continue

        # handshake
        await _send({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "test", "version": "0"}},
        })
        await _read_response(1)
        await _send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        responses: dict[int, dict] = {}
        for i, call in enumerate(tool_calls, start=2):
            msg = {
                "jsonrpc": "2.0", "id": i, "method": "tools/call",
                "params": {"name": call["name"], "arguments": call.get("arguments", {})},
            }
            await _send(msg)
            responses[i] = await _read_response(i)

        proc.stdin.close()
        await proc.wait()
        return responses

    return _asyncio.run(_run())


@pytest.mark.forked
def test_stdio_tools_list():
    """Server exposes exactly the 4 static tools."""
    import asyncio as _asyncio

    script = _STDIO_WRAPPER.format(workspace=_WORKSPACE)

    async def _run():
        proc = await _asyncio.create_subprocess_exec(
            sys.executable, "-c", script, "mcp",
            stdin=_asyncio.subprocess.PIPE,
            stdout=_asyncio.subprocess.PIPE,
            stderr=_asyncio.subprocess.DEVNULL,
        )
        # handshake
        proc.stdin.write((json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}) + "\n").encode())
        await proc.stdin.drain()
        # read initialize response
        while True:
            raw = await _asyncio.wait_for(proc.stdout.readline(), timeout=15)
            obj = json.loads(raw.decode())
            if obj.get("id") == 1:
                break
        proc.stdin.write((json.dumps({"jsonrpc":"2.0","method":"notifications/initialized","params":{}}) + "\n").encode())
        await proc.stdin.drain()
        # tools/list
        proc.stdin.write((json.dumps({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}) + "\n").encode())
        await proc.stdin.drain()
        while True:
            raw = await _asyncio.wait_for(proc.stdout.readline(), timeout=15)
            obj = json.loads(raw.decode())
            if obj.get("id") == 2:
                proc.stdin.close()
                await proc.wait()
                return obj
        return {}

    response = _asyncio.run(_run())
    tool_names = [t["name"] for t in response["result"]["tools"]]
    assert "get_namespaces" in tool_names
    assert "get_processes" in tool_names
    assert "get_process" in tool_names
    assert "run_process" in tool_names
    assert len(tool_names) == 4


@pytest.mark.forked
def test_stdio_get_namespaces():
    responses = _mcp_stdio({"name": "get_namespaces", "arguments": {}})
    text = responses[2]["result"]["content"][0]["text"]
    assert "exm_procs" in text
    assert "exm_pipes" in text
    assert "get_processes" in text


@pytest.mark.forked
def test_stdio_get_processes():
    responses = _mcp_stdio({"name": "get_processes", "arguments": {"ns": "exm_procs"}})
    text = responses[2]["result"]["content"][0]["text"]
    assert "P1" in text
    assert "P2" in text
    assert "UndescribedProc" in text
    assert "get_process" in text


@pytest.mark.forked
def test_stdio_get_processes_unknown():
    responses = _mcp_stdio({"name": "get_processes", "arguments": {"ns": "no_such_ns"}})
    text = responses[2]["result"]["content"][0]["text"]
    assert "Unknown namespace" in text
    assert "no_such_ns" in text


@pytest.mark.forked
def test_stdio_get_process():
    responses = _mcp_stdio({"name": "get_process", "arguments": {"ns": "exm_procs", "proc": "P1"}})
    text = responses[2]["result"]["content"][0]["text"]
    assert "--in.infile" in text
    assert "run_process" in text


@pytest.mark.forked
def test_stdio_get_process_unknown():
    responses = _mcp_stdio({"name": "get_process", "arguments": {"ns": "exm_procs", "proc": "Nonexistent"}})
    text = responses[2]["result"]["content"][0]["text"]
    assert "Unknown process" in text


@pytest.mark.forked
def test_stdio_multiple_calls_in_one_session():
    """Chain get_namespaces and get_processes in one server session."""
    responses = _mcp_stdio(
        {"name": "get_namespaces", "arguments": {}},
        {"name": "get_processes", "arguments": {"ns": "exm_pipes"}},
    )
    ns_text = responses[2]["result"]["content"][0]["text"]
    proc_text = responses[3]["result"]["content"][0]["text"]
    assert "exm_procs" in ns_text
    assert "ExampleProcGroup" in proc_text


# ---------------------------------------------------------------------------
# HTTP integration tests — SSE and streamable-http transports
# ---------------------------------------------------------------------------

def _find_free_port() -> int:
    """Return a free TCP port on localhost."""
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> None:
    """Poll TCP port until it accepts connections or timeout."""
    import asyncio as _asyncio
    import socket as _socket

    deadline = _asyncio.get_event_loop().time() + timeout
    while True:
        try:
            with _socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            if _asyncio.get_event_loop().time() >= deadline:
                raise TimeoutError(f"{host}:{port} not ready after {timeout}s")
            await _asyncio.sleep(0.3)


async def _http_tool_calls(
    transport: str,
    host: str,
    port: int,
    *tool_calls: dict,
    connect_timeout: float = 10.0,
    call_timeout: float = 15.0,
) -> list[str]:
    """Connect to an HTTP MCP server, call tools, return list of text responses."""
    import asyncio as _asyncio
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamable_http_client

    await _wait_for_port(host, port)

    if transport == "sse":
        url = f"http://{host}:{port}/sse"
        async with sse_client(url, timeout=connect_timeout, sse_read_timeout=call_timeout) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                results = []
                for call in tool_calls:
                    resp = await _asyncio.wait_for(
                        session.call_tool(call["name"], call.get("arguments", {})),
                        timeout=call_timeout,
                    )
                    text = resp.content[0].text if resp.content else ""
                    results.append(text)
                return results
    else:
        url = f"http://{host}:{port}/mcp/"
        async with streamable_http_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                results = []
                for call in tool_calls:
                    resp = await _asyncio.wait_for(
                        session.call_tool(call["name"], call.get("arguments", {})),
                        timeout=call_timeout,
                    )
                    text = resp.content[0].text if resp.content else ""
                    results.append(text)
                return results


def _run_http_server_test(
    transport: str,
    *tool_calls: dict,
) -> list[str]:
    """Start pipen mcp with *transport*, run *tool_calls*, return responses."""
    import asyncio as _asyncio

    port = _find_free_port()
    script = _STDIO_WRAPPER.format(workspace=_WORKSPACE)
    cli = [sys.executable, "-c", script, "mcp", "--transport", transport, "--port", str(port)]

    proc = subprocess.Popen(
        cli,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        async def _call():
            return await _http_tool_calls(transport, "127.0.0.1", port, *tool_calls)

        return _asyncio.run(_call())
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.mark.forked
def test_sse_tools_list():
    """SSE server exposes exactly the 4 static tools."""
    import asyncio as _asyncio
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    port = _find_free_port()
    script = _STDIO_WRAPPER.format(workspace=_WORKSPACE)
    cli = [sys.executable, "-c", script, "mcp", "--transport", "sse", "--port", str(port)]

    proc = subprocess.Popen(cli, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        async def _list():
            await _wait_for_port("127.0.0.1", port)
            async with sse_client(f"http://127.0.0.1:{port}/sse", timeout=10) as (r, w):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [t.name for t in result.tools]

        tool_names = _asyncio.run(_list())
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    assert "get_namespaces" in tool_names
    assert "get_processes" in tool_names
    assert "get_process" in tool_names
    assert "run_process" in tool_names
    assert len(tool_names) == 4


@pytest.mark.forked
def test_sse_get_namespaces():
    texts = _run_http_server_test("sse", {"name": "get_namespaces", "arguments": {}})
    assert "exm_procs" in texts[0]
    assert "exm_pipes" in texts[0]


@pytest.mark.forked
def test_sse_get_processes():
    texts = _run_http_server_test(
        "sse",
        {"name": "get_processes", "arguments": {"ns": "exm_procs"}},
    )
    assert "P1" in texts[0]
    assert "P2" in texts[0]


@pytest.mark.forked
def test_sse_get_process():
    texts = _run_http_server_test(
        "sse",
        {"name": "get_process", "arguments": {"ns": "exm_procs", "proc": "P1"}},
    )
    assert "--in.infile" in texts[0]
    assert "run_process" in texts[0]


@pytest.mark.forked
def test_streamable_http_tools_list():
    """Streamable-HTTP server exposes exactly the 4 static tools."""
    import asyncio as _asyncio
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    port = _find_free_port()
    script = _STDIO_WRAPPER.format(workspace=_WORKSPACE)
    cli = [sys.executable, "-c", script, "mcp", "--transport", "streamable-http", "--port", str(port)]

    proc = subprocess.Popen(cli, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        async def _list():
            await _wait_for_port("127.0.0.1", port)
            async with streamable_http_client(f"http://127.0.0.1:{port}/mcp/") as (r, w):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [t.name for t in result.tools]

        tool_names = _asyncio.run(_list())
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    assert "get_namespaces" in tool_names
    assert "get_processes" in tool_names
    assert "get_process" in tool_names
    assert "run_process" in tool_names
    assert len(tool_names) == 4


@pytest.mark.forked
def test_streamable_http_get_namespaces():
    texts = _run_http_server_test(
        "streamable-http", {"name": "get_namespaces", "arguments": {}}
    )
    assert "exm_procs" in texts[0]
    assert "exm_pipes" in texts[0]


@pytest.mark.forked
def test_streamable_http_get_process():
    texts = _run_http_server_test(
        "streamable-http",
        {"name": "get_process", "arguments": {"ns": "exm_procs", "proc": "P1"}},
    )
    assert "--in.infile" in texts[0]
    assert "run_process" in texts[0]
