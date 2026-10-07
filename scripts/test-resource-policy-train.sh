#!/usr/bin/env bash
# Tests for the .perun/policy.json wiring in agentic-delivery/scripts/{land_train,train_land}.sh. gh is a PATH stub.
# Prints PASS/FAIL lines; exits non-zero on any failure. Writes only under $WORK.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SC="$ROOT/.claude/skills/agentic-delivery/scripts"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/dcr-test-policy.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; else echo "FAIL  $2"; fail=$((fail + 1)); fi; }
g() { git -C "$R" -c user.email=t@example.com -c user.name=T "$@"; }

git init -q --bare "$WORK/origin.git" -b main
R="$WORK/clone"; git clone -q "$WORK/origin.git" "$R" 2>/dev/null
g commit -q --allow-empty -m base; g push -q origin HEAD:main
B=$(g rev-parse HEAD)
g checkout -q -b pr1 "$B"; echo 1 >"$R/f1"; g add f1; g commit -q -m "pr 1"
H1=$(g rev-parse pr1)
g checkout -q --detach "$B"; g merge -q --no-ff -m "merge-train: #1" pr1
U=$(g rev-parse HEAD)

STUB="$WORK/stub"; mkdir -p "$STUB/bin"
cat >"$STUB/bin/gh" <<'EOF'
#!/usr/bin/env bash
echo "gh $*" >>"$STUB/calls.log"
case "$1 $2" in
  "pr view") case "$5" in headRefOid) echo "$H1";; baseRefName) echo main;; mergeable) echo MERGEABLE;; isDraft) echo false;; headRefName) echo br1;; esac ;;
  "pr diff") echo changelog.d/1.md ;;
esac
EOF
chmod +x "$STUB/bin/gh"
export STUB H1 PATH="$STUB/bin:$PATH"
cd "$R" || exit 2

land() { : >"$STUB/calls.log"; UNION_DIRS="$R" BACKFILL_FILE="$WORK/bf.txt" WAIT_SECS=0 bash "$SC/land_train.sh" "$B" "$U" 2>&1 | tee "$WORK/land.out"; }
export PERUN_POLICY="$WORK/policy.json"
echo '{}' >"$PERUN_POLICY"; land >/dev/null
grep -q "pr merge 1 --merge --match-head-commit $H1\$" "$STUB/calls.log"; ok $? "land_train: default policy merges without [skip ci]"
echo '{"github_actions": "off"}' >"$PERUN_POLICY"; land >/dev/null
grep -q 'pr merge 1 --merge --match-head-commit .* --body \[skip ci\]' "$STUB/calls.log"; ok $? "land_train: github_actions=off adds [skip ci] to the merge"
echo '{"github_actions": 5.5e' >"$PERUN_POLICY"; land >/dev/null; rc=$?
out=$(UNION_DIRS="$R" bash "$SC/land_train.sh" "$B" "$U" 2>&1); rc=$?
[ $rc -eq 2 ] && grep -q "bad .perun/policy.json" <<<"$out"; ok $? "land_train: malformed policy fails closed (exit 2), nothing merged"

echo '{"local_cpu": 3, "github_actions": "off"}' >"$PERUN_POLICY"
out=$(VERIFY_CMD='echo "jobs=$PERUN_JOBS gha=$PERUN_GITHUB_ACTIONS"; echo "RED x"; exit 1' UNION_DIRS="$R" LOG_DIR="$WORK" bash "$SC/train_land.sh" t1 1 2 2>&1 >/dev/null; cat "$WORK/traint1.log")
grep -q "jobs=3 gha=off" <<<"$out"; ok $? "train_land: VERIFY_CMD sees PERUN_JOBS from local_cpu and PERUN_GITHUB_ACTIONS"
echo '{"local_cpu": "fast"}' >"$PERUN_POLICY"
UNION_DIRS="$R" VERIFY_CMD=true bash "$SC/train_land.sh" t2 1 2 >/dev/null 2>&1; [ $? -eq 2 ]; ok $? "train_land: malformed policy refuses the train (exit 2)"
grep -q "pr checks\|run rerun\|run watch" "$STUB/calls.log"; [ $? -ne 0 ]; ok $? "no CI poll/re-run gh call is ever made"
[ "$fail" -eq 0 ] && echo "all passed" || { echo "$fail failed"; exit 1; }
