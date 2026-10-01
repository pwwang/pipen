# `bench_portability/` — running the harness on a different machine

This directory exists so a reader who does not have the author's machine can still run the
benchmark. It documents what in the harness assumed the original box, what was changed to remove
those assumptions, and the result of replaying the harness from the archived materials on a clean
environment at a different path.

**Read first:** `PORTABILITY.md` — the inventory of machine assumptions, the changes, and the
results of both replays.

## What is here

| Path | What it is |
|---|---|
| `PORTABILITY.md` | the full write up: assumptions found, what was changed, what was verified |
| `evidence/inventory_before.txt` | the raw grep evidence of the state before the changes (every machine specific line found) |
| `orig/` | pristine copies of the six harness files that were modified, so the before and after can be diffed |
| `out_clean_run/` | a replay on a clean virtualenv at a different path, at reduced sizes |
| `out_archive_replay/` | a replay that re-arms the archived run: **25 of 25 numbers identical** to the archive, including the 12.97 times caching figure and the 7.56 times throughput ratio |
| `run_cleanenv_reduced.sh` | the reduced size replay, as run |
| `run_archive_replay.sh` | the archive replay, as run |
| `run_runinfo_ab.sh` | A and B comparison for the per job environment provenance |
| `run_logs/` | the console logs of those runs |

## What the replay did and did not reproduce

The published numbers come from the earlier full size run and were **not** reproduced here. The
portability work was verified with a reduced size run (N=20 scaling, N=20 concurrency at two fork
levels, N=8 caching scope, N=20 cold and warm caching, one repetition) on a clean virtualenv at a
different path. Every reduced run observation is labelled as such in `PORTABILITY.md`, and the
frozen records in `../bench/raw/` were not modified by this work.

## Reading the two outputs

- `out_clean_run/` answers "does the harness run elsewhere, and does it still produce coherent
  numbers?" Its `summary.json`, `derived_numbers.json`, `environment.json` and `integrity_check.json`
  are the evidence.
- `out_archive_replay/` answers a sharper question: given the archived raw materials, does the
  analysis chain reproduce the archived derived numbers exactly? 25 of 25 identical means the
  numbers in the paper come from the records in the way the code says they do.

The `integrity_check.json` files record the marker counts, which is how the replay proves the right
number of jobs ran rather than merely that the pipeline exited successfully.
