#!/usr/bin/env bash
# With pgrep/ps unavailable (PATH stubs that fail, as in a restrictive sandbox), test-train-scripts.sh must
# SKIP its reap_own blocks and still return promptly instead of hanging on an unreapable child.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
S="$(mktemp -d "${TMPDIR:-/tmp}/dcr-test-nopgrep.XXXXXX")"
trap 'rm -rf "$S"' EXIT
mkdir "$S/bin"
for c in pgrep ps; do printf '#!/bin/sh\nexit 1\n' >"$S/bin/$c"; chmod +x "$S/bin/$c"; done
start=$SECONDS
PATH="$S/bin:$PATH" perl -e 'alarm 120; exec @ARGV' bash "$ROOT/scripts/test-train-scripts.sh" >"$S/out" 2>&1
rc=$?
took=$((SECONDS - start))
fail=0
grep -q '^SKIP  reap_own' "$S/out" || { echo "FAIL  reap_own did not SKIP"; fail=1; }
[ "$rc" -ne 142 ] && [ "$took" -lt 100 ] || { echo "FAIL  hung (rc=$rc, ${took}s)"; fail=1; }
[ "$fail" -eq 0 ] && echo "PASS  reap_own SKIPs without pgrep/ps and returns (${took}s)"
exit "$fail"
