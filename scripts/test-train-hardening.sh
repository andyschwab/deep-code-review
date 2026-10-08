#!/usr/bin/env bash
# Tests for the merge-train hardening (#1341): UNION_DIRS paths with spaces, a per-worktree train lock,
# and a distinct exit (3) when no union is GREEN. Plain bash; gh is a PATH stub. Writes only under $WORK.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SC="$ROOT/.claude/skills/agentic-delivery/scripts"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/dcr-test-train-hard.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
pass=0 fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; pass=$((pass + 1)); else echo "FAIL  $2"; fail=$((fail + 1)); fi; }
R="$WORK/clone dir"   # the space is the point
g() { git -C "$R" -c user.email=t@example.com -c user.name=T "$@"; }
git init -q --bare "$WORK/origin.git" -b main
git clone -q "$WORK/origin.git" "$R" 2>/dev/null
g commit -q --allow-empty -m base; g push -q origin HEAD:main
B=$(g rev-parse HEAD)
g checkout -q -b pr1 "$B"; echo 1 >"$R/f1"; g add f1; g commit -q -m "pr 1"; H1=$(g rev-parse pr1)
g checkout -q --detach "$B"; g merge -q --no-ff -m "merge-train: #1" pr1; U=$(g rev-parse HEAD)

mkdir -p "$WORK/bin"
cat >"$WORK/bin/gh" <<'STUB'
#!/usr/bin/env bash
case "$1 $2" in
  "pr view") case "$5" in headRefOid) echo "$H1" ;; baseRefName) echo main ;; isDraft) echo false ;;
                mergeable) echo MERGEABLE ;; headRefName) echo br1 ;; esac ;;
  "pr diff") echo changelog.d/x.md ;;
  "pr merge") echo "merged $3" ;;
esac
STUB
chmod +x "$WORK/bin/gh"; export H1 PATH="$WORK/bin:$PATH"
cd "$R" || exit 2

out=$(UNION_DIRS="/nonexistent"$'\n'"$R" WAIT_SECS=0 bash "$SC/land_train.sh" "$B" "$U" 2>&1); rc=$?
[ $rc -eq 0 ] && grep -q "^#1(MERGEABLE) last: merged 1" <<<"$out" && grep -q "WARN UNION_DIRS entry is not a directory: '/nonexistent'" <<<"$out"
ok $? "land_train: newline-separated UNION_DIRS finds a union in a path with a space; missing entry warns"
out=$(UNION_DIRS="$R" WAIT_SECS=0 bash "$SC/land_train.sh" "$B" "$U" 2>&1); rc=$?
[ $rc -eq 2 ] && grep -q "is not a directory" <<<"$out"; ok $? "land_train: space-separated list splits a spaced path, warns, exits 2"

RED='echo "RED"; exit 1'
out=$(VERIFY_CMD="$RED" UNION_DIRS="$R" LOG_DIR="$WORK" bash "$SC/train_land.sh" t1 1 2 2>&1); rc=$?
[ $rc -eq 3 ] && grep -q "nothing landed" <<<"$out"; ok $? "train_land: no GREEN union exits 3, distinct from landed (0)"

LOCK="$R/.git/train-land.lock"; sleep 300 & P=$!
mkdir "$LOCK"; echo "$P" >"$LOCK/pid"
out=$(VERIFY_CMD="$RED" UNION_DIRS="$R" LOG_DIR="$WORK" bash "$SC/train_land.sh" t2 1 2 2>&1); rc=$?
[ $rc -eq 1 ] && grep -q "lock held by pid $P" <<<"$out" && [ -d "$LOCK" ]; ok $? "train_land: a live lock holder refuses a second train and keeps the lock"
kill "$P" 2>/dev/null; wait "$P" 2>/dev/null
echo 1 >"$LOCK/ts"  # old record: a pid-only lock counts as young (owner may be mid-write)
out=$(VERIFY_CMD="$RED" UNION_DIRS="$R" LOG_DIR="$WORK" bash "$SC/train_land.sh" t3 1 2 2>&1); rc=$?
[ $rc -eq 1 ] && grep -q "STALE-LOCK" <<<"$out" && [ -d "$LOCK" ]; ok $? "train_land: a dead holder's lock is reported with a clear command, never auto-reclaimed"
rm -f "$LOCK/pid" "$LOCK/ts"; rmdir "$LOCK"
out=$(VERIFY_CMD="$RED" UNION_DIRS="$R" LOG_DIR="$WORK" bash "$SC/train_land.sh" t4 1 2 2>&1); rc=$?
[ $rc -eq 3 ] && [ ! -e "$LOCK" ]; ok $? "train_land: after the hand clear the lock is taken and released on exit"

echo "$pass passed, $fail failed"; [ "$fail" -eq 0 ]
