#!/usr/bin/env bash
# train_flake.sh — triage NEW gate failures into REAL vs FLAKE by re-running each alone.
# Usage: train_flake.sh <failed-ids-file> [baseline-ids-file]     (one test id per line)
# Env: RERUN_CMD (required; run via bash -c with TEST=<id>; exit 0 = pass), FLAKE_RUNS (default 3), FLAKE_REAL_AT (default 2).
# An id already failing on the base (baseline file) is skipped: it is not new. A new id is REAL only when it fails at least
# FLAKE_REAL_AT of FLAKE_RUNS isolated re-runs; stops early once the verdict is fixed. Prints "REAL <id>" / "FLAKE <id>"
# lines (flakes are reported separately, never blamed on a PR). Exit: 0 no REAL ids, 1 at least one REAL, 2 usage or bad FLAKE_RUNS/FLAKE_REAL_AT (fails closed).
set -uo pipefail
[ $# -ge 1 ] && [ -n "${RERUN_CMD:-}" ] || { echo "usage: RERUN_CMD=... train_flake.sh <failed-ids> [baseline-ids]" >&2; exit 2; }
runs=${FLAKE_RUNS:-3} need=${FLAKE_REAL_AT:-2} real=0
case $runs$need in ''|*[!0-9]*) echo "train_flake: FLAKE_RUNS/FLAKE_REAL_AT must be integers" >&2; exit 2 ;; esac
[ "$runs" -ge 1 ] && [ "$need" -ge 1 ] && [ "$need" -le "$runs" ] || { echo "train_flake: need 1 <= FLAKE_REAL_AT <= FLAKE_RUNS" >&2; exit 2; }
while IFS= read -r id; do
  [ -n "$id" ] || continue
  [ -z "${2:-}" ] || ! grep -qxF -- "$id" "$2" 2>/dev/null || continue
  f=0 p=0
  for _ in $(seq "$runs"); do
    if TEST=$id bash -c "$RERUN_CMD" >/dev/null 2>&1 </dev/null; then p=$((p + 1)); else f=$((f + 1)); fi
    [ "$f" -ge "$need" ] || [ "$p" -gt $((runs - need)) ] && break
  done
  if [ "$f" -ge "$need" ]; then echo "REAL $id"; real=1; else echo "FLAKE $id (failed $f of $((f + p)) alone)"; fi
done <"$1"
exit $real
