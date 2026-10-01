#!/usr/bin/env python3
"""Build RESULTS_ABLATION.md from the raw JSON/logs the driver produced.

Every number in the generated markdown is read from a raw record (per-run JSON
or parsed-from-log field) -- nothing is typed by hand.  Run inside WSL:

  ~/bench/.venv/bin/python /mnt/f/E/hermes-workspace/pipen/bench_ablation/make_report_ablation.py
"""
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path("/mnt/f/E/hermes-workspace/pipen/bench_ablation")
RAW = HERE / "raw"
OUT_MD = HERE / "RESULTS_ABLATION.md"

# Snakemake reference points: taken verbatim from the *existing* benchmark on
# this same machine (bench/RESULTS.md §3, 3 reps, --cores 32, same DAG).
SMK = {100: {"wall_median": 2.898, "wall_min": 2.849, "wall_max": 2.899,
             "overhead_per_job_median": 0.0274},
       500: {"wall_median": 7.284, "wall_min": 7.189, "wall_max": 7.441,
             "overhead_per_job_median": 0.0130}}


def load_records():
    recs = []
    for f in sorted(RAW.glob("time_records_*.json")):
        d = json.loads(f.read_text())
        recs.extend(d["records"])
    return recs


def stat(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {"n": len(vals), "median": statistics.median(vals),
            "min": min(vals), "max": max(vals)}


def main():
    recs = load_records()
    verify = json.loads((RAW / "verify_records.json").read_text())
    vrecs = {r["arm"]: r for r in verify["records"]}

    by = defaultdict(list)
    for r in recs:
        by[(r["arm"], r["n"])].append(r)

    keys = sorted(by, key=lambda k: (k[1], k[0]))
    summary = {}
    for k in keys:
        rs = by[k]
        summary[k] = {
            "n_reps": len(rs),
            "wall_sec": stat([r["wall_sec"] for r in rs]),
            "pipeline_run_sec": stat([r["pipeline_run_sec"] for r in rs]),
            "overhead_wall_per_job_sec": stat([r["overhead_wall_per_job_sec"] for r in rs]),
            "overhead_run_per_job_sec": stat([r["overhead_run_per_job_sec"] for r in rs]),
            "job_start_rate_per_sec_span": stat([r["job_start_rate_per_sec_span"] for r in rs]),
            "end_to_end_rate_per_sec": stat([r["end_to_end_rate_per_sec"] for r in rs]),
            "peak_concurrent_jobs_from_markers": stat(
                [r["peak_concurrent_jobs_from_markers"] for r in rs]),
            "mean_concurrent_jobs_from_markers": stat(
                [r["mean_concurrent_jobs_from_markers"] for r in rs]),
            "shard_jobs_started": [r["shard_jobs_started"] for r in rs],
            "shard_jobs_expected": rs[0]["n"],
            "agg_jobs_started": [r["agg_jobs"] for r in rs],
            "rc": [r["rc"] for r in rs],
            "agg_content_correct": [r["correctness"]["agg_content_equals_expected_0_to_N_minus_1"]
                                    for r in rs],
            "all_jobs_finished": [r["correctness"]["all_jobs_finished"] for r in rs],
            "false_fail_counts": [r["correctness"]["n_jobs_marked_failed_before_running"]
                                  for r in rs],
            "job_status_histograms": [r["correctness"]["job_status_histogram"] for r in rs],
            "effective_declared": sorted({
                json.dumps(r["effective"]["effective"], sort_keys=True) for r in rs
                if r["effective"]}),
            "loadavg": [[r["loadavg_before"], r["loadavg_after"]] for r in rs],
            "tags": [r["tag"] for r in rs],
            "logs": [r["log"] for r in rs],
            "markers": [r["marker_log"] for r in rs],
        }

    derived = {"summary": {f"{k[0]}|N={k[1]}": v for k, v in summary.items()},
               "snakemake_reference_from_bench_RESULTS_md": SMK}

    # ---- ratios vs baseline A at the same N, and the marginal per-job cost
    ratios = {}
    for (arm, n) in summary:
        base = summary.get(("A", n))
        if base and base["wall_sec"] and summary[(arm, n)]["wall_sec"]:
            ratios[f"{arm}|N={n}"] = {
                "wall_ratio_vs_A": round(summary[(arm, n)]["wall_sec"]["median"]
                                         / base["wall_sec"]["median"], 3),
                "overhead_per_job_ratio_vs_A": round(
                    summary[(arm, n)]["overhead_wall_per_job_sec"]["median"]
                    / base["overhead_wall_per_job_sec"]["median"], 3),
            }
    derived["ratios_vs_baseline_A"] = ratios

    for arm in {k[0] for k in summary}:
        a100, a500 = summary.get((arm, 100)), summary.get((arm, 500))
        if a100 and a500 and a100["wall_sec"] and a500["wall_sec"]:
            derived.setdefault("marginal_per_job_sec_from_N100_to_N500", {})[arm] = (
                round((a500["wall_sec"]["median"] - a100["wall_sec"]["median"]) / 400, 5))

    (RAW / "derived_ablation.json").write_text(json.dumps(derived, indent=2))
    print(json.dumps({"summary_keys": [f"{k[0]}|N={k[1]}" for k in keys],
                      "marginal_per_job_sec": derived.get("marginal_per_job_sec_from_N100_to_N500"),
                      "ratios": ratios}, indent=2))


if __name__ == "__main__":
    main()
