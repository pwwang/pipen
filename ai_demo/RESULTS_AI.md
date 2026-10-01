# pipen as an "AI-friendly" framework: CLI + MCP integration, demonstrated

Evidence run for the paper claim:

> A process declared as a Python class becomes (a) a **CLI tool** via `pipen-cli-run` and
> (b) an **MCP tool** via `pipen-mcp`, so an LLM agent can discover and run a scientific
> pipeline with no bespoke integration.

Everything below is captured output, not description. Every block is reproduced from a file
under `ai_demo/raw/` (paths in §7). Where a step did **not** work, it says so.

---

## 1. Versions

Machine: Windows 11 host, Linux via `wsl -d Ubuntu-24.04`. Fresh venv created for this demo at
`~/aidemo/.venv` (Python 3.12.2) — the pre-existing `~/bench/.venv` was left untouched.
All plugin versions came from **PyPI** (no editable fallback was needed): the install resolved
`pipen-1.2.3-py3-none-any.whl` and friends with `PIP_INSTALL_RC=0` (`raw/01_install.txt`).

| Package | Version | Source | Notes |
|---|---|---|---|
| `pipen` | **1.2.3** | PyPI wheel | ships the `pipen` console script and the `pipen.cli` plugin host |
| `pipen-cli-run` | **1.0.6** | PyPI wheel | CLI plugin `run`; entry-point group `pipen_cli_run` |
| `pipen-annotate` | **1.0.6** | PyPI wheel | docstring → `Input:`/`Envs:` annotations |
| `pipen-args` | **1.3.0** | PyPI wheel | pulls arguments out of the annotations (pulled in by pipen-cli-run) |
| `pipen-mcp` | **0.1.0** | PyPI wheel | CLI plugin `mcp`; builds the MCP server |
| `mcp` | **2.2.0** | PyPI wheel | MCP SDK (`mcp[cli]`), required by pipen-mcp |
| `xqute` | 2.2.0 | PyPI wheel | pipen's job runner |
| `simplug` | 0.5.7 | PyPI wheel | plugin framework |
| `argx` | 0.4.4 | PyPI wheel | argument parser used by pipen-args |

Verification commands (verbatim from `raw/01_install.txt`):

```
$ python3 -m venv ~/aidemo/.venv
$ ~/aidemo/.venv/bin/pip install "pipen==1.2.3" pipen-cli-run pipen-annotate pipen-mcp "mcp[cli]"
...
Successfully installed ... mcp-2.2.0 pipen-1.2.3 pipen-annotate-1.0.6 pipen-args-1.3.0
pipen-cli-run-1.0.6 pipen-mcp-0.1.0 xqute-2.2.0 simplug-0.5.7 argx-0.4.4
PIP_INSTALL_RC=0
```

```
$ pip freeze | grep -i -E 'pipen|xqute|simplug|argx|^mcp'
mcp==2.2.0
pipen-annotate==1.0.6
pipen-args==1.3.0
pipen-cli-run==1.0.6
pipen-mcp==0.1.0
pipen==1.2.3
simplug==0.5.7
xqute==2.2.0
```

Plugin inventory as pipen itself reports it (`raw/07_extra.txt`):

```
$ pipen plugins
Pipen version: 1.2.3

Pipen plugins:
- args: (version: 1.3.0)

CLI plugins:
- mcp    : (version: 0.1.0)
- cli-run: (version: 1.0.6)
```

Install route: **PyPI releases only** — no `pip install -e` of the local checkouts, no network
or TLS fallback needed.

---

## 2. The demo package: declaring a class is (almost) the whole integration surface

The integration surface for a new scientific process is one class plus one entry-point line.
Files (all in `ai_demo/`):

* `demo_ns/demo_ns/__init__.py` — 71 lines, two `Proc` subclasses, no CLI/JSON/MCP code
* `demo_ns/pyproject.toml` — 20 lines, of which the integration is these two:

```toml
[project.entry-points.pipen_cli_run]
demo_ns = "demo_ns"
```

* `demo_extra_ns/` — a second, independent package used for the generalisation check

The process declares typed `input`/`output` channels, an `envs` option, and a shell `script`;
the `Input:`/`Envs:`/`Output:` docstring sections become the user-facing help text:

```python
class FastqStats(Proc):
    """Read-length statistics of a paired-end FASTQ sample

    Input:
        r1: gzipped R1 FASTQ file of the sample
        r2: gzipped R2 FASTQ file of the sample

    Envs:
        min_length: Reads shorter than this many bases are not counted
        sample_id: Label written into the first column of the output table

    Output:
        stats: TSV table of per-sample read-length statistics
    """

    input = "r1:file, r2:file"
    output = "stats:file:read_stats.tsv"
    envs = {"min_length": 0, "sample_id": "sample"}
    script = """
    zcat {{in.r1}} {{in.r2}} \
      | awk -v min={{envs.min_length}} -v sid={{envs.sample_id}} '
          NR % 4 == 2 { ... }
          END { printf("%s\t%d\t%d\t%d\t%.1f\n", sid, n, kept, max, len / n); }
        ' > {{out.stats}}
    """
```

```
$ pip install -e ~/aidemo/demo_ns -e ~/aidemo/demo_extra_ns
Successfully installed demo-extra-ns-0.1.0 demo-ns-0.1.0
PIP_INSTALL_RC=0

# registered entry points in group 'pipen_cli_run'
demo-extra-ns__demo_extra_ns -> demo_extra_ns
demo-ns__demo_ns -> demo_ns
```

```python
# raw/01_install.txt — the released pipen 1.2.3 wheel does ship the CLI host
import importlib.util, pipen
pipen.__version__  = 1.2.3
pipen.cli spec     = ModuleSpec(name='pipen.cli', ... '/pipen/cli/__init__.py')
cli dir listing    = ['_hooks.py', '_main.py', 'profile.py', 'help.py', 'plugins.py',
                      'version.py', '__init__.py']
```

---

## 3. CLI surface (claim a)

Captured from `raw/02_cli.txt` (raw file keeps ANSI styling; the blocks below are the same bytes
with escape sequences stripped, as produced by a second capture in `raw/07_extra.txt`).

### 3.1 `pipen --help` — the plugins add subcommands

```
$ pipen --help
Usage: pipen [-h] {mcp,run,profile,plugins,version,help} ...

CLI Tool for pipen v1.2.3

Options:
  -h, --help            show this help message and exit

Subcommands:
    mcp                 Expose pipen processes/pipelines as MCP tools
    run                 Run a process or a pipeline
    profile             List available profiles.
    plugins             List installed plugins
    version             Print versions of pipen and its dependencies
    help                Print help for commands
RC=0
```

### 3.2 `pipen run --help` — namespaces discovered from installed distributions

```
$ pipen run --help
Usage: pipen run [-h] {demo_extra_ns,demo_ns} ...

Run a process or a pipeline

Options:
  -h, --help            show this help message and exit

Process Namespaces:
    demo_extra_ns       A second, independent pipen namespace package
                        (generalisation check).
    demo_ns             Toy scientific namespace used to demonstrate pipen's
                        agent-facing surface.
RC=0
```

### 3.3 `pipen run demo_ns --help` — processes discovered from the module

```
$ pipen run demo_ns --help
Usage: pipen run demo_ns [-h] {CountReads,FastqStats} ...

Options:
  -h, --help            show this help message and exit

Processes / Pipelines:
    CountReads          Count the reads in a single FASTQ file
    FastqStats          Read-length statistics of a paired-end FASTQ sample
RC=0
```

### 3.4 `pipen run demo_ns FastqStats --help` — **the auto-generated argument schema**

This is the artifact an agent reads. Note what is present without any hand-written parser:
per-channel flags, metavars (`R1 [R1 ...]` for a multi-value file input), typed `int`/`str`
options for `envs`, docstring-derived descriptions, and `[default: ...]` for every defaulted
option.

```
$ pipen run demo_ns FastqStats --help
Usage: pipen [-h | -h+] [options]

Read-length statistics of a paired-end FASTQ sample
Use `@configfile` to load default values for the options.

Pipeline Options:
  --name NAME           The name for the pipeline, will affect the default
                        workdir and outdir. [default: FastqStats]
  --profile PROFILE     The default profile from the configuration to run the
                        pipeline. ...
  --outdir OUTDIR       The output directory of the pipeline [default:
                        ./<name>-output]
  --forks FORKS         How many jobs to run simultaneously by the scheduler
  --scheduler SCHEDULER
                        The scheduler to run the jobs
  --output_flatten, --output-flatten
                        Whether to flatten the output from jobs of the process
                        (without creating subdirectories with job indexes).

Namespace <envs>:
  --envs ENVS           Environment variables for the process [default:
                        {'min_length': 0, 'sample_id': 'sample'}]
  --envs.min_length MIN_LENGTH, --envs.min-length MIN_LENGTH
                        Reads shorter than this many bases are not counted
                        [default: 0]
  --envs.sample_id SAMPLE_ID, --envs.sample-id SAMPLE_ID
                        Label written into the first column of the output
                        table [default: sample]

Namespace <in>:
  --in.r1 R1 [R1 ...]   gzipped R1 FASTQ file of the sample
  --in.r2 R2 [R2 ...]   gzipped R2 FASTQ file of the sample

Namespace <out>:
  --out.stats STATS     TSV table of per-sample read-length statistics
                        [default: read_stats.tsv]

Options:
  -h, --help, -h+, --help+
                        show this help message and exit (with + for more
                        options)
RC=0
```

**What an LLM agent sees here.** (i) arguments are *grouped and named* by channel
(`--in.*`, `--envs.*`, `--out.*`) rather than positionally; (ii) required vs. optional is
explicit — `--in.r1`/`--in.r2` have no default and therefore must be supplied, while
`--envs.min_length` shows `[default: 0]`; (iii) types are visible as metavars and in the MCP
schema as JSON-Schema types (`<int>`, `<bool>`, `string`, `array`); (iv) every option carries a
natural-language description taken verbatim from the class docstring; (v) the `-h+` escape
hatch exposes the full option set — `--help` prints 12 option lines, `--help+` prints 24,
adding `--workdir`, `--error_strategy`, `--cache`, `--plugins`, `--scheduler_opts`, … 
(`raw/19_helpplus.txt`), so an agent can escalate when it needs the lower-level knobs. The
schema is derived, not declared: it came from `input`/`output`/`envs` plus the docstring.

`CountReads --help` (second process, same mechanism, `--in.fastq`) is in `raw/07_extra.txt`.

---

## 4. Running through the CLI, and the produced file (claim a, end-to-end)

```
$ cd ~/aidemo/run_cli_workdir
$ pipen run demo_ns FastqStats \
    --in.r1 ~/aidemo/testdata/s1_R1.fastq.gz \
    --in.r2 ~/aidemo/testdata/s1_R2.fastq.gz \
    --envs.min_length 50 --envs.sample_id s1 --outdir ./out
09-30 21:45:13 I core    plugins         : args v1.3.0
09-30 21:45:13 I core    # procs         : 1
09-30 21:45:13 I core    outdir          : out
09-30 21:45:13 I core    scheduler       : local
09-30 21:45:13 I core    workdir         : .pipen/FastqStats
09-30 21:45:13 I core    ╭══════════════════════════════ FastqStats ═══════════════════════════════╮
09-30 21:45:13 I core    ║ Read-length statistics of a paired-end FASTQ sample                     ║
09-30 21:45:13 I core    ╰═════════════════════════════════════════════════════════════════════════╯
09-30 21:45:13 I core    FastqStats: <<< [START]
09-30 21:45:13 I core    FastqStats: >>> [END]
RC=0

$ find out -type f
out/FastqStats/read_stats.tsv

$ cat out/FastqStats/read_stats.tsv
s1	80	57	80	59.9
```

The class's `script` was rendered by pipen into a real bash job (`.pipen/FastqStats/FastqStats/0/job.script`),
with `{{in.r1}}`, `{{envs.min_length}}` and `{{out.stats}}` substituted:

```
zcat /home/pwwang/aidemo/testdata/s1_R1.fastq.gz /home/pwwang/aidemo/testdata/s1_R2.fastq.gz \
  | awk -v min=50 -v sid=s1 '
      NR % 4 == 2 { ... }
      END { printf("%s\t%d\t%d\t%d\t%.1f\n", sid, n, kept, max, len / n); }
    ' > out/FastqStats/read_stats.tsv
```

Job bookkeeping captured alongside (`raw/11_jobscript.txt`): `job.rc` = `0`, `job.status` = `6`
(succeeded), `job.stdout`/`job.stderr` empty.

A second, independently installed namespace was run the same way, with no extra code
(`raw/02_cli.txt`):

```
$ pipen run demo_extra_ns FastaGc --in.fasta ~/aidemo/testdata/toy.fasta --outdir ~/aidemo/out_gc
RC=0
$ cat ~/aidemo/out_gc/FastaGc/gc.tsv
34	0.5294
```

---

## 5. MCP surface, driven by a real MCP client (claim b)

Server start (part of the plugin surface, `raw/07_extra.txt`):

```
$ pipen mcp --help
Usage: pipen mcp [-h] [--transport {stdio,sse,streamable-http}] [--host HOST]
                 [--port PORT]

Expose pipen processes/pipelines as MCP tools

Options:
  -h, --help            show this help message and exit
  --transport {stdio,sse,streamable-http}
                        MCP transport to use [default: stdio]
  --host HOST           Host to bind to for sse/streamable-http [default:
                        127.0.0.1]
  --port PORT           Port to listen on for sse/streamable-http [default:
                        8520]
RC=0
```

Transport used: **stdio** (the default). Two independent clients were run against it:
(a) the official `mcp` SDK 2.2.0 client (`ClientSession` + `stdio_client`), and
(b) a hand-written raw JSON-RPC 2.0 client that writes newline-delimited messages to the
server's stdin and echoes every line received, so the protocol payloads are captured verbatim.

### 5.1 Handshake and tool listing (`raw/05a_initialize.json`, `raw/05b_list_tools.json`)

```
{"protocol_version": "2025-11-25", "capabilities": {"tools": {"list_changed": false}, ...},
 "server_info": {"name": "pipen-mcp", "version": ""}}
```

```
"tools": [
  {"name": "get_namespaces",
   "description": "List all available namespaces registered with pipen. Start here to discover what is available.",
   "input_schema": {"properties": {}, "type": "object", "title": "get_namespacesArguments"}},
  {"name": "get_processes",
   "description": "List all processes/pipelines available in a namespace.",
   "input_schema": {"properties": {"ns": {"description": "The namespace name",
                                          "title": "Ns", "type": "string"}},
                    "required": ["ns"], "type": "object"}},
  {"name": "get_process",
   "description": "Get the detailed argument schema for a specific process or pipeline, including required and optional CLI arguments.",
   "input_schema": {"properties": {"ns": {...}, "proc": {"description": "The process or pipeline name",
                                                         "title": "Proc", "type": "string"}},
                    "required": ["ns", "proc"], "type": "object"}},
  {"name": "run_process",
   "description": "Run a pipen process or pipeline. Build the arguments list from the schema returned by get_process.",
   "input_schema": {"properties": {"ns": {...}, "proc": {...},
                    "arguments": {"description": "CLI arguments as a flat list, e.g. [\"--in.infile\", \"/path/to/file\", \"--outdir\", \"./out\"]",
                                  "items": {"type": "string"}, "title": "Arguments", "type": "array"}},
                    "required": ["ns", "proc", "arguments"], "type": "object"}}
]
```

Full JSON (unabridged, both `inputSchema` and `outputSchema` per tool):
`raw/05b_list_tools.json`; raw wire form: `raw/06_mcp_wire_trace.jsonl` (id 2).

### 5.2 Discovery: `get_namespaces`, `get_processes` (`raw/05c`, `raw/05d`)

```
{"content": [{"type": "text", "text":
 "Available namespaces:\n\n  demo_extra_ns: A second, independent pipen namespace package (generalisation check).\n  demo_ns: Toy scientific namespace used to demonstrate pipen's agent-facing surface.\n\nUse get_processes('<namespace>') to see available processes."}],
 "is_error": false}
```

```
{"content": [{"type": "text", "text":
 "Namespace: demo_ns\nDescription: Toy scientific namespace used to demonstrate pipen's agent-facing surface.\n\nAvailable processes:\n  CountReads (proc): Count the reads in a single FASTQ file\n  FastqStats (proc): Read-length statistics of a paired-end FASTQ sample\n\nUse get_process('demo_ns', '<process_name>') to see detailed arguments."}],
 "is_error": false}
```

Unknown-namespace handling is graceful rather than a crash (`raw/05g`):

```
"Unknown namespace 'no_such_ns'. Known namespaces: demo_extra_ns, demo_ns"
```

### 5.3 The argument schema an agent consumes: `get_process` (`raw/05e`)

```
Process: FastqStats  (namespace: demo_ns)
Description: Read-length statistics of a paired-end FASTQ sample

Arguments:
  Required:
    --in.r1 <str>  gzipped R1 FASTQ file of the sample
    --in.r2 <str>  gzipped R2 FASTQ file of the sample
  Optional:
    --envs.min_length <int> (default: 0)  Reads shorter than this many bases are not counted
    --envs.sample_id <str> (default: 'sample')  Label written into the first column of the output table
    --outdir <str>  Output directory of the pipeline
    --forks <int>  Number of jobs to run simultaneously
    --scheduler <str>  Scheduler to run the jobs
    --profile <str>  Configuration profile to use
    --cache <str>  Cache strategy: true/false/force

Example:
  run_process("demo_ns", "FastqStats", ["--in.r1", "<value>"])
```

This is the same schema as §3.4, re-rendered for an agent that has no terminal: required vs.
optional, types, defaults, descriptions, and a call example.

### 5.4 Execution over MCP: `run_process` (`raw/05h`, produced file in `raw/05_mcp_run.txt`)

```
$ run_process(ns='demo_ns', proc='FastqStats', arguments=[
    '--in.r1', '.../s1_R1.fastq.gz', '--in.r2', '.../s1_R2.fastq.gz',
    '--envs.min_length', '50', '--envs.sample_id', 'mcp_s1', '--outdir', '.../out_mcp'])

{"content": [{"type": "text", "text": "09-30 21:36:31 I core  ... version: 1.2.3
 ... ╭═══════ FastqStats ═══════╮
 ... ║ Read-length statistics of a paired-end FASTQ sample ║
 ... FastqStats: <<< [START]
 ... FastqStats: >>> [END]"}],
 "is_error": false}

produced file: /home/pwwang/aidemo/out_mcp/FastqStats/read_stats.tsv exists=True
contents: 'mcp_s1\t80\t57\t80\t59.9\n'
```

The raw wire trace shows the same call and response as literal JSON-RPC
(`raw/06_mcp_wire_trace.jsonl`):

```
-> {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "run_process",
    "arguments": {"ns": "demo_ns", "proc": "FastqStats", "arguments": ["--in.r1", "...", ...]}}}
<- {"jsonrpc":"2.0","id":6,"result":{"content":[{"text":"09-30 21:36:38 I core ... FastqStats: >>> [END]","type":"text"}],"isError":false,"structuredContent":{"result":"..."}}}
...
produced file: /home/pwwang/aidemo/out_mcp/FastqStats/read_stats.tsv exists=True
contents: 'wire_s1\t80\t80\t80\t59.9\n'
```

The raw client negotiated `protocolVersion 2025-06-18` on the first try; the SDK client's
session came back with `2025-11-25`. In both cases the server echoed the requested version
rather than downgrading. `list_resources` and `list_prompts` both return empty lists
(`raw/05i`, `raw/05j`) — this is deliberately a static-tools server.

---

## 6. Generalisation: does it work for a third-party namespace?

**Yes.** Discovery, schema *and* execution all work for a real third-party namespace; the only
obstacle encountered was that package's own runtime prerequisite (its npm frontend), which had
to be installed once (§6.3–6.5).

### 6.1 A real third-party distribution registers the same entry-point group

`biopipen` 1.5.1 (PyPI wheel) carries `[pipen_cli_run]` with **24 namespaces**
(`raw/08_jobscript_biopipen.txt`, `raw/10_biopipen.txt`):

```
=== biopipen-1.5.1.dist-info/entry_points.txt ===
[pipen_cli_run]
bam = biopipen.ns.bam
bed = biopipen.ns.bed
cellranger = biopipen.ns.cellranger
...
vcf = biopipen.ns.vcf
web = biopipen.ns.web
```

Installed in a separate venv (`~/aidemo_bio/.venv`, `INSTALL_RC=0`) so the demo venv above stays
pristine; also `biopipen==1.5.1`, `pipen==1.2.3`, `pipen-cli-run==1.0.6`, `pipen-mcp==0.1.0`.

### 6.2 The same CLI and the same MCP tools now report 24 third-party namespaces

`pipen run --help` in that venv (`raw/10_biopipen.txt`):

```
$ pipen run --help
Usage: pipen run [-h]
                 {bam,bed,cellranger,cellranger_pipeline,cnv,cnvkit,cnvkit_pipeline,delim,gene,gsea,misc,pipseeker,plot,protein,regulatory,rnaseq,scrna,scrna_metabolic_landscape,snp,stats,tcgamaf,tcr,vcf,web}
                 ...

Process Namespaces:
    bam                 Tools to process sam/bam/cram files
    bed                 Tools to handle BED files
    ...
    delim               Tools to deal with csv/tsv files
    misc                Misc processes
    ...
RC=0
```

Third-party process listing and schema (`raw/10_biopipen.txt`):

```
$ pipen run delim --help
Usage: pipen run delim [-h] {RowsBinder,SampleInfo} ...

Processes / Pipelines:
    RowsBinder          Bind rows of input files
    SampleInfo          List sample information and perform statistics

$ pipen run delim RowsBinder --help
Namespace <envs>:
  --envs.sep SEP        The separator of the input files [default:      ]
  --envs.header         Whether the input files have header [default: True]
  --envs.filenames FILENAMES
                        Whether to add filename as the last column. ...
Namespace <in>:
  --in.infiles INFILES [INFILES ...]
                        The input files to bind. ...
Namespace <out>:
  --out.outfile OUTFILE
                        The output file with rows bound [default: {{in.infiles | first | stem}}_rbound{{in.infiles | first | ext}}]
RC=0
```

The MCP server in that venv reports the same 24 namespaces and the same third-party schema
(`raw/14_bio_mcp_run.txt`):

```
"Available namespaces:\n\n  bam: Tools to process sam/bam/cram files\n  bed: Tools to handle BED files\n ... web: Get data from the web\n\nUse get_processes('<namespace>') to see available processes."

"Process: RowsBinder  (namespace: delim)\nDescription: Bind rows of input files\n\nArguments:\n  Required:\n    --in.infiles <str>  The input files to bind.\n...\n  Example:\n  run_process(\"delim\", \"RowsBinder\", [\"--in.infiles\", \"<value>\"])"
```

This is the key generalisation result: the namespace list is produced by iterating installed
distributions' entry points at runtime (`pipen_cli_run.entry`/`pipen_mcp.entry` call
`importlib.metadata.distributions()`), so **the tool list is a function of what is installed,
not a hardcoded list**: the demo venv reports exactly the 2 namespaces its 2 installed packages
declare, and this separate venv reports the 24 namespaces that `biopipen` alone contributes.

### 6.3 Third-party **execution** — first attempt failed, then succeeded

The first attempt to run a BioPipen process (`misc` → `Shell`, a bash-only process) over MCP
**failed**, and the failure was in BioPipen's dependency stack rather than in the CLI/MCP
plumbing (`raw/14_bio_mcp_run.txt`):

```
$ pipen run misc Shell --in.infile ... --envs.cmd 'cp $infile $outfile' --outdir ...
09-30 21:47:05 I core    Initializing plugins ...
09-30 21:47:05 I report  Checking npm and frontend dependencies ...
09-30 21:47:05 E report  Frontend dependencies are not installed
09-30 21:47:05 E report  Run `pipen report update` to install them

$ run_process(ns='misc', proc='Shell', arguments=[...])
{"content": [{"type": "text", "text": "Error executing tool run_process"}], "is_error": true}
produced file: .../out/Shell/shell_out.txt exists=False
```

`pipen-report` 1.2.6 (pulled in by `biopipen` → `pipen-board[report]`) aborts plugin
initialisation without its npm frontend, so the pipeline never reaches the job, and the MCP
tool surfaces it as `is_error: true`. `--report false` is not a recognised flag in this build
(`pipen: error: unrecognized arguments: --report false`, `raw/15_bio_report_off.txt`) — so an
agent has no in-band way to opt out.

Fix: `pipen report update` (installs the frontend; `added 107 packages`, `REPORT_UPDATE_RC=0`,
`raw/16_bio_run_retry.txt`). After that the same third-party process runs.

### 6.4 Third-party performance through MCP — end-to-end, after that prerequisite

Same MCP session type as §5, but against a **third-party** namespace
(`raw/17_bio_mcp_ok.txt`, full JSON in `raw/17b_bio_get_process_shell.json`):

```
$ run_process(ns='misc', proc='Shell', arguments=[
    '--in.infile', '/home/pwwang/aidemo_bio/work/input.txt',
    '--envs.cmd', 'cp $infile $outfile',
    '--outdir', '/home/pwwang/aidemo_bio/work/out'])

{"content": [{"type": "text", "text": "09-30 21:49:20 I core ... version: 1.2.3
 ... plugins : args v1.3.0 / poplog v1.1.7 / report v1.2.6 / deprecated v1.0.3
               / verbose v1.1.5 / filters v1.1.3 / log2file v1.1.4 / board v1.2.0
 ... ╔═════════ SHELL ═════════╗"}],
 "is_error": false}

produced file: /home/pwwang/aidemo_bio/work/out/Shell/input.txt exists=True
contents: 'agent-provided input\nsecond line\n'
```

i.e. the agent's input file was copied through BioPipen's `Shell` process, driven entirely by
MCP calls against a package that knows nothing about this demo. The generated job file for the
equivalent CLI run is one line — `cp $infile $outfile` — with `$infile`/`$outfile` bound by
pipen (`raw/17_bio_mcp_ok.txt`), and the output was byte-identical to the input (`diff` →
`IDENTICAL`).

### 6.5 One caveat found in the schema: `--out.<key>` is advertised but ineffective

While running the third-party process we passed `--out.outfile shell_out_cli.txt`; the run
succeeded but wrote the process's *default* filename instead (`raw/16_bio_run_retry.txt`:
`out.outfile: .../out_cli/Shell/input.txt`). The same happens for the demo process
(`raw/18_out_override.txt`):

```
$ pipen run demo_ns FastqStats --in.r1 ... --in.r2 ... --out.stats custom_stats.tsv --outdir ./out
RC=0
$ find out -type f
out/FastqStats/read_stats.tsv        <-- not custom_stats.tsv; exit code was still 0
```

`--out.stats STATS` is listed in `--help` (§3.4) with a default, so an agent will reasonably try
to use it to control the output path — and it silently does nothing. This is worth flagging in
the paper: schema *discoverability* is not the same as schema *effectiveness*.

---

## 7. What this proves / what it does not prove

**Proven with captured output**

1. `pipen` 1.2.3 + `pipen-cli-run` 1.0.6 turn an installed `Proc` class into a working CLI
   subcommand, with an auto-generated, typed, defaulted, documented argument schema
   (§3.4) and a real end-to-end execution producing a real output file (§4). `RC=0`,
   `job.rc=0`.
2. `pipen-mcp` 0.1.0 exposes the same class over MCP with 4 tools; an official MCP SDK client
   and a raw JSON-RPC client both completed handshake → list → read-schema → execute, and the
   MCP-driven execution wrote the output file (`mcp_s1 80 57 80 59.9`) (§5).
3. The mechanism generalises in discovery: installing a third-party distribution (biopipen
   1.5.1) adds its 24 namespaces to both the CLI and the MCP tool list with no configuration
   (§6.2).
4. The mechanism generalises in **execution**: an agent session drove BioPipen's `misc`→`Shell`
   process over MCP (`is_error: false`, output file byte-identical to the input) against a
   package that contains no knowledge of this demo (§6.4).
5. The integration surface is small and declarative: one Python module of 71 lines holding two
   `Proc` subclasses (including their docstrings and awk scripts), plus a two-line
   `[project.entry-points.pipen_cli_run]` table; the same entry point serves both the CLI and
   the MCP server.

**Not proven / limits a reviewer should be told**

1. **Not zero-configuration.** The plugins are *separate PyPI packages*: `pipen` alone has no
   `run`/`mcp` subcommands. Without `pipen-cli-run` + `pipen-annotate` + `pipen-args` there is
   no CLI schema; without `pipen-mcp` + `mcp[cli]` there is no MCP server. The accurate claim is
   "one entry point, no bespoke integration code", not "no extra dependencies".
2. **One entry-point line is still required.** The claim must be phrased as *class +
   entry-point registration*; a bare class in an uninstalled module is invisible to discovery.
3. **Third-party execution needs the third-party package's own prerequisites.** BioPipen
   discovery/schema worked immediately, but running a BioPipen process required
   `pipen report update` (npm frontend, 107 packages) first; most BioPipen processes
   additionally need R, which this environment does not have. That is a property of the
   *installed pipeline package*, not of pipen's CLI/MCP mechanism — but it means "install the
   namespace package and go" only holds where the package's own runtime deps are satisfied.
4. **Schema discoverability ≠ schema effectiveness.** `--out.<key>` is listed in the generated
   help with a default, yet passing it does not change the produced filename and the run still
   exits 0 (§6.5). An agent that trusts the schema can be misled without any error signal.
5. **`run_process` shells out to the `pipen` console script.** If the MCP client's environment
   lacks `pipen` on `PATH`, the call fails with `UnexpectedToolError: Error executing tool
   run_process` / `isError: true` and no output is produced (captured in `raw/05_mcp_run.txt`,
   step 5d). Real deployments must ensure the venv is active for the server process.
6. **MCP tool output is a text log**, not structured per-process results; the agent must read
   the pipeline log text or the output files themselves. Only the four static tools exist;
   resources/prompts are empty.
7. **Version coupling is untested beyond this pair.** The evidence covers pipen 1.2.3 with
   pipen-cli-run 1.0.6 / pipen-mcp 0.1.0 (and, in the biopipen venv, pipen-report 1.2.6 which
   blocked execution until its frontend was installed). pipen-mcp is version 0.1.0 — young,
   single-maintainer, and it pins `pipen-cli-run>=1.0.1` + `pipen-annotate>=1.0` + `mcp[cli]>=2.0`.
8. **stdio-in-container behaviour was not tested.** The demo is stdio over local pipes on one
   machine (`~/aidemo`, Linux under WSL2). `--transport sse|streamable-http` exists in
   `pipen mcp --help` but was not exercised; neither was a container, a remote client, or
   concurrent MCP sessions. Each `run_process` spawns one child `pipen run`, and it inherits
   the server's CWD (relative `--outdir`/workdir land relative to the *server's* CWD).
9. **The tool schemas describe the CLI, not the science.** A reviewer should note that
   `get_process` returns a rendered *text* schema, not a JSON Schema of the process arguments
   (the tool's own `inputSchema` only covers `ns`/`proc`/`arguments`, §5.1). Constraining an
   LLM's arguments therefore still relies on the model reading a text listing — there is no
   machine-validatable per-process JSON Schema yet.

---

## 8. Raw captures (verbatim, unedited)

All paths relative to `F:/E/hermes-workspace/pipen/ai_demo/` (= `/mnt/f/E/hermes-workspace/pipen/ai_demo/` in WSL).

| File | Contents |
|---|---|
| `raw/01_install.txt` | venv creation, full `pip install` log, `pip freeze`/`pip show`, `pipen.cli` presence check, console scripts |
| `raw/02_cli.txt` | `pipen --help`, `run --help`, `run demo_ns --help`, `run demo_ns FastqStats --help`, `run demo_ns CountReads --help`, real run + `ls`/`cat` of output, second-namespace run |
| `raw/03_mcp_api_probe.txt` | installed `mcp` 2.2.0 layout/API, `mcp --help` (CLI: version/dev/run/install), `pipen mcp --help` |
| `raw/04_mcp_signatures.txt` | exact signatures of `stdio_client`, `ClientSession.*`, `MCPServer.*` used by the clients |
| `raw/05_mcp_run.txt` | SDK client run: handshake, `list_tools`, all `tools/call` results, produced file, plus the no-PATH caveat (step 5d) |
| `raw/05a_initialize.json` … `raw/05j_list_prompts.json` | per-call raw JSON of the SDK session: initialize, list_tools, get_namespaces, get_processes (demo_ns, demo_extra_ns, unknown), get_process, run_process, list_resources, list_prompts |
| `raw/06_mcp_wire_trace.jsonl` | raw JSON-RPC stdio trace: every message sent/received, incl. server stderr lines and exit code, with the produced file contents |
| `raw/07_extra.txt` | ANSI-free help captures, `pipen plugins`, `pipen version`, biopipen wheel download check |
| `raw/08_jobscript_biopipen.txt` | biopipen 1.5.1 `entry_points.txt` (24 namespaces); unrelated pre-existing `.pipen` tree |
| `raw/09_workdir_meta.txt` | workdir lookups, `[truncated]` false-positive check, biopipen `Requires-Dist` |
| `raw/10_biopipen.txt` | biopipen venv install, version list, 24 namespaces, `pipen run --help`/`delim`/`misc`/`RowsBinder` help, MCP `get_namespaces`/`get_processes`/`get_process` |
| `raw/11_jobscript.txt` | deterministic CLI rerun: full workdir tree, generated `job.script`, `job.rc`/`job.status`/`job.stdout`, produced file |
| `raw/12_inventory.txt` | integration-surface line counts, entry-point table, capture inventory |
| `raw/13_biopipen_procs.txt` | schemas of `misc` processes (Shell/File2Proc/Str2File/Glob2Dir/Config2File) |
| `raw/14_bio_mcp_run.txt` | biopipen MCP session + the **failed** third-party execution (blocked by pipen-report/npm) |
| `raw/15_bio_report_off.txt` | node/npm availability, `--report false` rejection, pipen-report version |
| `raw/16_bio_run_retry.txt` | `pipen report update` (frontend installed) and the now-successful third-party CLI run |
| `raw/17_bio_mcp_ok.txt` | third-party CLI `cmd.sh`, byte-identical output, and the **successful** MCP-driven third-party run |
| `raw/17a_bio_list_tools.json`, `raw/17b_bio_get_process_shell.json`, `raw/17c_bio_run_process_shell.json` | raw JSON of the biopipen MCP session (tools/list, get_process, run_process) |
| `raw/18_out_override.txt` | `--out.stats custom_stats.tsv` accepted but ignored (`read_stats.tsv` produced, RC=0) |
| `raw/19_helpplus.txt` | `--help` (12 option lines) vs `--help+` (24) for the demo process; options only in the full help |

Reproducing scripts (also in `ai_demo/`): `step1_install.sh`, `step234_cli.sh`, `step3f_helpplus.sh`,
`step4e_jobscript.sh`, `step4g_out_override.sh`, `step5_mcp.sh` (+ `mcp_client_sdk.py`, `mcp_client_raw.py`),
`step6_biopipen.sh`, `step6d_biopipen_proc.sh`, `step6e_bio_mcp.sh` (+ `mcp_bio_client.py`),
`step6f_bio_report.sh`, `step6g_report_update.sh`, `step6h_bio_mcp_ok.sh` (+ `mcp_bio_client2.py`),
`run_capture.sh` (runner that tees to `raw/`), `inventory.sh`.

Demo packages: `demo_ns/` (the toy scientific namespace), `demo_extra_ns/` (second independent
namespace). Reference copies of the installed plugin sources are in `src_ref/`.
