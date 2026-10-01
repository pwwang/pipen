#!/usr/bin/env bash
# Probe: does pipen 1.2.3 support disabling a plugin by name (runinfo)?
set -uo pipefail
V=/home/pwwang/ws_bench/.venv/lib/python3.12/site-packages/pipen
echo "=== files ==="
ls "$V"
echo
echo "=== grep 'plugin' in pipen/config.py ==="
grep -n -i "plugin" "$V/config.py" | head -40
echo
echo "=== grep 'plugin' in pipen/defaults.py ==="
grep -n -i "plugin" "$V/defaults.py" | head -40
echo
echo "=== how plugins get loaded (simplug) ==="
grep -rn "plugin" "$V/pipen.py" | head -30
echo
echo "=== probe: instantiate a tiny pipeline with plugins = ['-runinfo'] ==="
cd /tmp
cat > /tmp/probe_plugin_off.py <<'PY'
from pipen import Pipen, Proc

class P(Proc):
    input = "i"
    input_data = [1]
    output = "outfile:file:o.txt"
    script = "echo {{in.i}} > {{out.outfile}}"

class Pipe(Pipen):
    starts = P
    workdir = "/tmp/probe_plugin_off_wd"
    outdir = "/tmp/probe_plugin_off_out"
    plugins = ["-runinfo"]
    loglevel = "warning"

if __name__ == "__main__":
    Pipe().run()
    print("RAN_OK_with_plugins_-runinfo")
PY
rm -rf /tmp/probe_plugin_off_wd /tmp/probe_plugin_off_out
/home/pwwang/ws_bench/.venv/bin/python /tmp/probe_plugin_off.py 2>&1 | tail -5
echo "--- runinfo files present? (expect none) ---"
find /tmp/probe_plugin_off_wd -name 'job.runinfo.*' | head
echo "--- for contrast, the same DAG without the plugins setting ---"
sed 's/    plugins = \["-runinfo"\]//' /tmp/probe_plugin_off.py > /tmp/probe_plugin_on.py
sed -i 's#/tmp/probe_plugin_off_wd#/tmp/probe_plugin_on_wd#; s#/tmp/probe_plugin_off_out#/tmp/probe_plugin_on_out#' /tmp/probe_plugin_on.py
rm -rf /tmp/probe_plugin_on_wd /tmp/probe_plugin_on_out
/home/pwwang/ws_bench/.venv/bin/python /tmp/probe_plugin_on.py 2>&1 | tail -3
echo "--- runinfo files present? (expect all three) ---"
find /tmp/probe_plugin_on_wd -name 'job.runinfo.*'
