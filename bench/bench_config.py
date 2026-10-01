#!/usr/bin/env python3
"""Single configuration entry point for the pipen benchmark harness.

Every driver, analyser and helper reads its paths and protocol sizes from here,
so nothing in the harness hardcodes a machine layout.

Resolution order (last one wins):

  1. DEFAULTS below
  2. KEY=VALUE lines in ``bench.env`` (next to this file, or ``$BENCH_ENV``)
  3. environment variables named ``BENCH_<KEY>`` (e.g. ``BENCH_NPROC=8``)

Usage::

    from bench_config import load
    CFG = load()
    PY, OUT, WORK = CFG.path("py"), CFG.path("out_root"), CFG.path("work_root")
    for n in CFG.list("scaling_ns"):
        ...

``python bench_config.py`` prints the resolved configuration (useful for a
reviewer: it is the first thing run_all.sh logs).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

#: key -> default (empty string means "computed at load time", see Config)
DEFAULTS: dict[str, str] = {
    # locations
    "root": "",            # -> HERE
    "py": "",              # -> sys.executable
    "smk": "",             # -> shutil.which("snakemake")
    "out_root": "",        # -> ROOT/out
    "work_root": "",       # -> OUT_ROOT/work
    # machine / protocol
    "nproc": "",           # -> os.cpu_count()
    "reps": "3",
    "scaling_ns": "1,10,100,500",
    "conc_n": "20",
    "conc_forks": "1,2,4,MAX",
    "cache_scope_n": "8",
    "cache_timing_n": "100",
    "cache_timing_reps": "1",
    "sleep": "0.05",
    # self-describing job dirs
    "runinfo": "1",
    "runinfo_install": "1",
    # environment creation (setup_env.sh only)
    "base_python": "python3",
    "pipen_install": "pipen==1.2.3",
    "pipen_runinfo_pkg": "pipen-runinfo",
    "smk_install": "snakemake==9.27.0",
    # provenance / publishing
    "pipen_repo": "",
    "archive": "",
    "loglevel": "info",
}

#: keys whose value is a path relative to ROOT
PATH_KEYS = ("root", "py", "smk", "out_root", "work_root", "pipen_repo", "archive")
#: keys whose value is an integer
INT_KEYS = ("nproc", "reps", "conc_n", "cache_scope_n", "cache_timing_n",
            "cache_timing_reps")
#: keys read as booleans
BOOL_KEYS = ("runinfo", "runinfo_install")


def env_file_path(env_file: str | os.PathLike | None = None) -> Path:
    """Location of the configuration file.

    ``$BENCH_ENV`` wins; then ``bench.local.env`` (machine-local paths written by
    setup_env.sh, *not* part of the archived materials); then ``bench.env``
    (the portable defaults committed with the harness).
    """
    if env_file:
        return Path(env_file)
    if os.environ.get("BENCH_ENV"):
        return Path(os.environ["BENCH_ENV"])
    local = HERE / "bench.local.env"
    return local if local.exists() else HERE / "bench.env"


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a shell-compatible ``KEY=VALUE`` file (comments with ``#``)."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().lower()
        value = value.split(" #", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


class Config:
    """Resolved harness configuration."""

    def __init__(self, values: dict[str, str], source: Path):
        self.values = values
        self.source = source
        # paths are resolved after ROOT is known
        self._root = None

    # -- primitive accessors ------------------------------------------------
    def raw(self, key: str, default: str = "") -> str:
        return str(self.values.get(key, DEFAULTS.get(key, default)))

    def path(self, key: str) -> Path:
        value = self.raw(key)
        if not value:
            return self._default_path(key)
        value = os.path.expandvars(os.path.expanduser(value))
        p = Path(value)
        return p if p.is_absolute() else (self.root / p).resolve()

    def int(self, key: str) -> int:
        value = self.raw(key)
        if value == "":
            return int(self._default_value(key))
        return int(float(value))

    def bool(self, key: str) -> bool:
        return _as_bool(self.raw(key) or DEFAULTS.get(key, "0"))

    def list(self, key: str) -> list[int]:
        """Integer list; the token ``MAX`` means NPROC."""
        out: list[int] = []
        for token in self.raw(key).replace(" ", "").split(","):
            if not token:
                continue
            out.append(self.nproc if token.upper() in ("MAX", "NPROC") else int(token))
        return out

    # -- computed defaults --------------------------------------------------
    @property
    def root(self) -> Path:
        value = self.raw("root")
        if not value:
            return HERE
        value = os.path.expandvars(os.path.expanduser(value))
        p = Path(value)
        return p if p.is_absolute() else (HERE / p).resolve()

    def _default_path(self, key: str) -> Path:
        if key == "out_root":
            return self.root / "out"
        if key == "work_root":
            return self.path("out_root") / "work"
        if key == "root":
            return self.root
        return Path("")

    def _default_value(self, key: str):
        if key == "nproc":
            return os.cpu_count() or 1
        return DEFAULTS.get(key, "")

    @property
    def nproc(self) -> int:
        value = self.raw("nproc")
        if value == "":
            return os.cpu_count() or 1
        return int(value)

    @property
    def py(self) -> Path:
        value = self.raw("py")
        return Path(value) if value else Path(sys.executable)

    @property
    def smk(self) -> str:
        """Snakemake executable (may be empty: the snakemake arms then fail loudly)."""
        value = self.raw("smk")
        if value:
            p = self.path("smk")
            return str(p) if p.is_absolute() else value
        return shutil.which("snakemake") or ""

    # -- derived helpers ----------------------------------------------------
    def python_has(self, module: str) -> bool:
        """True if ``module`` is importable by the configured PY interpreter."""
        import subprocess
        try:
            proc = subprocess.run([str(self.py), "-c", f"import {module}"],
                                  capture_output=True, text=True, timeout=180)
            return proc.returncode == 0
        except Exception:
            return False

    def module_version(self, module: str, distribution: str | None = None) -> str | None:
        """Version of ``module`` as seen by the configured PY interpreter."""
        import subprocess
        dist = distribution or module
        code = ("import importlib.metadata as m, sys\n"
                f"try:\n    import {module}\nexcept Exception:\n    sys.exit(3)\n"
                f"try:\n    print(m.version('{dist}'), flush=True)\n"
                "except Exception:\n    print(getattr(__import__('%s'), '__version__', '-'), flush=True)\n"
                % module)
        try:
            proc = subprocess.run([str(self.py), "-c", code],
                                  capture_output=True, text=True, timeout=180)
            if proc.returncode != 0:
                return None
            return proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else None
        except Exception:
            return None

    def mkdirs(self) -> dict[str, Path]:
        """Create the run directories and return them."""
        dirs = {
            "out_root": self.path("out_root"),
            "work_root": self.path("work_root"),
            "logs": self.path("out_root") / "logs",
            "logs_smk": self.path("out_root") / "logs_smk",
            "markers": self.path("out_root") / "markers",
        }
        for d in dirs.values():
            d.mkdir(parents=True, exist_ok=True)
        return dirs

    # -- introspection ------------------------------------------------------
    def as_dict(self) -> dict[str, str]:
        d = {k: self.raw(k) for k in DEFAULTS}
        d.update({
            "source": str(self.source),
            "root": str(self.root),
            "py": str(self.py),
            "smk": self.smk,
            "out_root": str(self.path("out_root")),
            "work_root": str(self.path("work_root")),
            "nproc": str(self.nproc),
        })
        return d

    def describe(self) -> str:
        lines = [f"# bench config <- {self.source}",
                 f"#   override file: BENCH_ENV=<path>   override keys: BENCH_<KEY>=<value>"]
        for key, value in self.as_dict().items():
            lines.append(f"{key.upper():<18}= {value}")
        return "\n".join(lines)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Config source={self.source} out_root={self.path('out_root')}>"


def load(env_file: str | os.PathLike | None = None) -> Config:
    """Read the configuration (file + ``BENCH_*`` environment overrides)."""
    source = env_file_path(env_file)
    values = dict(DEFAULTS)
    values.update(_parse_env_file(source))
    for key in DEFAULTS:
        over = os.environ.get(f"BENCH_{key.upper()}")
        if over is not None:
            values[key] = over
    return Config(values, source)


if __name__ == "__main__":
    print(load().describe())
