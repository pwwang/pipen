# `ai_demo/` — the agent facing surface, demonstrated

This directory holds the evidence behind the Application Note's claim that one process declaration
can be projected into two other interfaces: a command line tool and a Model Context Protocol (MCP)
service. It backs the paragraph on the surface seen by agents, and the paper's description of the
framework as AI friendly without AI in the core.

**Read first:** `RESULTS_AI.md` — what was done, in order, with the raw captures listed.

## What was demonstrated

1. **CLI.** A namespace package declaring a `Proc` class produced a grouped, typed command line
   schema whose option descriptions come from the process's docstrings, and running it produced the
   expected output file. A generated `--out.<key>` option was found to be advertised and then
   ignored; that defect was fixed in the plugin before release.
2. **MCP.** A client listed the tools, read a process's argument schema (which carried the
   arguments with type, required flag, default and group) and then executed the process, receiving
   the pipeline's own log and the output file. `get_process` originally returned rendered text with
   no schema a machine could read; that defect was fixed before release as well.
3. **Generalisation to a third party library.** Installing the process library Biopipen 1.5.1 added
   its namespaces to both surfaces with no configuration, and one of its processes (`misc/Shell`)
   was discovered and executed over MCP unchanged, with output byte identical to its input.

## Files

| File | Role |
|---|---|
| `RESULTS_AI.md` | the write up: every step, the result, and the caveats, referring to the captures in `raw/` |
| `raw/*.txt` | the captures themselves: probe output, CLI help and run logs, MCP handshake and tool results |
| `demo_ns/`, `demo_extra_ns/` | the minimal namespace packages used as the declared process library |
| `probe_envs.sh`, `probe_mcp_api.sh`, `probe_mcp_sigs.sh`, `inventory.sh` | environment and API probes |
| `copy_src.sh`, `copy_src2.sh` | how the toy packages were staged into fresh environments |
| `mcp_client_raw.py`, `mcp_client_sdk.py`, `mcp_bio_client.py`, `mcp_bio_client2.py` | the MCP clients used, one raw and one through the SDK, and the Biopipen run |

## Caveats recorded with the evidence

- The plugins must be installed, and the namespace must declare the entry point. Both are part of
  the claim in the paper, not incidental setup.
- `run_process` shells out to the pipen console script, so the demonstration exercises the
  installed command rather than an in process call.
- The MCP SDK exposes the process schema under a snake case field name; an earlier probe reported
  no output schema, and the capture in `raw/` records the correction.

Nothing in this directory is a benchmark: it is a capability demonstration, and the paper reports
it as such.
