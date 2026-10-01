#!/usr/bin/env bash
set -u
cd "$HOME/bench/out"
for tag in sleep05 nosleep forks1; do
  echo "########## $tag ##########"
  "$HOME/bench/.venv/bin/python" /mnt/f/E/hermes-workspace/pipen/bench/analyse_marker.py "$HOME/bench/out/marker_diag_$tag.log"
done
