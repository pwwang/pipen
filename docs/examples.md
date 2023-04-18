
You can find the source code of the examples under directory `examples/` in the github repository.

Theses examples including:

## Caching

When run the script the second time, you may see from the logs that jobs are cached:

```log
❯ python examples/caching.py
[09/13/21 06:10:03] I main                        _____________________________________   __
[09/13/21 06:10:03] I main                        ___  __ \___  _/__  __ \__  ____/__  | / /
[09/13/21 06:10:03] I main                        __  /_/ /__  / __  /_/ /_  __/  __   |/ /
[09/13/21 06:10:03] I main                        _  ____/__/ /  _  ____/_  /___  _  /|  /
[09/13/21 06:10:03] I main                        /_/     /___/  /_/     /_____/  /_/ |_/
[09/13/21 06:10:03] I main
[09/13/21 06:10:03] I main                                     version: 0.1.0
[09/13/21 06:10:03] D main
[09/13/21 06:10:03] D main    Building process relationships:
[09/13/21 06:10:03] D main    - Start processes: [<Proc:AProcess>]
[09/13/21 06:10:03] I main
[09/13/21 06:10:03] I main    ╭══════════════════════════════════ PIPEN-0 ═══════════════════════════════════╮
[09/13/21 06:10:03] I main    ║  # procs          = 1                                                        ║
[09/13/21 06:10:03] I main    ║  plugins          = ['main', 'verbose-0.0.1']                                ║
[09/13/21 06:10:03] I main    ║  profile          = default                                                  ║
[09/13/21 06:10:03] I main    ║  outdir           = Pipen-output                                          ║
[09/13/21 06:10:03] I main    ║  cache            = True                                                     ║
[09/13/21 06:10:03] I main    ║  dirsig           = 1                                                        ║
[09/13/21 06:10:03] I main    ║  error_strategy   = ignore                                                   ║
[09/13/21 06:10:03] I main    ║  forks            = 1                                                        ║
[09/13/21 06:10:03] I main    ║  lang             = bash                                                     ║
[09/13/21 06:10:03] I main    ║  loglevel         = debug                                                    ║
[09/13/21 06:10:03] I main    ║  num_retries      = 3                                                        ║
[09/13/21 06:10:03] I main    ║  plugin_opts      = {}                                                       ║
[09/13/21 06:10:03] I main    ║  plugins          = None                                                     ║
[09/13/21 06:10:03] I main    ║  scheduler        = local                                                    ║
[09/13/21 06:10:03] I main    ║  scheduler_opts   = {}                                                       ║
[09/13/21 06:10:03] I main    ║  submission_batch = 8                                                        ║
[09/13/21 06:10:03] I main    ║  template         = liquid                                                   ║
[09/13/21 06:10:03] I main    ║  template_opts    = {}                                                       ║
[09/13/21 06:10:03] I main    ║  workdir          = ./.pipen                                                 ║
[09/13/21 06:10:03] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:10:03] I main
[09/13/21 06:10:03] I main    ╭══════════════════════════════════ AProcess ══════════════════════════════════╮
[09/13/21 06:10:03] I main    ║ A normal process                                                             ║
[09/13/21 06:10:03] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:10:03] I main    AProcess: Workdir: '.pipen/pipen-0/aprocess'
[09/13/21 06:10:03] I main    AProcess: <<< [START]
[09/13/21 06:10:03] I main    AProcess: >>> [END]
[09/13/21 06:10:03] I verbose AProcess: size: 1
[09/13/21 06:10:03] I verbose AProcess: [0/0] in.infile: /tmp/pipen_example_caching.txt
[09/13/21 06:10:03] I verbose AProcess: [0/0] out.outfile: /home/pwwang/github/pipen/Pipen-output/AProcess/pipen_example_caching.txt
[09/13/21 06:10:03] I main    AProcess: Cached jobs: 0
[09/13/21 06:10:03] I verbose AProcess: Time elapsed: 00:00:00.040s
[09/13/21 06:10:03] I main
```

To "de-cache" the jobs:

```log
❯ PIPEN_default_cache=0 python examples/caching.py
[09/13/21 06:11:55] I main                        _____________________________________   __
[09/13/21 06:11:55] I main                        ___  __ \___  _/__  __ \__  ____/__  | / /
[09/13/21 06:11:55] I main                        __  /_/ /__  / __  /_/ /_  __/  __   |/ /
[09/13/21 06:11:55] I main                        _  ____/__/ /  _  ____/_  /___  _  /|  /
[09/13/21 06:11:55] I main                        /_/     /___/  /_/     /_____/  /_/ |_/
[09/13/21 06:11:55] I main
[09/13/21 06:11:55] I main                                     version: 0.1.0
[09/13/21 06:11:55] D main
[09/13/21 06:11:55] D main    Building process relationships:
[09/13/21 06:11:55] D main    - Start processes: [<Proc:AProcess>]
[09/13/21 06:11:55] I main
[09/13/21 06:11:55] I main    ╭══════════════════════════════════ PIPEN-0 ═══════════════════════════════════╮
[09/13/21 06:11:55] I main    ║  # procs          = 1                                                        ║
[09/13/21 06:11:55] I main    ║  plugins          = ['main', 'verbose-0.0.1']                                ║
[09/13/21 06:11:55] I main    ║  profile          = default                                                  ║
[09/13/21 06:11:55] I main    ║  outdir           = Pipen-output                                          ║
[09/13/21 06:11:55] I main    ║  cache            = 0                                                        ║
[09/13/21 06:11:55] I main    ║  dirsig           = 1                                                        ║
[09/13/21 06:11:55] I main    ║  error_strategy   = ignore                                                   ║
[09/13/21 06:11:55] I main    ║  forks            = 1                                                        ║
[09/13/21 06:11:55] I main    ║  lang             = bash                                                     ║
[09/13/21 06:11:55] I main    ║  loglevel         = debug                                                    ║
[09/13/21 06:11:55] I main    ║  num_retries      = 3                                                        ║
[09/13/21 06:11:55] I main    ║  plugin_opts      = {}                                                       ║
[09/13/21 06:11:55] I main    ║  plugins          = None                                                     ║
[09/13/21 06:11:55] I main    ║  scheduler        = local                                                    ║
[09/13/21 06:11:55] I main    ║  scheduler_opts   = {}                                                       ║
[09/13/21 06:11:55] I main    ║  submission_batch = 8                                                        ║
[09/13/21 06:11:55] I main    ║  template         = liquid                                                   ║
[09/13/21 06:11:55] I main    ║  template_opts    = {}                                                       ║
[09/13/21 06:11:55] I main    ║  workdir          = ./.pipen                                                 ║
[09/13/21 06:11:55] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:11:55] I main
[09/13/21 06:11:55] I main    ╭══════════════════════════════════ AProcess ══════════════════════════════════╮
[09/13/21 06:11:55] I main    ║ A normal process                                                             ║
[09/13/21 06:11:55] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:11:55] I main    AProcess: Workdir: '.pipen/pipen-0/aprocess'
[09/13/21 06:11:55] I main    AProcess: <<< [START]
[09/13/21 06:11:55] I main    AProcess: >>> [END]
[09/13/21 06:11:55] I verbose AProcess: size: 1
[09/13/21 06:11:55] D main    AProcess: [0/0] Not cached (proc.cache is False)
[09/13/21 06:11:55] D main    AProcess: [0/0] Clearing previous output files.
[09/13/21 06:11:55] I verbose AProcess: [0/0] in.infile: /tmp/pipen_example_caching.txt
[09/13/21 06:11:55] I verbose AProcess: [0/0] out.outfile: /home/pwwang/github/pipen/Pipen-output/AProcess/pipen_example_caching.txt
[09/13/21 06:11:56] I verbose AProcess: Time elapsed: 00:00:01.060s
[09/13/21 06:11:56] I main
```

## Input data callback

```log
❯ python examples/input_data_callback.py
[09/13/21 06:13:12] I main                        _____________________________________   __
[09/13/21 06:13:12] I main                        ___  __ \___  _/__  __ \__  ____/__  | / /
[09/13/21 06:13:12] I main                        __  /_/ /__  / __  /_/ /_  __/  __   |/ /
[09/13/21 06:13:12] I main                        _  ____/__/ /  _  ____/_  /___  _  /|  /
[09/13/21 06:13:12] I main                        /_/     /___/  /_/     /_____/  /_/ |_/
[09/13/21 06:13:12] I main
[09/13/21 06:13:12] I main                                     version: 0.1.0
[09/13/21 06:13:12] I main
[09/13/21 06:13:12] I main    ╭══════════════════════════════════ PIPEN-0 ═══════════════════════════════════╮
[09/13/21 06:13:12] I main    ║  # procs          = 2                                                        ║
[09/13/21 06:13:12] I main    ║  plugins          = ['main', 'verbose-0.0.1']                                ║
[09/13/21 06:13:12] I main    ║  profile          = default                                                  ║
[09/13/21 06:13:12] I main    ║  outdir           = Pipen-output                                             ║
[09/13/21 06:13:12] I main    ║  cache            = True                                                     ║
[09/13/21 06:13:12] I main    ║  dirsig           = 1                                                        ║
[09/13/21 06:13:12] I main    ║  error_strategy   = ignore                                                   ║
[09/13/21 06:13:13] I main    ║  forks            = 3                                                        ║
[09/13/21 06:13:13] I main    ║  lang             = bash                                                     ║
[09/13/21 06:13:13] I main    ║  loglevel         = info                                                     ║
[09/13/21 06:13:13] I main    ║  num_retries      = 3                                                        ║
[09/13/21 06:13:13] I main    ║  plugin_opts      = {}                                                       ║
[09/13/21 06:13:13] I main    ║  plugins          = None                                                     ║
[09/13/21 06:13:13] I main    ║  scheduler        = local                                                    ║
[09/13/21 06:13:13] I main    ║  scheduler_opts   = {}                                                       ║
[09/13/21 06:13:13] I main    ║  submission_batch = 8                                                        ║
[09/13/21 06:13:13] I main    ║  template         = liquid                                                   ║
[09/13/21 06:13:13] I main    ║  template_opts    = {}                                                       ║
[09/13/21 06:13:13] I main    ║  workdir          = ./.pipen                                                 ║
[09/13/21 06:13:13] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:13:13] I main
[09/13/21 06:13:13] I main    ╭───────────────────────────────────── P1 ─────────────────────────────────────╮
[09/13/21 06:13:13] I main    │ Sort input file                                                              │
[09/13/21 06:13:13] I main    ╰──────────────────────────────────────────────────────────────────────────────╯
[09/13/21 06:13:13] I main    P1: Workdir: '.pipen/pipen-0/p1'
[09/13/21 06:13:13] I main    P1: <<< [START]
[09/13/21 06:13:13] I main    P1: >>> ['P2']
[09/13/21 06:13:13] I verbose P1: size: 10
[09/13/21 06:13:13] I verbose P1: [0/9] in.infile: /tmp/pipen_example_input_data_callback/0.txt
[09/13/21 06:13:13] I verbose P1: [0/9] out.outfile: /home/pwwang/github/pipen/.pipen/pipen-0/p1/0/output/intermediate.txt
[09/13/21 06:13:15] I verbose P1: Time elapsed: 00:00:02.224s
[09/13/21 06:13:15] I main
[09/13/21 06:13:15] I main    ╭═════════════════════════════════════ P2 ═════════════════════════════════════╮
[09/13/21 06:13:15] I main    ║ Paste line number                                                            ║
[09/13/21 06:13:15] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:13:15] I main    P2: Workdir: '.pipen/pipen-0/p2'
[09/13/21 06:13:15] I main    P2: <<< ['P1']
[09/13/21 06:13:15] I main    P2: >>> [END]
[09/13/21 06:13:15] I verbose P2: size: 10
[09/13/21 06:13:15] I verbose P2: [0/9] in.infile: /home/pwwang/github/pipen/.pipen/pipen-0/p1/0/output/intermediate.txt
[09/13/21 06:13:15] I verbose P2: [0/9] in.nlines: 2
[09/13/21 06:13:15] I verbose P2: [0/9] out.outfile: /home/pwwang/github/pipen/Pipen-output/P2/0/result.txt
[09/13/21 06:13:17] I verbose P2: Time elapsed: 00:00:02.192s
[09/13/21 06:13:17] I main
```

```shell
❯ cat /home/pwwang/github/pipen/Pipen-output/P2/0/result.txt
1       0_0
2       0_1
```

## mako templating

```log
❯ python examples/mako-templating.py
[09/13/21 06:14:57] I main                        _____________________________________   __
[09/13/21 06:14:57] I main                        ___  __ \___  _/__  __ \__  ____/__  | / /
[09/13/21 06:14:57] I main                        __  /_/ /__  / __  /_/ /_  __/  __   |/ /
[09/13/21 06:14:57] I main                        _  ____/__/ /  _  ____/_  /___  _  /|  /
[09/13/21 06:14:57] I main                        /_/     /___/  /_/     /_____/  /_/ |_/
[09/13/21 06:14:57] I main
[09/13/21 06:14:57] I main                                     version: 0.1.0
[09/13/21 06:14:57] I main
[09/13/21 06:14:57] I main    ╭══════════════════════════════════ PIPEN-0 ═══════════════════════════════════╮
[09/13/21 06:14:57] I main    ║  # procs          = 1                                                        ║
[09/13/21 06:14:57] I main    ║  plugins          = ['main', 'verbose-0.0.1']                                ║
[09/13/21 06:14:57] I main    ║  profile          = default                                                  ║
[09/13/21 06:14:57] I main    ║  outdir           = Pipen-output                                             ║
[09/13/21 06:14:57] I main    ║  cache            = True                                                     ║
[09/13/21 06:14:57] I main    ║  dirsig           = 1                                                        ║
[09/13/21 06:14:57] I main    ║  error_strategy   = ignore                                                   ║
[09/13/21 06:14:57] I main    ║  forks            = 1                                                        ║
[09/13/21 06:14:57] I main    ║  lang             = bash                                                     ║
[09/13/21 06:14:57] I main    ║  loglevel         = info                                                     ║
[09/13/21 06:14:57] I main    ║  num_retries      = 3                                                        ║
[09/13/21 06:14:57] I main    ║  plugin_opts      = {}                                                       ║
[09/13/21 06:14:57] I main    ║  plugins          = None                                                     ║
[09/13/21 06:14:57] I main    ║  scheduler        = local                                                    ║
[09/13/21 06:14:57] I main    ║  scheduler_opts   = {}                                                       ║
[09/13/21 06:14:57] I main    ║  submission_batch = 8                                                        ║
[09/13/21 06:14:57] I main    ║  template         = liquid                                                   ║
[09/13/21 06:14:57] I main    ║  template_opts    = {}                                                       ║
[09/13/21 06:14:57] I main    ║  workdir          = ./.pipen                                                 ║
[09/13/21 06:14:57] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:14:57] I main
[09/13/21 06:14:57] I main    ╭════════════════════════════════ MakoProcess ═════════════════════════════════╮
[09/13/21 06:14:57] I main    ║ A process using mako templating                                              ║
[09/13/21 06:14:57] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:14:57] I main    MakoProcess: Workdir: '.pipen/pipen-0/makoprocess'
[09/13/21 06:14:57] I main    MakoProcess: <<< [START]
[09/13/21 06:14:57] I main    MakoProcess: >>> [END]
[09/13/21 06:14:57] I verbose MakoProcess: size    : 1
[09/13/21 06:14:57] I verbose MakoProcess: template: mako
[09/13/21 06:14:57] I verbose MakoProcess: [0/0] in.a: 1
[09/13/21 06:14:57] I verbose MakoProcess: [0/0] out.outfile: /home/pwwang/github/pipen/Pipen-output/MakoProcess/1.txt
[09/13/21 06:14:58] I verbose MakoProcess: Time elapsed: 00:00:01.019s
[09/13/21 06:14:58] I main
```

## multile jobs

```log
> python examples/multijobs.py
[09/13/21 06:16:09] I main                        _____________________________________   __
[09/13/21 06:16:09] I main                        ___  __ \___  _/__  __ \__  ____/__  | / /
[09/13/21 06:16:09] I main                        __  /_/ /__  / __  /_/ /_  __/  __   |/ /
[09/13/21 06:16:09] I main                        _  ____/__/ /  _  ____/_  /___  _  /|  /
[09/13/21 06:16:09] I main                        /_/     /___/  /_/     /_____/  /_/ |_/
[09/13/21 06:16:09] I main
[09/13/21 06:16:09] I main                                     version: 0.1.0
[09/13/21 06:16:09] I main
[09/13/21 06:16:09] I main    ╭══════════════════════════════════ PIPEN-0 ═══════════════════════════════════╮
[09/13/21 06:16:09] I main    ║  # procs          = 1                                                        ║
[09/13/21 06:16:09] I main    ║  plugins          = ['main', 'verbose-0.0.1']                                ║
[09/13/21 06:16:09] I main    ║  profile          = default                                                  ║
[09/13/21 06:16:09] I main    ║  outdir           = Pipen-output                                             ║
[09/13/21 06:16:09] I main    ║  cache            = True                                                     ║
[09/13/21 06:16:09] I main    ║  dirsig           = 1                                                        ║
[09/13/21 06:16:09] I main    ║  error_strategy   = ignore                                                   ║
[09/13/21 06:16:09] I main    ║  forks            = 1                                                        ║
[09/13/21 06:16:09] I main    ║  lang             = bash                                                     ║
[09/13/21 06:16:09] I main    ║  loglevel         = info                                                     ║
[09/13/21 06:16:09] I main    ║  num_retries      = 3                                                        ║
[09/13/21 06:16:09] I main    ║  plugin_opts      = {}                                                       ║
[09/13/21 06:16:09] I main    ║  plugins          = None                                                     ║
[09/13/21 06:16:09] I main    ║  scheduler        = local                                                    ║
[09/13/21 06:16:09] I main    ║  scheduler_opts   = {}                                                       ║
[09/13/21 06:16:09] I main    ║  submission_batch = 8                                                        ║
[09/13/21 06:16:09] I main    ║  template         = liquid                                                   ║
[09/13/21 06:16:09] I main    ║  template_opts    = {}                                                       ║
[09/13/21 06:16:09] I main    ║  workdir          = ./.pipen                                                 ║
[09/13/21 06:16:09] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:16:09] I main
[09/13/21 06:16:09] I main    ╭════════════════════════════════ MultiJobProc ════════════════════════════════╮
[09/13/21 06:16:09] I main    ║ A process with multiple jobs                                                 ║
[09/13/21 06:16:09] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:16:09] I main    MultiJobProc: Workdir: '.pipen/pipen-0/multijobproc'
[09/13/21 06:16:09] I main    MultiJobProc: <<< [START]
[09/13/21 06:16:09] I main    MultiJobProc: >>> [END]
[09/13/21 06:16:10] I verbose MultiJobProc: forks: 3
[09/13/21 06:16:10] I verbose MultiJobProc: cache: False
[09/13/21 06:16:10] I verbose MultiJobProc: size : 10
[09/13/21 06:16:10] I verbose MultiJobProc: [0/9] in.i: 0
[09/13/21 06:16:10] I verbose MultiJobProc: [0/9] out.outfile: /home/pwwang/github/pipen/Pipen-output/MultiJobProc/0/0.txt
[09/13/21 06:16:16] I verbose MultiJobProc: Time elapsed: 00:00:06.139s
[09/13/21 06:16:16] I main
```

## plugin

```log
❯ python examples/plugin-example.py
[09/13/21 06:18:18] I notify  Calling on_setup
[09/13/21 06:18:18] I main                        _____________________________________   __
[09/13/21 06:18:18] I main                        ___  __ \___  _/__  __ \__  ____/__  | / /
[09/13/21 06:18:18] I main                        __  /_/ /__  / __  /_/ /_  __/  __   |/ /
[09/13/21 06:18:18] I main                        _  ____/__/ /  _  ____/_  /___  _  /|  /
[09/13/21 06:18:18] I main                        /_/     /___/  /_/     /_____/  /_/ |_/
[09/13/21 06:18:18] I main
[09/13/21 06:18:18] I main                                     version: 0.1.0
[09/13/21 06:18:18] I main
[09/13/21 06:18:18] I main    ╭══════════════════════════════════ PIPEN-0 ═══════════════════════════════════╮
[09/13/21 06:18:18] I main    ║  # procs          = 1                                                        ║
[09/13/21 06:18:18] I main    ║  plugins          = ['main', 'notifyplugin-0.0.0']                           ║
[09/13/21 06:18:18] I main    ║  profile          = default                                                  ║
[09/13/21 06:18:18] I main    ║  outdir           = Pipen-output                                             ║
[09/13/21 06:18:18] I main    ║  cache            = True                                                     ║
[09/13/21 06:18:18] I main    ║  dirsig           = 1                                                        ║
[09/13/21 06:18:18] I main    ║  error_strategy   = ignore                                                   ║
[09/13/21 06:18:18] I main    ║  forks            = 1                                                        ║
[09/13/21 06:18:18] I main    ║  lang             = bash                                                     ║
[09/13/21 06:18:18] I main    ║  loglevel         = info                                                     ║
[09/13/21 06:18:18] I main    ║  num_retries      = 3                                                        ║
[09/13/21 06:18:18] I main    ║  plugin_opts      = {}                                                       ║
[09/13/21 06:18:18] I main    ║  plugins          = [<class '__main__.NotifyPlugin'>]                        ║
[09/13/21 06:18:18] I main    ║  scheduler        = local                                                    ║
[09/13/21 06:18:18] I main    ║  scheduler_opts   = {}                                                       ║
[09/13/21 06:18:18] I main    ║  submission_batch = 8                                                        ║
[09/13/21 06:18:18] I main    ║  template         = liquid                                                   ║
[09/13/21 06:18:18] I main    ║  template_opts    = {}                                                       ║
[09/13/21 06:18:18] I main    ║  workdir          = ./.pipen                                                 ║
[09/13/21 06:18:18] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:18:18] I notify  Calling on_start
[09/13/21 06:18:18] I main
[09/13/21 06:18:18] I main    ╭══════════════════════════════════ AProcess ══════════════════════════════════╮
[09/13/21 06:18:18] I main    ║ Undescribed                                                                  ║
[09/13/21 06:18:18] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:18:18] I main    AProcess: Workdir: '.pipen/pipen-0/aprocess'
[09/13/21 06:18:18] I main    AProcess: <<< [START]
[09/13/21 06:18:18] I main    AProcess: >>> [END]
[09/13/21 06:18:18] W main    AProcess: No script specified.
[09/13/21 06:18:18] I notify  Calling on_proc_start
[09/13/21 06:18:18] I main    AProcess: Cached jobs: 0
[09/13/21 06:18:18] I notify  Calling on_proc_done, succeeded = cached
[09/13/21 06:18:18] I main

                PIPEN-0: 100%|█████████████████████████████████████████████████| 1/1 [00:00<00:00, 2.91 procs/s]
[09/13/21 06:18:18] I notify  Calling on_complete, succeeded = True
```

## Using python interpreter

```log
❯ python examples/python-script.py
[09/13/21 06:19:45] I main                        _____________________________________   __
[09/13/21 06:19:45] I main                        ___  __ \___  _/__  __ \__  ____/__  | / /
[09/13/21 06:19:45] I main                        __  /_/ /__  / __  /_/ /_  __/  __   |/ /
[09/13/21 06:19:45] I main                        _  ____/__/ /  _  ____/_  /___  _  /|  /
[09/13/21 06:19:45] I main                        /_/     /___/  /_/     /_____/  /_/ |_/
[09/13/21 06:19:45] I main
[09/13/21 06:19:45] I main                                     version: 0.1.0
[09/13/21 06:19:45] I main
[09/13/21 06:19:45] I main    ╭══════════════════════════════════ PIPEN-0 ═══════════════════════════════════╮
[09/13/21 06:19:45] I main    ║  # procs          = 1                                                        ║
[09/13/21 06:19:45] I main    ║  plugins          = ['main', 'verbose-0.0.1']                                ║
[09/13/21 06:19:45] I main    ║  profile          = default                                                  ║
[09/13/21 06:19:45] I main    ║  outdir           = Pipen-output                                             ║
[09/13/21 06:19:46] I main    ║  cache            = True                                                     ║
[09/13/21 06:19:46] I main    ║  dirsig           = 1                                                        ║
[09/13/21 06:19:46] I main    ║  error_strategy   = ignore                                                   ║
[09/13/21 06:19:46] I main    ║  forks            = 1                                                        ║
[09/13/21 06:19:46] I main    ║  lang             = bash                                                     ║
[09/13/21 06:19:46] I main    ║  loglevel         = info                                                     ║
[09/13/21 06:19:46] I main    ║  num_retries      = 3                                                        ║
[09/13/21 06:19:46] I main    ║  plugin_opts      = {}                                                       ║
[09/13/21 06:19:46] I main    ║  plugins          = None                                                     ║
[09/13/21 06:19:46] I main    ║  scheduler        = local                                                    ║
[09/13/21 06:19:46] I main    ║  scheduler_opts   = {}                                                       ║
[09/13/21 06:19:46] I main    ║  submission_batch = 8                                                        ║
[09/13/21 06:19:46] I main    ║  template         = liquid                                                   ║
[09/13/21 06:19:46] I main    ║  template_opts    = {}                                                       ║
[09/13/21 06:19:46] I main    ║  workdir          = ./.pipen                                                 ║
[09/13/21 06:19:46] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:19:46] I main
[09/13/21 06:19:46] I main    ╭══════════════════════════════ PythonScriptProc ══════════════════════════════╮
[09/13/21 06:19:46] I main    ║ A process using python interpreter for script                                ║
[09/13/21 06:19:46] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:19:46] I main    PythonScriptProc: Workdir: '.pipen/pipen-0/pythonscriptproc'
[09/13/21 06:19:46] I main    PythonScriptProc: <<< [START]
[09/13/21 06:19:46] I main    PythonScriptProc: >>> [END]
[09/13/21 06:19:46] I verbose PythonScriptProc: lang: python
[09/13/21 06:19:46] I verbose PythonScriptProc: size: 1
[09/13/21 06:19:46] I verbose PythonScriptProc: [0/0] in.a: 1
[09/13/21 06:19:46] I verbose PythonScriptProc: [0/0] out.outfile:
                      /home/pwwang/github/pipen/Pipen-output/PythonScriptProc/1.txt
[09/13/21 06:19:48] I verbose PythonScriptProc: Time elapsed: 00:00:02.031s
[09/13/21 06:19:48] I main
```

## Error-handling: retry

```log
❯ python examples/retry.py
[09/13/21 06:20:38] I main                        _____________________________________   __
[09/13/21 06:20:38] I main                        ___  __ \___  _/__  __ \__  ____/__  | / /
[09/13/21 06:20:38] I main                        __  /_/ /__  / __  /_/ /_  __/  __   |/ /
[09/13/21 06:20:38] I main                        _  ____/__/ /  _  ____/_  /___  _  /|  /
[09/13/21 06:20:38] I main                        /_/     /___/  /_/     /_____/  /_/ |_/
[09/13/21 06:20:38] I main
[09/13/21 06:20:38] I main                                     version: 0.1.0
[09/13/21 06:20:38] D main
[09/13/21 06:20:38] D main    Building process relationships:
[09/13/21 06:20:38] D main    - Start processes: [<Proc:RetryProc>]
[09/13/21 06:20:38] I main
[09/13/21 06:20:38] I main    ╭══════════════════════════════════ PIPEN-0 ═══════════════════════════════════╮
[09/13/21 06:20:38] I main    ║  # procs          = 1                                                        ║
[09/13/21 06:20:38] I main    ║  plugins          = ['main', 'verbose-0.0.1']                                ║
[09/13/21 06:20:38] I main    ║  profile          = default                                                  ║
[09/13/21 06:20:38] I main    ║  outdir           = Pipen-output                                             ║
[09/13/21 06:20:38] I main    ║  cache            = True                                                     ║
[09/13/21 06:20:38] I main    ║  dirsig           = 1                                                        ║
[09/13/21 06:20:38] I main    ║  error_strategy   = ignore                                                   ║
[09/13/21 06:20:38] I main    ║  forks            = 1                                                        ║
[09/13/21 06:20:38] I main    ║  lang             = bash                                                     ║
[09/13/21 06:20:38] I main    ║  loglevel         = debug                                                    ║
[09/13/21 06:20:38] I main    ║  num_retries      = 3                                                        ║
[09/13/21 06:20:38] I main    ║  plugin_opts      = {}                                                       ║
[09/13/21 06:20:38] I main    ║  plugins          = None                                                     ║
[09/13/21 06:20:38] I main    ║  scheduler        = local                                                    ║
[09/13/21 06:20:38] I main    ║  scheduler_opts   = {}                                                       ║
[09/13/21 06:20:38] I main    ║  submission_batch = 8                                                        ║
[09/13/21 06:20:38] I main    ║  template         = liquid                                                   ║
[09/13/21 06:20:38] I main    ║  template_opts    = {}                                                       ║
[09/13/21 06:20:38] I main    ║  workdir          = ./.pipen                                                 ║
[09/13/21 06:20:38] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:20:38] I main
[09/13/21 06:20:38] I main    ╭═════════════════════════════════ RetryProc ══════════════════════════════════╮
[09/13/21 06:20:38] I main    ║ Retry the jobs when fail                                                     ║
[09/13/21 06:20:38] I main    ╰══════════════════════════════════════════════════════════════════════════════╯
[09/13/21 06:20:38] I main    RetryProc: Workdir: '.pipen/pipen-0/retryproc'
[09/13/21 06:20:38] I main    RetryProc: <<< [START]
[09/13/21 06:20:38] I main    RetryProc: >>> [END]
[09/13/21 06:20:38] I verbose RetryProc: size: 1
[09/13/21 06:20:38] D main    RetryProc: [0/0] Not cached (job.rc != 0)
[09/13/21 06:20:38] D main    RetryProc: [0/0] Clearing previous output files.
[09/13/21 06:20:38] I verbose RetryProc: [0/0] in.starttime: 1631539238
[09/13/21 06:20:39] D main    RetryProc: [0/0] Retrying #1
[09/13/21 06:20:40] D main    RetryProc: [0/0] Retrying #2
[09/13/21 06:20:41] D main    RetryProc: [0/0] Retrying #3
[09/13/21 06:20:42] D main    RetryProc: [0/0] Retrying #4
[09/13/21 06:20:43] I verbose RetryProc: Time elapsed: 00:00:05.203s
[09/13/21 06:20:43] I main
```
