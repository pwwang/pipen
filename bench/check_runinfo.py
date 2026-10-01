#!/usr/bin/env python3
"""List the per-job provenance files (job.runinfo.*) written by pipen-runinfo.

This is the self-describing part of the archived run: every pipen job directory
carries

    job.runinfo.session   interpreter / package versions used by that job
    job.runinfo.device    host, CPU, memory, disk, network, GPU of the node
    job.runinfo.time      GNU `time -v` accounting for that job

A reviewer checks these files to know *what* actually ran each job.

Usage::

    check_runinfo.py [root ...]        default root: WORK_ROOT from bench.env

Writes ``<OUT_ROOT>/runinfo_check.json`` and exits non-zero if RUNINFO=1 but no
job directory has any runinfo file.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_config import load  # noqa: E402

CFG = load()
OUT = CFG.path("out_root")
RUNINFO = CFG.bool("runinfo")
EXPECTED = ("session", "device", "time")
JOB_MARKERS = ("job.script", "job.status", "job.rc")

roots = [Path(a) for a in sys.argv[1:] if not a.startswith("--")]
if not roots:
    roots = [CFG.path("work_root")]
out_override = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--out=")), None)
report_path = Path(out_override) if out_override else OUT / "runinfo_check.json"


def is_jobdir(d: Path) -> bool:
    """A pipen job directory contains job.* bookkeeping files."""
    try:
        names = {p.name for p in d.iterdir() if p.is_file()}
    except (PermissionError, FileNotFoundError):
        return False
    return any(n in names for n in JOB_MARKERS) or any(n.startswith("job.runinfo.") for n in names)


jobdirs: list[Path] = []
for root in roots:
    if not root.exists():
        continue
    for dirpath, dirnames, _ in os.walk(root):
        d = Path(dirpath)
        if is_jobdir(d):
            jobdirs.append(d)
        # do not descend into a job directory's payload
        if ".output" in dirnames:
            dirnames.remove(".output")
jobdirs = sorted(set(jobdirs))

rows = []
for d in jobdirs:
    present = {}
    for kind in EXPECTED:
        f = d / f"job.runinfo.{kind}"
        present[kind] = {"path": str(f), "exists": f.exists(),
                         "bytes": f.stat().st_size if f.exists() else None}
    rows.append({"job_dir": str(d), "files": present,
                 "complete": all(v["exists"] for v in present.values())})

complete = [r for r in rows if r["complete"]]
with_any = [r for r in rows if any(v["exists"] for v in r["files"].values())]

print(f"# job.runinfo check (bench_config: RUNINFO={int(RUNINFO)})")
print(f"# roots scanned : {', '.join(str(r) for r in roots)}")
print(f"# job dirs found: {len(rows)}")
print(f"# with session+device+time: {len(complete)}")
print(f"# with at least one runinfo file: {len(with_any)}")
print()
for r in rows:
    flags = " ".join(("+" if r["files"][k]["exists"] else "-") + k for k in EXPECTED)
    print(f"{flags}  {r['job_dir']}")

sample_session = next((r["files"]["session"]["path"] for r in rows if r["files"]["session"]["exists"]), None)
sample_device = next((r["files"]["device"]["path"] for r in rows if r["files"]["device"]["exists"]), None)
sample_time = next((r["files"]["time"]["path"] for r in rows if r["files"]["time"]["exists"]), None)


def show(title: str, path: str | None, head: int = 40):
    print(f"\n=== {title} ===")
    if not path:
        print("(none produced)")
        return None
    p = Path(path)
    try:
        text = p.read_text(errors="replace")
    except Exception as exc:
        print(f"(unreadable: {exc})")
        return None
    print(f"--- {p} ---")
    lines = text.splitlines()
    print("\n".join(lines[:head]))
    if len(lines) > head:
        print(f"... ({len(lines) - head} more lines; {len(text)} bytes total)")
    return path


show("job.runinfo.session (first job that has one)", sample_session)
show("job.runinfo.time (first job that has one)", sample_time)
show("job.runinfo.device (first job that has one)", sample_device, head=12)

report = {
    "roots": [str(r) for r in roots],
    "runinfo_requested": RUNINFO,
    "job_dirs": len(rows),
    "job_dirs_complete": len(complete),
    "job_dirs_with_any": len(with_any),
    "sample_session_file": sample_session,
    "sample_session_text": Path(sample_session).read_text(errors="replace") if sample_session else None,
    "rows": rows,
}
OUT.mkdir(parents=True, exist_ok=True)
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2))
print(f"\n# report: {report_path}")

if RUNINFO and not with_any:
    print("\nFAIL: RUNINFO=1 but no job directory carries any job.runinfo.* file.",
          file=sys.stderr)
    sys.exit(1)
if rows and len(complete) < len(rows):
    print(f"\nNOTE: {len(rows) - len(complete)} of {len(rows)} job dirs lack one or more "
          "runinfo files (a job killed early, or a non-bash/python job).", file=sys.stderr)
sys.exit(0)
