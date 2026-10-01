#!/usr/bin/env python3
"""Make sure the pipeline interpreter (PY) can import pipen-runinfo.

pipen-runinfo is a pipen plugin: once installed in the interpreter that runs the
pipeline, every job directory gets ``job.runinfo.session`` (interpreter and
package versions), ``job.runinfo.device`` and ``job.runinfo.time`` with no
change to the pipeline code.

Controlled by bench.env: ``RUNINFO`` (1/0) and ``RUNINFO_INSTALL`` (1/0, may we
pip-install it?).  Exit codes: 0 = usable, 2 = missing and installing not
allowed, 3 = install attempted but still not importable.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_config import load  # noqa: E402

CFG = load()
PY = CFG.py

if not CFG.bool("runinfo"):
    print("RUNINFO=0: job.runinfo.* files are NOT requested (pipen-runinfo check skipped).")
    sys.exit(0)

version = CFG.module_version("pipen_runinfo", "pipen-runinfo")
if version:
    print(f"pipen-runinfo {version} is importable by {PY} -> job.runinfo.* will be written.")
    sys.exit(0)

pkg = CFG.raw("pipen_runinfo_pkg") or "pipen-runinfo"
print(f"pipen-runinfo is NOT importable by {PY}.")
if not CFG.bool("runinfo_install"):
    print("RUNINFO_INSTALL=0, refusing to install.  Fix with either "
          f"`{PY} -m pip install {pkg}` or RUNINFO=0 in bench.env.")
    sys.exit(2)

print(f"installing `{pkg}` into {PY} ...", flush=True)
proc = subprocess.run([str(PY), "-m", "pip", "install", pkg])
if proc.returncode != 0:
    print(f"pip install failed with rc={proc.returncode}", file=sys.stderr)
    sys.exit(3)

version = CFG.module_version("pipen_runinfo", "pipen-runinfo")
if not version:
    print("installed, but the module still does not import; check for a broken "
          "env or a pip/pipen mismatch.", file=sys.stderr)
    sys.exit(3)
print(f"pipen-runinfo {version} installed into {PY}.")
sys.exit(0)
