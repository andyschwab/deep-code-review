#!/usr/bin/env bash
# train_land.sh <tag> <pr> <pr> [pr...] — union-verify a train from the fresh base, then land every PR of a
# GREEN union via land_train.sh. Never a single-PR train: one PR goes through the normal merge path.
#
# Run it from a detached tools worktree on the base branch; it re-detaches that worktree onto the fresh base.
# Env: VERIFY_CMD (required; run via bash -c as `$VERIFY_CMD <tag> <pr...>`, must print a final line
# "GREEN base=<sha> union=<sha>" on success, e.g. a merge_train.py wrapper), UNION_DIRS (required, passed on
# to land_train.sh), BASE_BRANCH (default main), REMOTE (default origin), LOG_DIR (default .).
set -euo pipefail
[ $# -ge 3 ] || { echo "usage: train_land.sh <tag> <pr> <pr> [pr...] (a train is >= 2 PRs)" >&2; exit 2; }
: "${VERIFY_CMD:?set VERIFY_CMD}" "${UNION_DIRS:?set UNION_DIRS}"
T=$1; shift
BASE_BRANCH=${BASE_BRANCH:-main} REMOTE=${REMOTE:-origin} LOG=${LOG_DIR:-.}/train$T.log
HERE=$(cd "$(dirname "$0")" && pwd)

git fetch -q "$REMOTE" "$BASE_BRANCH"
git checkout -q --detach "$REMOTE/$BASE_BRANCH"
rc=0; bash -c "$VERIFY_CMD" _ "$T" "$@" >"$LOG" 2>&1 </dev/null || rc=$?
# Filter by verdict prefix, never by position; `|| true` keeps pipefail from aborting on no match.
grep -E '^(DEFER|DROP|GREEN|RED|STALE|CONFLICT)' "$LOG" | tail -4 || true
L=$(grep -E '^GREEN' "$LOG" | tail -1 || true)
[ -n "$L" ] || { echo "no GREEN union (verify rc=$rc); nothing landed"; exit 0; }
B=$(sed -E 's/.*base=([0-9a-f]+).*/\1/' <<<"$L"); U=$(sed -E 's/.*union=([0-9a-f]+).*/\1/' <<<"$L")
exec bash "$HERE/land_train.sh" "$B" "$U"
