#!/usr/bin/env python3
"""Emit environment.json: the machine/version provenance of a benchmark run.

Paths and interpreters come from ``bench.env`` (see ``bench_config.py``).  Any
piece that cannot be determined on this machine is recorded as a string
``<unavailable: ...>`` instead of aborting the run.

Usage::

    env_json.py [destination]        default: <OUT_ROOT>/environment.json
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_config import load  # noqa: E402

CFG = load()
OUT = CFG.path("out_root")
PY = CFG.py
REPO = CFG.path("pipen_repo") if CFG.raw("pipen_repo") else None
SMK = CFG.smk


def sh(cmd: str) -> str:
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=120).stdout.strip()
    except Exception as e:  # pragma: no cover
        return f"<unavailable: {e}>"


uname = sh("uname -a")
try:
    osrel = dict(l.split("=", 1) for l in open("/etc/os-release").read().splitlines() if "=" in l)
except Exception:
    osrel = {}

lscpu = sh("lscpu")
lscpu_d = {}
for line in lscpu.splitlines():
    if ":" in line:
        k, v = line.split(":", 1)
        lscpu_d[k.strip()] = v.strip()

meminfo = {}
try:
    for line in open("/proc/meminfo"):
        if ":" in line:
            k, v = line.split(":", 1)
            meminfo[k.strip()] = v.strip()
except Exception:
    pass

# only query filesystems that exist on this machine
disk_paths = [str(p) for p in {Path("/"), OUT, CFG.path("work_root"), CFG.root} if Path(p).exists()]
lsblk = sh("lsblk -o NAME,ROTA,SIZE,TYPE,MOUNTPOINT -d")
df = sh("df -hT " + " ".join(f"'{p}'" for p in disk_paths))


def py_version(interpreter: str, code: str) -> str:
    if not interpreter:
        return ""
    return sh(f"'{interpreter}' -c {json.dumps(code)}")


pipen_ver = py_version(str(PY), "import pipen; print(pipen.__version__)")
pipen_file = py_version(str(PY), "import pipen; print(pipen.__file__)")
runinfo_ver = py_version(str(PY),
                         "import importlib.metadata as m; print(m.version('pipen-runinfo'))")
if not runinfo_ver or runinfo_ver.startswith("<unavailable"):
    runinfo_ver = ""

git_sha = git_describe = git_branch = git_date = ""
if REPO and (REPO / ".git").exists():
    git_sha = sh(f"git -C '{REPO}' rev-parse HEAD")
    git_describe = sh(f"git -C '{REPO}' describe --tags --always --dirty")
    git_branch = sh(f"git -C '{REPO}' rev-parse --abbrev-ref HEAD")
    git_date = sh(f"git -C '{REPO}' log -1 --format=%cI")
else:
    note = f"<unavailable: no git checkout at {REPO}>" if REPO else "<not configured: PIPEN_REPO empty>"
    git_sha = git_describe = git_branch = git_date = note

deps = {}
for pkg in ["liquidpy", "pandas", "enlighten", "argx", "xqute", "python-simpleconf",
            "pipda", "varname", "diot", "simplug", "rich", "snakemake",
            "pipen-runinfo"]:
    v = sh(f"'{PY}' -m pip show {pkg} 2>/dev/null | grep -E '^Version' | cut -d' ' -f2")
    if not v and pkg == "snakemake" and SMK:
        smk_py = str(Path(SMK).parent / "python")
        v = sh(f"'{smk_py}' -m pip show {pkg} 2>/dev/null | grep -E '^Version' | cut -d' ' -f2") \
            if Path(smk_py).exists() else ""
    deps[pkg] = v or None

out = {
    "bench_config": CFG.as_dict(),
    "wsl_distro": osrel.get("PRETTY_NAME", "").strip('"'),
    "os_release": osrel,
    "kernel": uname,
    "kernel_release": platform.release(),
    "nproc": int(sh("nproc") or 0),
    "cpu_model_name": lscpu_d.get("Model name"),
    "cpu_mhz": lscpu_d.get("CPU MHz"),
    "cpu_max_mhz": lscpu_d.get("CPU max MHz"),
    "cpu_min_mhz": lscpu_d.get("CPU min MHz"),
    "lscpu_onlines": lscpu_d.get("On-line CPU(s) list"),
    "lscpu_caches": {k: v for k, v in lscpu_d.items() if k.startswith("L")},
    "lscpu_raw": lscpu,
    "mem_total": meminfo.get("MemTotal"),
    "mem_total_bytes": int(re.sub(r"\D", "", meminfo.get("MemTotal", "0")) or 0) * 1024,
    "swap_total": meminfo.get("SwapTotal"),
    "lsblk_devices": lsblk,
    "df": df,
    "df_paths": disk_paths,
    "python_version": sys.version,
    "python_executable": str(PY),
    "pipen_version": pipen_ver,
    "pipen_import_path": pipen_file,
    "pipen_runinfo_version": runinfo_ver or None,
    "snakemake_executable": SMK,
    "pipen_git_commit": git_sha,
    "pipen_git_describe": git_describe,
    "pipen_git_branch": git_branch,
    "pipen_git_commit_date": git_date,
    "dependency_versions": deps,
    "java": sh("java -version 2>&1 | head -3"),
}

dest = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "environment.json"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(out, indent=2))
print(json.dumps({k: v for k, v in out.items()
                  if k not in ("lscpu_raw", "os_release", "bench_config")}, indent=2))
print(f"\n# written to {dest}", file=sys.stderr)
