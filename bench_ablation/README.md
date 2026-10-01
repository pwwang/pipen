# `bench_ablation/` — the scheduler wait ablation

This directory explains the one place where pipen is slower than the comparison engine, by
measuring it rather than arguing about it. It backs Supplementary Table S2 and the throughput
paragraph of the Application Note.

**Read first:** `RESULTS_ABLATION.md` — the arms, the timed matrix, the correctness matrix, the
await site census and the CPU probe.

## What was tested

The local scheduler of pipen 1.2.4 wraps each job in two waits of one second, which exist to keep
job status synchronisation correct. The ablation modifies the shipped constants one at a time, in
arms A to F, and measures wall time, marginal cost per job, job start rate, whether the output is
correct, whether every job reports FINISHED, and whether any job is falsely reported as FAILED.

| Arm | What it changes |
|---|---|
| `A` | baseline, the shipped values |
| `B` | the submission sleep, 0.1 s to 0.001 s |
| `C_pf_poll` | the producer and consumer polling intervals |
| others through `F` | the remaining await sites, and one combination |

## What it found

- **The submission sleep is a null result.** Arm B moved N=500 wall time from 55.896 s to 56.118 s
  and the marginal cost from 0.1102 s to 0.1107 s per job, with a census proving all nine submit
  loop awaits had been patched. Lowering that interval does not buy speed, and this is stated in
  the paper rather than left out.
- **Polling is where the cost is.** `C_pf_poll` takes 55.896 s to 38.310 s at N=500, and the
  marginal cost from 0.1102 s to 0.0751 s per job: **36.1 % of the gap with Snakemake is closed**,
  with byte identical output.
- **Arm F is disqualified, and the reason is in the paper.** Removing the waits entirely recovers
  more, but 99 to 100 of 100 jobs are then falsely marked FAILED with `rc = -3`, the aggregation
  job is never submitted, and the pipeline still exits 0. That is a correctness failure, not a
  speed up, so the number is not available for the comparison.
- **Polling faster is not free.** The CPU probe records the cost of a 1 ms polling interval, which
  roughly doubles per job CPU.

## Files

| File | Role |
|---|---|
| `abl_dag.py`, `driver_ablation.py` | the ablation DAG and its driver |
| `derived_ablation.json` (in `raw/`) | the machine computed numbers: `summary` per arm and N, `gap_closed_fraction_overhead_per_job`, `marginal_per_job_sec_from_N100_to_N500`, `cpu_probe` |
| `verify_records*.json` (in `raw/`) | the await site census and the job status census that prove what was patched |
| `emit_results_ablation.py`, `make_report_ablation.py` | produce `RESULTS_ABLATION.md` from the records |
| `cpu_probe.sh`, `probe_*.sh`, `diag_F*.sh`, `inventory.sh` | the individual probes, kept so any single claim can be re-run |
| `croscheck_counts.sh` | cross check of the job counts |

## Caveat that matters when quoting

The per job marginal cost of this ablation's baseline arm is **0.1102 s**, measured with the
ablation harness. The paper's head to head figure against Snakemake quotes **0.1085 s** per job,
which comes from `../bench/raw/derived_numbers.json` (the scaling arm of the main harness). The two
are different measurements of a similar quantity and must not be mixed inside one sentence.
