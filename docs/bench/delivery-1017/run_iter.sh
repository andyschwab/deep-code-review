#!/bin/sh
# usage: run_iter.sh ARM SPLIT  -- generate ARM on SPLIT, judge vs both rivals (thinking judges, no GLM), score.
# Needs KEYFILE in the environment.
set -e
cd "$(dirname "$0")"
export JTHINK=1 PAR=8 NOGLM=1
python3 -I bench.py gen "$1" "$2"
python3 -I bench.py judge "$1" sp "$2"
python3 -I bench.py judge "$1" gs "$2"
python3 -I bench.py score "$1" sp
python3 -I bench.py score "$1" gs
echo DONE-ITER
