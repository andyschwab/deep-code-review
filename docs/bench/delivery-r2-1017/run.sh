#!/bin/sh
# Needs PCSS_KEY in the environment. Judge passes repeat until every record exists (a failed call writes nothing).
cd "$(dirname "$0")" || exit 1
for a in sp v0 ship; do python3 -I bench.py gen $a; done
for a in v0 ship; do for i in 1 2 3; do python3 -I bench.py judge $a sp; done; python3 -I bench.py score $a sp; done
python3 -I bench.py paired v0 ship
