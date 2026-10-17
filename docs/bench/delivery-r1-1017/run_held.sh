#!/bin/sh
# Held-out pass for the chosen arm(s) given as arguments (v0 always). Needs PCSS_KEY in the environment.
cd "$(dirname "$0")" || exit 1
for a in sp "$@"; do python3 -I bench.py gen $a held; done
for a in "$@"; do python3 -I bench.py judge $a sp held; done
for a in "$@"; do python3 -I bench.py judge $a sp held; python3 -I bench.py score $a sp held; done
echo DONE-HELD
