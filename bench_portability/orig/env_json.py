#!/usr/bin/env python3
"""Emit environment.json for the pipen benchmark."""
import json, os, platform, subprocess, sys, re

def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:
        return f"<error: {e}>"

home = os.path.expanduser("~")
repo = f"{home}/github/pipen"

# kernel / distro
uname = sh("uname -a")
try:
    osrel = dict(
        l.split("=", 1) for l in open("/etc/os-release").read().splitlines() if "=" in l
    )
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

# disk type from lsblk
lsblk = sh("lsblk -o NAME,ROTA,SIZE,TYPE,MOUNTPOINT -d")
df = sh("df -hT / /mnt/f " + home)

# pipen version + git commit
venv_py = f"{home}/bench/.venv/bin/python"
pipen_ver = sh(f"{venv_py} -c 'import pipen; print(pipen.__version__)'")
pipen_file = sh(f"{venv_py} -c 'import pipen; print(pipen.__file__)'")
git_sha = sh(f"git -C {repo} rev-parse HEAD")
git_describe = sh(f"git -C {repo} describe --tags --always --dirty")
git_branch = sh(f"git -C {repo} rev-parse --abbrev-ref HEAD")
git_date = sh(f"git -C {repo} log -1 --format=%cI")

deps = {}
for pkg in ["liquidpy", "pandas", "enlighten", "argx", "xqute", "python-simpleconf",
            "pipda", "varname", "diot", "simplug", "rich", "snakemake"]:
    v = sh(f"{venv_py} -m pip show {pkg} 2>/dev/null | grep -E '^(Version)' | cut -d' ' -f2")
    if not v:
        v = sh(f"{home}/bench/smk/bin/python -m pip show {pkg} 2>/dev/null | grep -E '^(Version)' | cut -d' ' -f2")
    deps[pkg] = v or None

out = {
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
    "python_version": sys.version,
    "python_executable": venv_py,
    "pipen_version": pipen_ver,
    "pipen_import_path": pipen_file,
    "pipen_git_commit": git_sha,
    "pipen_git_describe": git_describe,
    "pipen_git_branch": git_branch,
    "pipen_git_commit_date": git_date,
    "dependency_versions": deps,
    "java": sh("java -version 2>&1 | head -3"),
}

dest = sys.argv[1] if len(sys.argv) > 1 else f"{home}/bench/out/environment.json"
with open(dest, "w") as f:
    json.dump(out, f, indent=2)
print(json.dumps({k: v for k, v in out.items() if k not in ("lscpu_raw", "os_release")}, indent=2))
