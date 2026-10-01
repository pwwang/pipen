# pipen — benchmark evidence, harness and reproduction scripts

This branch is the **frozen evidence pack** for the *Bioinformatics* (OUP) Application Note
"pipen: an AI friendly Python native pipeline framework with signature based job caching and
scheduler agnostic execution". Every measured number in the note, and in its Supplementary
Tables S1–S3, is computed from the files here and from nothing else. Nothing was re-measured,
re-typed or extrapolated when the pack was assembled.

The paths named in the supplement's *source* column are relative to this branch root, e.g.
`bench/raw/derived_numbers.json`, `bench_ablation/raw/derived_ablation.json`,
`bench/raw/touch_test.json`.

| Directory | What it holds | What it backs |
|---|---|---|
| `bench/` | The harness: both DAG definitions (`bench_pipen_dag.py`, `bench_cache_dag.py`), their Snakemake equivalents (`smk_dag/Snakefile`, `smk_cache/Snakefile`), the drivers, the analysis chain, `RESULTS.md` and the frozen `raw/` records (per-run JSON, full stdout logs of every pipen and Snakemake run, per-job marker logs) | the paper's Results section and Supplementary Table S1 |
| `bench_ablation/` | The scheduler-wait ablation: arms A–F, the timed matrix, the correctness matrix, the await-site census, `RESULTS_ABLATION.md` and its `raw/` records | Supplementary Table S2, and the throughput paragraph |
| `bench_portability/` | The portability work: `PORTABILITY.md`, the pristine copies of the harness files it modified, and a reduced-size clean-environment replay (`out_clean_run/`, `out_archive_replay/`) | the reproduction path: it shows the harness runs on a different machine and at reduced size |
| `ai_demo/` | The agent-surface evidence: `RESULTS_AI.md` plus the raw CLI and MCP captures | the "surface seen by agents" paragraph and the AI-friendly claim |

Each of those four directories carries its own `README.md` saying what it holds, what it backs and
what to read first; this file is the index to them.

## Reproduction

```bash
bash bench/setup_env.sh                 # creates the two virtualenvs, writes bench.local.env locally
bash bench/run_all.sh /tmp/bench-out    # the whole table in one command
```

The harness is self-locating: paths and protocol sizes come from `bench/bench.env`, overridable
per run with `BENCH_<KEY>=...`. `bench/bench.local.env` is deliberately **not** part of this
branch (it records the author's virtualenv locations); `setup_env.sh` recreates it.

The vintage chain that actually produced raw/ ships alongside (`setup.sh`, `verify.sh`,
`driver_pipen.py`, `driver_smk.py`, `touch_test2.py`, `analyse_all.py`, `make_report.py`,
the `run_*.sh` wrappers), so the archived numbers stay reproducible with the scripts that made
them.

## Machine, and known deviations

The timings come from a WSL2 Ubuntu 24.04 box on Windows 11: 32 logical CPUs (13th Gen Intel
Core i9-13900), 47 GiB RAM, workdir on ext4 (no 9p/Windows filesystem in any timing). Full
inventory in `bench/raw/environment.json` and `bench/raw/env_raw.txt`. The runs ran under a
recorded background load (loadavg 4.4–7.0), stated in `bench/RESULTS.md`.

- The frozen `raw/` trees are byte-for-byte as produced, and **were not rewritten**: their log
  and JSON text still contains the author's absolute paths and WSL home paths. That text is the
  evidence. Scripts are likewise deposited as they ran.
- `bench.local.env` is not deposited; the two virtualenvs are recreated by `setup_env.sh`.
- Versions must match to reproduce timings; see `bench/raw/environment.json` (pipen 1.2.3/1.2.4,
  Python 3.12.2, Snakemake 9.27.0, xqute 2.2.0).

## Integrity

`MANIFEST.txt` lists every file with its size and SHA-256 — 545 files, 4819352 bytes.

## Licence

MIT, the same licence as pipen (see `LICENSE`).
