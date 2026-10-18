#!/bin/sh
# Needs PCSS_KEY in the environment. Judge passes repeat until every record exists (a failed call writes nothing).
cd "$(dirname "$0")" || exit 1
for a in sp ship; do python3 -I bench.py gen $a; done
for i in 1 2 3; do python3 -I bench.py judge ship sp; done
python3 -I bench.py score ship sp
