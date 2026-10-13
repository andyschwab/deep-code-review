#!/usr/bin/env bash
# Tests for the base-red guard in train_land.sh: when BROWSER_CMD fails and BASELINE_FAILS is unset, failing ids are re-run
# alone at BASE_SHA (RERUN_CMD, TEST=<id>); ids that also fail on the base are pre-existing and never block, new ones do.
# Stubs only; plain bash; writes only under $WORK.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SC="$ROOT/.claude/skills/agentic-delivery/scripts"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/dcr-test-train-rb.XXXXXX")"
trap '[ -n "$WORK" ] && rm -r "$WORK" 2>/dev/null' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null PERUN_HEAVY_DIR="$WORK/hv/heavy"
pass=0 fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; pass=$((pass + 1)); else echo "FAIL  $2"; fail=$((fail + 1)); fi; }
R="$WORK/clone"; g() { git -C "$R" -c user.email=t@example.com -c user.name=T "$@"; }
git init -q --bare "$WORK/origin.git" -b main; git clone -q "$WORK/origin.git" "$R" 2>/dev/null
g commit -q --allow-empty -m base; g push -q origin HEAD:main; B=$(g rev-parse HEAD)
for n in 1 3; do g checkout -q -b "pr$n" "$B"; echo "$n" >"$R/f$n"; g add "f$n"; g commit -q -m "pr $n"; g push -q origin "pr$n:refs/pull/$n/head"; done
g checkout -q --detach "$B"; for n in 1 3; do g merge -q --no-ff -m "merge-train: #$n" "pr$n"; done; U13=$(g rev-parse HEAD)
mkdir -p "$WORK/bin"; cat >"$WORK/bin/gh" <<'STUB'
#!/usr/bin/env bash
case "$1 $2" in
  "pr view") case "$5" in headRefOid) v=H$3; echo "${!v}" ;; baseRefName) echo main ;; isDraft) echo false ;;
                mergeable) echo MERGEABLE ;; headRefName) echo br$3 ;; esac ;;
  "pr diff") echo changelog.d/x.md ;;
  "pr merge") echo "merged $3" >>"$WORK/merged.log"; echo "merged $3" ;;
esac
STUB
chmod +x "$WORK/bin/gh"; export PATH="$WORK/bin:$PATH" WORK B U13 H1=$(g rev-parse pr1) H3=$(g rev-parse pr3)
echo 'echo "GREEN base=$B union=$U13"' >"$WORK/verify.sh"
# bx is red on the base (always fails); nw fails only while a PR file is present (a new failure the union introduced)
cat >"$WORK/rerun.sh" <<'STUB'
# bx: red on the base; nw: fails only while a PR file is present; ad: a test the PR added (absent on the base: nonzero, no FAIL line)
# fl: fails once on the base then passes; hk: setup/hook crash (rc 125 path via FLAKE_SETUP_CMD)
case "$TEST" in
  bx) echo "FAIL bx"; exit 1 ;;
  nw) [ ! -e f1 ] && [ ! -e f3 ] || { echo "FAIL nw"; exit 1; } ;;
  ad) [ -e f1 ] || { echo "no such test: ad"; exit 1; }; echo "FAIL ad"; exit 1 ;;
  fl) [ -e fl.seen ] || { touch fl.seen; echo "FAIL fl"; exit 1; } ;;
esac
STUB
printf 'echo "FAIL bx"; echo "FAILURES 1"; exit 1\n' >"$WORK/b-base.sh"
printf 'echo "FAIL bx"; echo "FAIL nw"; echo "FAILURES 2"; exit 1\n' >"$WORK/b-new.sh"
printf 'echo "FAIL ad"; echo "FAILURES 1"; exit 1\n' >"$WORK/b-add.sh"
printf 'echo "FAIL fl"; echo "FAILURES 1"; exit 1\n' >"$WORK/b-flaky.sh"
printf 'echo crash; exit 1\n' >"$WORK/b-empty.sh"
printf 'echo "FAIL bx"; echo "FAILURES 3"; exit 1\n' >"$WORK/b-count.sh"
cd "$R" || exit 2
run() { VERIFY_CMD="bash $WORK/verify.sh" UNION_DIRS="$R" LOG_DIR="$WORK" BROWSER_CMD="bash $WORK/$1.sh" PUSH_WAIT_SECS=0 "${@:2}" bash "$SC/train_land.sh" t 1 3 2>&1; }
: >"$WORK/merged.log"
out=$(run b-base env RERUN_CMD="bash $WORK/rerun.sh"); rc=$?
[ $rc -eq 0 ] && grep -q '^BASE RED: 1 pre-existing: bx$' <<<"$out" && [ "$(sort "$WORK/merged.log" | tr '\n' ' ')" = "merged 1 merged 3 " ]
ok $? "train_land: union whose only failure is red on the base lands, printing BASE RED"
: >"$WORK/merged.log"
out=$(run b-new env RERUN_CMD="bash $WORK/rerun.sh"); rc=$?
[ $rc -eq 3 ] && grep -q '^BASE RED: 1 pre-existing: bx$' <<<"$out" && grep -q '^REAL nw$' <<<"$out" && ! grep -q 'REAL bx' <<<"$out" && [ ! -s "$WORK/merged.log" ]
ok $? "train_land: a new failure beside a pre-existing one still blocks (only bx is excused)"
out=$(run b-base env); rc=$?
[ $rc -eq 1 ] && grep -q '^BROWSER RED' <<<"$out" && grep -q 'hint: set RERUN_CMD' <<<"$out" && [ ! -s "$WORK/merged.log" ]
ok $? "train_land: without RERUN_CMD behavior is unchanged and the fix hint is printed"
blocked() { { [ $rc -eq 1 ] || [ $rc -eq 3 ]; } && [ ! -s "$WORK/merged.log" ]; }
rr="RERUN_CMD=bash $WORK/rerun.sh"
for c in add empty count; do
  : >"$WORK/merged.log"; rm -f "$R/fl.seen"; out=$(run b-$c env "$rr"); rc=$?
  blocked && { [ $c = count ] || ! grep -q '^BASE RED' <<<"$out"; }; ok $? "train_land: b-$c (added test absent on base / empty FAIL list / FAILURES count mismatch) is not excused and lands nothing"
done
rm -f "$R/fl.seen"; out=$(run b-flaky env "$rr"); ! grep -q '^BASE RED' <<<"$out"; ok $? "train_land: an id that passes on the base in most runs is not called pre-existing (flake triage handles it)"
: >"$WORK/merged.log"; out=$(run b-base env "$rr" FLAKE_SETUP_CMD=false); rc=$?
blocked && grep -q 'fresh store or FLAKE_SETUP_CMD failed' <<<"$out" && ! grep -q '^BASE RED' <<<"$out"; ok $? "train_land: a failing setup hook on the base re-run (rc 125) fails closed, never excused"
[ "$(g rev-parse HEAD)" = "$(g rev-parse origin/main)" ] && [ -z "$(g branch --show-current)" ]; ok $? "train_land: HEAD is detached back on origin/main after a blocked run"
printf 'echo "FAIL abc"; exit 1\n' >"$WORK/rr-abc.sh"
RERUN_CMD="bash $WORK/rr-abc.sh" bash "$SC/train_flake.sh" --base 'a.c' >/dev/null 2>&1; [ $? -eq 1 ]; ok $? "train_flake --base: id is a literal, 'a.c' does not match 'FAIL abc'"
RERUN_CMD="bash $WORK/rr-abc.sh" bash "$SC/train_flake.sh" --base abc >/dev/null 2>&1; ok $? "train_flake --base: exact id with FAIL line is pre-existing"
grep -q 'AFFECTED browser specs plus the smoke set, NEVER the full suite' "$SC/train_land.sh"; ok $? "train_land: header says BROWSER_CMD is affected specs + smoke, never the full suite"
echo "$pass passed, $fail failed"; [ "$fail" -eq 0 ]
