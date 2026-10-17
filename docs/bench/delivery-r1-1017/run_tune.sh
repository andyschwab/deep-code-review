#!/bin/sh
# Tune pass: generate all arms on the 10 tune tickets, judge each vs sp, score. Needs PCSS_KEY in the environment.
cd "$(dirname "$0")" || exit 1
for a in sp v0 e1 e2 e3 all; do python3 -I bench.py gen $a tune; done
for a in v0 e1 e2 e3 all; do python3 -I bench.py judge $a sp tune; done
for a in v0 e1 e2 e3 all; do python3 -I bench.py score $a sp tune; done
echo DONE-TUNE
