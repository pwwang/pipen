#!/usr/bin/env bash
# Step 1+2: environment record + fresh venv install of pipen from source
#
# ARCHIVED (run-once, this machine's paths: $HOME/bench/.venv, ~/github/pipen).
# SUPERSEDED by the portable setup_env.sh -> run_all.sh pair, which read every
# path from bench.env.  Kept verbatim as provenance of the archived full run.
set -x
BENCH_HOME="$HOME/bench"
OUT="$BENCH_HOME/out"
mkdir -p "$OUT"

# ---- environment record ----
{
  echo "=== uname ==="; uname -a
  echo "=== os-release ==="; cat /etc/os-release
  echo "=== nproc ==="; nproc
  echo "=== lscpu ==="; lscpu
  echo "=== meminfo ==="; grep -E 'MemTotal|SwapTotal' /proc/meminfo
  echo "=== lsblk ==="; lsblk -o NAME,ROTA,SIZE,TYPE,MOUNTPOINT 2>/dev/null || echo "lsblk unavailable"
  echo "=== df ==="; df -hT / /mnt/f $HOME 2>/dev/null
  echo "=== python ==="; python3 --version; which python3
  echo "=== pip ==="; python3 -m pip --version 2>&1 | head -2
  echo "=== uv ==="; which uv && uv --version || echo "uv not present"
  echo "=== java ==="; which java && java -version 2>&1 | head -3 || echo "java not present"
  echo "=== cpu governor ==="; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "no cpufreq (VM)"
} > "$OUT/env_raw.txt" 2>&1

# ---- fresh venv ----
rm -rf "$BENCH_HOME/.venv"
python3 -m venv "$BENCH_HOME/.venv"
VP="$BENCH_HOME/.venv/bin"
"$VP/python" -m pip install --upgrade pip > "$OUT/pip_upgrade.log" 2>&1
echo "PIP_UPGRADE_RC=$?" >> "$OUT/pip_upgrade.log"

"$VP/pip" install -e "$HOME/github/pipen" > "$OUT/pipen_install.log" 2>&1
echo "PIPEN_INSTALL_RC=$?"
tail -25 "$OUT/pipen_install.log"
