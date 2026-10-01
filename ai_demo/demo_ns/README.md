# demo-ns — pipen CLI/MCP integration surface

A deliberately tiny, dependency-free `pipen` namespace package used to
demonstrate the paper claim that *declaring a process class is the entire
integration surface*:

* `pipen run demo_ns FastqStats --help` → auto-generated CLI argument schema
* `get_processes` / `run_process` MCP tools → the same schema for an LLM agent

The whole package is `demo_ns/__init__.py` (two `Proc` subclasses) plus the
`[project.entry-points.pipen_cli_run]` table in `pyproject.toml`.
