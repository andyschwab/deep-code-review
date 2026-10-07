#!/usr/bin/env bash
# train_land.sh <tag> <pr> <pr> [pr...] — union-verify a train from the fresh base, then land every PR of a
# GREEN union via land_train.sh. Never a single-PR train: one PR goes through the normal merge path.
#
# Stacked children of each member are retargeted to the base by land_train.sh before the merge.
#
# Refuses the whole train when any PR's base is not BASE_BRANCH. Linked worktrees in UNION_DIRS are removed on
# every exit (_clean_union.sh); the current worktree is kept.
#
# Run it from a detached tools worktree on the base branch; it re-detaches that worktree onto the fresh base.
# Env: VERIFY_CMD (required; run via bash -c as `$VERIFY_CMD <tag> <pr...>`, must print a final line
# "GREEN base=<sha> union=<sha>" on success, e.g. a merge_train.py wrapper), UNION_DIRS (required, passed on
# to land_train.sh), BASE_BRANCH (default main), REMOTE (default origin), LOG_DIR (default .).
# Takes a per-worktree lock (<git-dir>/train-land.lock, pid-checked; a dead holder's lock is reclaimed), so two
# trains cannot share this worktree or a log. UNION_DIRS: space-separated, or newline-separated when a path has a space.
# Exit: 0 landed, 1 base/browser red or lock held, 2 usage/refused, 3 no GREEN union (nothing landed).
# Optional: CLEAN_ROOT (your own worktree tree: runs reap_own.sh and clean_finished.sh on it first), BASE_AUDIT_CMD (run via bash -c on the bare fresh base before verifying; non-zero prints
# "BASE RED" and exits 1, so a red base is never blamed on a PR), RATCHET_CMD (run via bash -c on each PR
# merged alone onto the base, with PR=<n>; when no union is GREEN, prints "CULPRIT #n" for each PR that fails it),
# BROWSER_CMD (run via bash -c in this worktree checked out at the GREEN union, with UNION_SHA and BASE_SHA set,
# before anything lands: the affected browser specs plus the smoke set; non-zero prints "BROWSER RED" and lands
# nothing. Unset = loud "WARN" that the union's browser specs were NOT run; BROWSER_CMD=skip is the explicit opt-out).
set -euo pipefail
[ $# -ge 3 ] || { echo "usage: train_land.sh <tag> <pr> <pr> [pr...] (a train is >= 2 PRs)" >&2; exit 2; }
: "${VERIFY_CMD:?set VERIFY_CMD}" "${UNION_DIRS:?set UNION_DIRS}"
T=$1; shift
BASE_BRANCH=${BASE_BRANCH:-main} REMOTE=${REMOTE:-origin} LOG=${LOG_DIR:-.}/train$T.log
HERE=$(cd "$(dirname "$0")" && pwd) GH=${GH:-gh}
. "$HERE/_clean_union.sh"
# .perun/policy.json: PERUN_JOBS (parallelism from local_cpu) and PERUN_GITHUB_ACTIONS reach VERIFY_CMD and
# BROWSER_CMD. github_actions=off: this script never waits on or re-runs CI (it has no CI wait at all), and
# land_train.sh adds [skip ci] to every merge-commit body only; it never suppresses PR-head checks or
# tag-triggered releases. A malformed policy fails closed (exit 2).
PERUN_GITHUB_ACTIONS=$(python3 "$HERE/perun_policy.py" get github_actions) && PERUN_JOBS=$(python3 "$HERE/perun_policy.py" lanes) \
  || { echo "train_land: bad .perun/policy.json" >&2; exit 2; }
export PERUN_GITHUB_ACTIONS PERUN_JOBS
LOCK=$(git rev-parse --git-dir)/train-land.lock
if ! mkdir "$LOCK" 2>/dev/null; then
  p=$(cat "$LOCK/pid" 2>/dev/null || true)
  if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then echo "train_land: lock held by pid $p ($LOCK)" >&2; exit 1; fi
  rm -rf "$LOCK"; mkdir "$LOCK" || { echo "train_land: cannot take $LOCK" >&2; exit 1; }
fi
echo $$ >"$LOCK/pid"; trap 'clean_union_dirs; rm -rf "$LOCK"' EXIT
if [ -n "${CLEAN_ROOT:-}" ]; then  # start-of-train cleanup of your own finished work; never blocks the train
  ROOT=$CLEAN_ROOT bash "$HERE/reap_own.sh" || true; ROOT=$CLEAN_ROOT bash "$HERE/clean_finished.sh" || true
fi
for n in "$@"; do
  bb=$("$GH" pr view "$n" --json baseRefName -q .baseRefName </dev/null)
  [ "$bb" = "$BASE_BRANCH" ] || { echo "REFUSE #$n base is $bb, expected $BASE_BRANCH; nothing built" >&2; exit 2; }
done

git fetch -q "$REMOTE" "$BASE_BRANCH"
git checkout -q --detach "$REMOTE/$BASE_BRANCH"
if [ -n "${BASE_AUDIT_CMD:-}" ] && ! bash -c "$BASE_AUDIT_CMD" >"$LOG.base" 2>&1 </dev/null; then
  echo "BASE RED: audit fails on bare $REMOTE/$BASE_BRANCH (see $LOG.base); no PR to blame, nothing landed" >&2; exit 1
fi
rc=0; bash -c "$VERIFY_CMD" _ "$T" "$@" >"$LOG" 2>&1 </dev/null || rc=$?
# Filter by verdict prefix, never by position; `|| true` keeps pipefail from aborting on no match.
grep -E '^(DEFER|DROP|GREEN|RED|STALE|CONFLICT)' "$LOG" | tail -4 || true
L=$(grep -E '^GREEN' "$LOG" | tail -1 || true)
if [ -z "$L" ]; then
  if [ -n "${RATCHET_CMD:-}" ]; then  # attribute: merge each PR alone onto the base, run the ratchet
    base=$(git rev-parse HEAD)
    for n in "$@"; do
      git checkout -q --detach "$base"
      if git fetch -q "$REMOTE" "pull/$n/head" && git merge -q --no-edit FETCH_HEAD >/dev/null 2>&1 \
        && ! PR=$n bash -c "$RATCHET_CMD" >/dev/null 2>&1 </dev/null; then echo "CULPRIT #$n fails the ratchet alone on the base"; fi
      git merge --abort 2>/dev/null || true
    done
    git checkout -q --detach "$base"
  fi
  echo "no GREEN union (verify rc=$rc); nothing landed"; exit 3
fi
B=$(sed -E 's/.*base=([0-9a-f]+).*/\1/' <<<"$L"); U=$(sed -E 's/.*union=([0-9a-f]+).*/\1/' <<<"$L")
if [ -z "${BROWSER_CMD:-}" ] || [ "$BROWSER_CMD" = skip ]; then
  echo "WARN: browser specs NOT run on union $U (BROWSER_CMD unset or skip); UI breakage can land unproven" >&2
else
  git checkout -q --detach "$U"
  rc=0; UNION_SHA=$U BASE_SHA=$B bash -c "$BROWSER_CMD" >"$LOG.browser" 2>&1 </dev/null || rc=$?
  git checkout -q --detach "$REMOTE/$BASE_BRANCH"
  [ $rc -eq 0 ] || { echo "BROWSER RED: union $U fails browser specs (see $LOG.browser); nothing landed" >&2; exit 1; }
fi
bash "$HERE/land_train.sh" "$B" "$U"  # not exec: the EXIT trap must still fire
