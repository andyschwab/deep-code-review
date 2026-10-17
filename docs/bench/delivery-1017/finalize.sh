#!/bin/sh
# Final scoring. GLM-5.2 with thinking timed out on most tiebreak calls, so judge/glm-t is dropped (never complete)
# and the tiebroken column equals the strict column for the thinking judges. Non-thinking GLM (judge/glm) is complete for the baseline.
set -e
cd "$(dirname "$0")"
rm -rf judge/glm-t
export JTHINK=1
for p in "perun sp" "perun gs" "perun2 sp" "perun2 gs"; do python3 -I bench.py score $p; done
unset JTHINK
for p in "perun sp" "perun gs"; do python3 -I bench.py score $p; done
