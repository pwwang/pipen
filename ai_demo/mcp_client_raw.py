"""Raw JSON-RPC over stdio probe: captures the MCP wire protocol verbatim.

Does not use the mcp SDK's session layer for sending - it writes
newline-delimited JSON-RPC 2.0 messages straight to the server's stdin and
echoes every line received on stdout, so the trace is the literal protocol
payload an MCP client exchanges with `pipen mcp`.
"""

from __future__ import annotations

import json
import os
import pathlib
import queue
import subprocess
import sys
import threading
import time

PIPEN = os.environ["PIPEN_BIN"]
RAW = pathlib.Path(os.environ["RAW_DIR"])
TESTDATA = pathlib.Path(os.environ["TESTDATA"])
OUTDIR = pathlib.Path(os.environ["OUTDIR"])
TRACE = RAW / "06_mcp_wire_trace.jsonl"

trace_fh = TRACE.open("w", encoding="utf-8")
counter = {"n": 0}


def log(direction: str, payload: str) -> None:
    rec = {"seq": counter["n"], "dir": direction, "payload": payload}
    counter["n"] += 1
    trace_fh.write(json.dumps(rec) + "\n")
    trace_fh.flush()
    print(f"{direction} {payload}")
    sys.stdout.flush()


class Server:
    def __init__(self, protocol_version: str) -> None:
        self.proc = subprocess.Popen(
            [PIPEN, "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding="utf-8",
        )
        self.q: queue.Queue = queue.Queue()
        threading.Thread(target=self._pump, args=(self.proc.stdout, "OUT"), daemon=True).start()
        threading.Thread(target=self._pump, args=(self.proc.stderr, "SERVER-STDERR"), daemon=True).start()
        self.protocol_version = protocol_version

    def _pump(self, stream, tag) -> None:
        for line in stream:  # type: ignore[union-attr]
            self.q.put((tag, line.rstrip("\n")))

    def send(self, msg: dict) -> None:
        raw = json.dumps(msg)
        log("->", raw)
        assert self.proc.stdin is not None
        self.proc.stdin.write(raw + "\n")
        self.proc.stdin.flush()

    def wait_for_id(self, wanted_id: int, timeout: float = 90.0):
        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise TimeoutError(f"no response for id={wanted_id} within {timeout}s")
            tag, line = self.q.get(timeout=remaining)
            log("<-", f"[{tag}] {line}")
            if tag != "OUT":
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == wanted_id:
                return msg

    def call(self, mid: int, method: str, params: dict | None = None, timeout: float = 90.0):
        msg = {"jsonrpc": "2.0", "id": mid, "method": method}
        if params is not None:
            msg["params"] = params
        self.send(msg)
        return self.wait_for_id(mid, timeout)

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        log("--", f"server exit code: {self.proc.returncode}")


def main() -> int:
    candidates = ["2025-06-18", "2025-03-26", "2024-11-05"]
    srv = None
    for version in candidates:
        print(f"\n########## attempting initialize with protocolVersion={version}")
        s = Server(version)
        try:
            reply = s.call(
                1,
                "initialize",
                {
                    "protocolVersion": version,
                    "capabilities": {},
                    "clientInfo": {"name": "raw-jsonrpc-probe", "version": "0.1.0"},
                },
                timeout=60,
            )
        except Exception as exc:
            print(f"initialize failed for {version}: {type(exc).__name__}: {exc}")
            s.close()
            continue
        if "result" in reply:
            print(f"########## handshake OK, server negotiated: {reply['result'].get('protocolVersion')}")
            srv = s
            break
        print(f"########## server rejected {version}: {json.dumps(reply)[:400]}")
        s.close()

    if srv is None:
        print("NO MCP HANDSHAKE ACHIEVED")
        trace_fh.close()
        return 1

    srv.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    srv.call(2, "tools/list", {})
    srv.call(3, "tools/call", {"name": "get_namespaces", "arguments": {}})
    srv.call(4, "tools/call", {"name": "get_processes", "arguments": {"ns": "demo_ns"}})
    srv.call(5, "tools/call", {"name": "get_process", "arguments": {"ns": "demo_ns", "proc": "FastqStats"}})
    srv.call(
        6,
        "tools/call",
        {
            "name": "run_process",
            "arguments": {
                "ns": "demo_ns",
                "proc": "FastqStats",
                "arguments": [
                    "--in.r1", str(TESTDATA / "s1_R1.fastq.gz"),
                    "--in.r2", str(TESTDATA / "s1_R2.fastq.gz"),
                    "--envs.sample_id", "wire_s1",
                    "--outdir", str(OUTDIR),
                ],
            },
        },
        timeout=300,
    )
    srv.close()
    trace_fh.close()
    produced = OUTDIR / "FastqStats" / "read_stats.tsv"
    print(f"\nproduced file: {produced} exists={produced.exists()}")
    if produced.exists():
        print("contents: " + repr(produced.read_text()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
