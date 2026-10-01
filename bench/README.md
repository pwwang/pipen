# `bench/` — the benchmark harness and the frozen measurements

This directory holds the harness that produced every measured number in the pipen Application
Note, the two DAG definitions it ran, and the raw records of the runs themselves.

**Read first:** `RESULTS.md` — the full measured write-up (sections 1 to 7 plus caveats and an
artefact map). It is the narrative behind the paper's Results section and Supplementary Table S1.

## The DAGs

| File | What it defines |
|---|---|
| `bench_pipen_dag.py` | pipen DAG: N independent shard jobs feeding one aggregation job. Parameterised by `BENCH_N`, `BENCH_SLEEP`, `BENCH_FORKS`, `BENCH_CACHE`, `BENCH_MARKER` |
| `bench_cache_dag.py` | pipen caching DAG: `Read(N) -> Mid(N)/Side(N) -> Agg(1)`, with switchable input and script variants so one change can be made at a time |
| `smk_dag/Snakefile` | the Snakemake equivalent of `bench_pipen_dag.py`: same DAG, same metrics, same marker protocol |
| `smk_cache/Snakefile` | the Snakemake equivalent of `bench_cache_dag.py` |

Each job writes a start and end marker, so the number of jobs that actually ran is read from the
markers rather than from the engine's own reporting. A cached job appears as an absent marker.

## Running it

```bash
bash setup_env.sh                 # creates the two virtualenvs; writes bench.local.env locally
bash run_all.sh /tmp/bench-out    # the whole table in one command
```

The harness is self-locating. Paths and protocol sizes come from `bench.env` (machine independent),
overridable per run with `BENCH_<KEY>=...` environment variables or a command line argument.
`bench.local.env` records this machine's virtualenv paths and is deliberately **not** part of the
deposit; `setup_env.sh` recreates it. `bench_config.py` prints the fully resolved configuration,
which is the first thing `run_all.sh` logs.

A reduced size run (minutes rather than the full 32 core timings) is documented in the sibling
`../bench_portability/` directory.

## The supporting files

| Group | Files | Role |
|---|---|---|
| Drivers | `driver_pipen.py`, `driver_smk.py`, `bench_common.py` | wall time, process tree RSS sampled from `/proc`, marker counting |
| Analysis chain | `analyse_all.py`, `evidence.py`, `make_report.py` | raw records to `summary.json` to `raw/derived_numbers.json`, which is the machine computed source of every ratio quoted in `RESULTS.md` |
| Concurrency and caching probes | `analyse_marker.py`, `touch_test2.py` | observed concurrency from job timestamps; the controlled `touch` versus content edit experiment |
| Vintage command lines | `setup.sh`, `verify.sh`, `calibrate.sh`, `install_smk.sh`, `run_*.sh`, `smk_smoke.sh`, `inspect_*.sh`, `debug_*.sh`, `package*.sh` | the exact invocations that produced the measurements, in the order given at the end of `RESULTS.md` |
| runinfo support | `ensure_runinfo.py`, `check_runinfo.py`, `preflight.py`, `summarise_run.py` | per job environment provenance, preflight checks, closing summary |

## `raw/` — the evidence, byte for byte

Frozen output of the archived runs: per run JSON records, the full stdout logs of every pipen and
Snakemake run (`logs_pipen/`, `logs_smk/`), the per job marker logs, `summary.json`, and
`derived_numbers.json`. Also `environment.json` and `env_raw.txt`, which record machine, kernel,
CPU, memory, disk, Python, the pipen git commit and dependency versions.

This tree is **not** rewritten: its log and JSON text still contains the author's absolute paths,
because that text is the evidence. Timings are only reproducible with the versions named in
`environment.json` (Python 3.12.2, Snakemake 9.27.0, xqute 2.2.0).

The headline numbers this directory backs: caching on a 301 job pipeline ran 301 jobs in 40.3 s
cold and 0 jobs in 3.1 s on re-run (12.97 times faster), and on the 500 job DAG pipen took 55.0 s
against Snakemake's 7.3 s, with the cause traced in `../bench_ablation/`.
