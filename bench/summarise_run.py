#!/usr/bin/env python3
"""Closing summary of a run_all.sh run: artefacts, key medians, missing inputs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_config import load  # noqa: E402

cfg = load()
out = cfg.path("out_root")
print(f"# artefacts in {out}")
for p in sorted(out.iterdir()):
    if p.is_dir():
        n = sum(1 for _ in p.rglob("*"))
        print(f"  {p.name}/   ({n} files)")
    else:
        print(f"  {p.name}   ({p.stat().st_size} bytes)")
print()

try:
    d = json.loads((out / "derived_numbers.json").read_text())
except Exception as exc:
    print(f"# derived_numbers.json not readable ({exc}) - did make_report.py run?")
    sys.exit(0)

print("# scaling arms (median wall seconds per N, cache off)")
for a, b in zip(d.get("pipen_scaling") or [], d.get("smk_scaling") or []):
    ratio = a["wall_median"] / b["wall_median"] if b["wall_median"] else float("nan")
    print(f"  N={a['n']:>4}  pipen={a['wall_median']:>9.3f}s  snakemake={b['wall_median']:>9.3f}s  "
          f"ratio={ratio:>5.2f}x  jobs={a['jobs']}  reps={a['reps']}")
print()
ct = d.get("pipen_caching_timing")
if ct:
    print("# pipen cold vs warm (caching arm)")
    print(f"  N={ct['n']}  cold: jobs={ct['cold_run_jobs']} wall={ct['cold_wall_sec']}s  ->  "
          f"warm1: jobs={ct['warm1_jobs']} wall={ct['warm1_wall_sec']}s "
          f"({ct['speedup_cold_over_warm1']}x)")
    print(f"  pipen-runinfo present in these job dirs: version {ct.get('runinfo_version')}")
else:
    print("# pipen cold vs warm: not available in this run")
print()
print("# invalidation scope phases (jobs executed per phase)")
for r in d.get("pipen_caching_scope") or []:
    print(f"  pipen {r['phase']:<24} jobs={r['jobs_executed']:<4} wall={r['wall_sec']}s")
for r in d.get("smk_caching_scope") or []:
    print(f"  smk   {r['phase']:<24} jobs={r['jobs_executed']:<4} wall={r['wall_sec']}s")
if d.get("missing"):
    print()
    print("# MISSING INPUTS (expected for a reduced-size run; see PORTABILITY.md)")
    for m in d["missing"]:
        print(f"  - {m}")

# --------------------------------------------------------------------------
# measurement integrity: the marker log has one line per job *event* (start and
# end for the DAG arms, one line per job for the caching DAG).  If the marker
# filesystem drops concurrent appends the counts come out low, so every arm is
# checked against its own arithmetic expectation here.
# --------------------------------------------------------------------------
def expected_lines(rec):
    n = rec.get("n")
    if rec.get("step") in ("3_scaling", "4_concurrency"):
        return 2 * (n + 1)          # per shard job: a start and an end line, + agg
    if rec.get("step") in ("5_caching_scope", "5_caching_timing"):
        return 3 * n + 1            # Read+Mid+Side per input, + agg
    return None


print()
print("# measurement-integrity cross-check (marker lines vs expected per arm)")
print("#   the full-set expectation only applies to cold/full runs; re-runs and")
print("#   post-invalidation phases legitimately execute a subset, so they are")
print("#   reported for information and never flagged.")
checks = []


def is_full_set(rec):
    """True when the arm must execute every job of its DAG."""
    if rec.get("step") in ("3_scaling", "4_concurrency"):
        return True
    if rec.get("step") == "5_caching_timing":
        return rec.get("note") == "cold"
    if rec.get("step") == "5_caching_scope":
        return str(rec.get("tag", "")).endswith("r1_cold")
    return False


for src in ("pipen_records_steps34.json", "pipen_records_step5.json",
            "smk_records_steps34.json", "smk_records_step5.json"):
    p = out / src
    if not p.exists():
        continue
    for rec in json.loads(p.read_text()):
        exp = expected_lines(rec)
        if exp is None:
            continue
        got = rec.get("jobs_executed")
        if not is_full_set(rec):
            print(f"  --   {rec.get('tag'):<26} marker-observed jobs={got:<4} "
                  f"(subset by design; a full run of this DAG would be {exp})")
            continue
        ok = got == exp
        checks.append({"tag": rec.get("tag"), "got": got, "expected": exp, "ok": ok})
        print(f"  {'OK  ' if ok else 'LOW '} {rec.get('tag'):<26} marker-observed jobs="
              f"{got:<4} expected={exp:<4} wall={rec.get('wall_sec')}s")
for rec in json.loads((out / "pipen_records_step5.json").read_text()) if (out / "pipen_records_step5.json").exists() else []:
    if rec.get("step") == "5_caching_scope" and rec.get("tag") == "s5_r1_cold":
        scope = cfg.path("work_root") / "wd_s5_scope"
        if scope.exists():
            dirs = sum(1 for _ in scope.rglob("job.script"))
            print(f"  {'OK  ' if dirs == rec['jobs_executed'] else 'LOW '} ground truth: "
                  f"{dirs} job directories on disk vs {rec['jobs_executed']} marker lines "
                  f"for the cold phase")
            checks.append({"tag": "scope_job_dirs", "got": rec["jobs_executed"],
                           "expected": dirs, "ok": dirs == rec["jobs_executed"]})
bad = [c for c in checks if not c["ok"]]
(out / "integrity_check.json").write_text(json.dumps(checks, indent=2))
print(f"# integrity: {len(checks) - len(bad)}/{len(checks)} arms match their expected "
      f"marker-line count; report in {out / 'integrity_check.json'}")
if bad:
    print("WARNING: marker-line counts are LOW for: "
          + ", ".join(c["tag"] for c in bad)
          + "  -> the marker filesystem is losing concurrent appends; put WORK_ROOT "
            "on a local disk and re-run.")

# --------------------------------------------------------------------------
# cross-arm artefact equality: the pipen DAG and the equivalent Snakefile must
# write byte-identical agg.txt for the same N (this is the claim a reviewer
# checks first).
# --------------------------------------------------------------------------
print()
print("# agg.txt cross-arm comparison (sha256, one file per arm in artefacts/)")
hashes = []
for src in ("pipen_records_steps34.json", "smk_records_steps34.json"):
    p = out / src
    if not p.exists():
        continue
    for rec in json.loads(p.read_text()):
        if rec.get("step") in ("3_scaling", "4_concurrency") and rec.get("agg_sha256"):
            hashes.append((rec.get("tag"), rec.get("n"), rec.get("agg_file"),
                           rec.get("agg_sha256"), rec.get("agg_bytes")))
pipen_by_n = {h[1]: h for h in hashes if h[0].startswith("s3") or h[0].startswith("s4")}
smk_by_n = {h[1]: h for h in hashes if h[0].startswith("smk_")}
agree = 0
for n in sorted(set(pipen_by_n) | set(smk_by_n)):
    a, b = pipen_by_n.get(n), smk_by_n.get(n)
    if not a or not b:
        print(f"  N={n:<5} only one arm present ({'pipen' if a else 'snakemake'})")
        continue
    same = a[3] == b[3]
    agree += same
    print(f"  N={n:<5} pipen={a[3][:16]}...  snakemake={b[3][:16]}...  "
          f"{'IDENTICAL' if same else 'DIFFERENT'}")
print(f"# agg.txt: {agree} of {len(set(pipen_by_n) & set(smk_by_n))} matched N produced "
      f"byte-identical output across the two frameworks")
scope_a = json.loads((out / "pipen_cache_scope.json").read_text()).get("agg_archive") \
    if (out / "pipen_cache_scope.json").exists() else None
print(f"# caching-DAG agg.txt (pipen, archived): "
      f"{scope_a.get('agg_file') if scope_a else '(absent)'} "
      f"sha256={scope_a.get('agg_sha256') if scope_a else '-'}")

print()
print(f"# verbatim console transcript: {out / 'run_all.log'}")
