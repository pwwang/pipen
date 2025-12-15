<div align="center">
    <img src="./docs/rtd-logo.png" width="320px">

**A pipeline framework for python**

</div>

______________________________________________________________________

[![Pypi][6]][7] [![Github][8]][9] ![Building][10] [![Docs and API][11]][1] [![Codacy][12]][13] [![Codacy coverage][14]][13] [![Deps][5]][23]

[Documentation][1] | [ChangeLog][2] | [Examples][3] | [API][4]

## Features

- Easy to use
- Nearly zero-configuration
- Nice logging
- Highly extendable
- Cloud support naively

## Installation

```bash
pip install -U pipen
```

## Quickstart

`example.py`

```python
from pipen import Proc, Pipen, run

class P1(Proc):
    """Sort input file"""
    input = "infile"
    input_data = ["/tmp/data.txt"]
    output = "outfile:file:intermediate.txt"
    script = "cat {{in.infile}} | sort > {{out.outfile}}"

class P2(Proc):
    """Paste line number"""
    requires = P1
    input = "infile:file"
    output = "outfile:file:result.txt"
    script = "paste <(seq 1 3) {{in.infile}} > {{out.outfile}}"

# class MyPipeline(Pipen):
#     starts = P1

if __name__ == "__main__":
    # MyPipeline().run()
    run("MyPipeline", starts=P1)
```

```shell
> echo -e "3\n2\n1" > /tmp/data.txt
> python example.py
```

```log
04-17 16:19:35 I core                   _____________________________________   __
04-17 16:19:35 I core                   ___  __ \___  _/__  __ \__  ____/__  | / /
04-17 16:19:35 I core                   __  /_/ /__  / __  /_/ /_  __/  __   |/ /
04-17 16:19:35 I core                   _  ____/__/ /  _  ____/_  /___  _  /|  /
04-17 16:19:35 I core                   /_/     /___/  /_/     /_____/  /_/ |_/
04-17 16:19:35 I core
04-17 16:19:35 I core                               version: 1.0.0
04-17 16:19:35 I core
04-17 16:19:35 I core    ╔═══════════════════════════ MYPIPELINE ════════════════════════════╗
04-17 16:19:35 I core    ║ My pipeline                                                       ║
04-17 16:19:35 I core    ╚═══════════════════════════════════════════════════════════════════╝
04-17 16:19:35 I core    plugins         : verbose v0.14.1
04-17 16:19:35 I core    # procs         : 2
04-17 16:19:35 I core    profile         : default
04-17 16:19:35 I core    outdir          : /path/to/cwd/MyPipeline-output
04-17 16:19:35 I core    cache           : True
04-17 16:19:35 I core    dirsig          : 1
04-17 16:19:35 I core    error_strategy  : ignore
04-17 16:19:35 I core    forks           : 1
04-17 16:19:35 I core    lang            : bash
04-17 16:19:35 I core    loglevel        : info
04-17 16:19:35 I core    num_retries     : 3
04-17 16:19:35 I core    scheduler       : local
04-17 16:19:35 I core    submission_batch: 8
04-17 16:19:35 I core    template        : liquid
04-17 16:19:35 I core    workdir         : /path/to/cwd/.pipen/MyPipeline
04-17 16:19:35 I core    plugin_opts     :
04-17 16:19:35 I core    template_opts   : filters={'realpath': <function realpath at 0x7fc3eba12...
04-17 16:19:35 I core                    : globals={'realpath': <function realpath at 0x7fc3eba12...
04-17 16:19:35 I core    Initializing plugins ...
04-17 16:19:36 I core
04-17 16:19:36 I core    ╭─────────────────────────────── P1 ────────────────────────────────╮
04-17 16:19:36 I core    │ Sort input file                                                   │
04-17 16:19:36 I core    ╰───────────────────────────────────────────────────────────────────╯
04-17 16:19:36 I core    P1: Workdir: '/path/to/cwd/.pipen/MyPipeline/P1'
04-17 16:19:36 I core    P1: <<< [START]
04-17 16:19:36 I core    P1: >>> ['P2']
04-17 16:19:36 I verbose P1: in.infile: /tmp/data.txt
04-17 16:19:36 I verbose P1: out.outfile: /path/to/cwd/.pipen/MyPipeline/P1/0/output/intermediate.txt
04-17 16:19:38 I verbose P1: Time elapsed: 00:00:02.051s
04-17 16:19:38 I core
04-17 16:19:38 I core    ╭═══════════════════════════════ P2 ════════════════════════════════╮
04-17 16:19:38 I core    ║ Paste line number                                                 ║
04-17 16:19:38 I core    ╰═══════════════════════════════════════════════════════════════════╯
04-17 16:19:38 I core    P2: Workdir: '/path/to/cwd/.pipen/MyPipeline/P2'
04-17 16:19:38 I core    P2: <<< ['P1']
04-17 16:19:38 I core    P2: >>> [END]
04-17 16:19:38 I verbose P2: in.infile: /path/to/cwd/.pipen/MyPipeline/P1/0/output/intermediate.txt
04-17 16:19:38 I verbose P2: out.outfile: /path/to/cwd/MyPipeline-output/P2/result.txt
04-17 16:19:41 I verbose P2: Time elapsed: 00:00:02.051s
04-17 16:19:41 I core

             MYPIPELINE: 100%|██████████████████████████████| 2/2 [00:06<00:00, 0.35 procs/s]
```

```shell
> cat ./MyPipeline-output/P2/result.txt
1       1
2       2
3       3
```

## Examples

See more examples at `examples/` and a more realcase example at:

<https://github.com/pwwang/pipen-report/tree/master/example>

## Plugin gallery

Plugins make `pipen` even better.

- [`pipen-annotate`][26]: Use docstring to annotate pipen processes
- [`pipen-args`][19]: Command line argument parser for pipen
- [`pipen-board`][27]: Visualize configuration and running of pipen pipelines on the web
- [`pipen-diagram`][18]: Draw pipeline diagrams for pipen
- [`pipen-dry`][20]: Dry runner for pipen pipelines
- [`pipen-filters`][17]: Add a set of useful filters for pipen templates.
- [`pipen-lock`][25]: Process lock for pipen to prevent multiple runs at the same time.
- [`pipen-log2file`][28]: Save running logs to file for pipen
- [`pipen-poplog`][30]: Populate logs from jobs to running log of the pipeline
- [`pipen-report`][16]: Generate report for pipen
- [`pipen-runinfo`][29]: Save running information to file for pipen
- [`pipen-verbose`][15]: Add verbosal information in logs for pipen.
- [`pipen-gcs`][32]: A plugin for pipen to handle files in Google Cloud Storage.
- [`pipen-deprecated`][34]: A pipen plugin to mark processes as deprecated.
- [`pipen-cli-init`][21]: A pipen CLI plugin to create a pipen project (pipeline)
- [`pipen-cli-ref`][31]: Make reference documentation for processes
- [`pipen-cli-require`][24]: A pipen cli plugin check the requirements of a pipeline
- [`pipen-cli-run`][22]: A pipen cli plugin to run a process or a pipeline
- [`pipen-cli-gbatch`][33]: A pipen cli plugin to submit pipeline to Google Batch Jobs

[1]: https://pwwang.github.io/pipen
[2]: https://pwwang.github.io/pipen/CHANGELOG
[3]: https://pwwang.github.io/pipen/examples
[4]: https://pwwang.github.io/pipen/api/pipen
[5]: https://img.shields.io/librariesio/release/pypi/pipen?style=flat-square
[6]: https://img.shields.io/pypi/v/pipen?style=flat-square
[7]: https://pypi.org/project/pipen/
[8]: https://img.shields.io/github/v/tag/pwwang/pipen?style=flat-square
[9]: https://github.com/pwwang/pipen
[10]: https://img.shields.io/github/actions/workflow/status/pwwang/pipen/build.yml?style=flat-square
[11]: https://img.shields.io/github/actions/workflow/status/pwwang/pipen/docs.yml?label=docs&style=flat-square
[12]: https://img.shields.io/codacy/grade/cf1c6c97e5c4480386a05b42dec10c6e?style=flat-square
[13]: https://app.codacy.com/gh/pwwang/pipen
[14]: https://img.shields.io/codacy/coverage/cf1c6c97e5c4480386a05b42dec10c6e?style=flat-square
[15]: https://github.com/pwwang/pipen-verbose
[16]: https://github.com/pwwang/pipen-report
[17]: https://github.com/pwwang/pipen-filters
[18]: https://github.com/pwwang/pipen-diagram
[19]: https://github.com/pwwang/pipen-args
[20]: https://github.com/pwwang/pipen-dry
[21]: https://github.com/pwwang/pipen-cli-init
[22]: https://github.com/pwwang/pipen-cli-run
[23]: https://libraries.io/github/pwwang/pipen#repository_dependencies
[24]: https://github.com/pwwang/pipen-cli-require
[25]: https://github.com/pwwang/pipen-lock
[26]: https://github.com/pwwang/pipen-annotate
[27]: https://github.com/pwwang/pipen-board
[28]: https://github.com/pwwang/pipen-log2file
[29]: https://github.com/pwwang/pipen-runinfo
[30]: https://github.com/pwwang/pipen-poplog
[31]: https://github.com/pwwang/pipen-cli-ref
[32]: https://github.com/pwwang/pipen-gcs
[33]: https://github.com/pwwang/pipen-cli-gbatch
[34]: https://github.com/pwwang/pipen-deprecated
