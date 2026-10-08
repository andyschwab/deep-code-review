#!/usr/bin/env bash
# Tests for merge-train resilience: flake re-run triage (train_flake.sh), the exclusive heavy lease while a gate runs
# (perun_policy.py + heavy_gate.py), and mkdir locks instead of pgrep/ps waits (_lock.sh). Every runner is a stub with an
# injected fail/pass sequence; gh is a PATH stub. Plain bash; writes only under $WORK and a private PERUN_HEAVY_DIR.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SC="$ROOT/.claude/skills/agentic-delivery/scripts"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/dcr-test-train-res.XXXXXX")"
trap '[ -n "$WORK" ] && rm -r "$WORK" 2>/dev/null' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null PERUN_HEAVY_DIR="$WORK/hv/heavy"
pass=0 fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; pass=$((pass + 1)); else echo "FAIL  $2"; fail=$((fail + 1)); fi; }

# --- (1) flake triage: RERUN_CMD pops the next result from $WORK/seq.<id> (P = pass, F = fail); empty = pass ---
cat >"$WORK/rerun.sh" <<'STUB'
f="$WORK/seq.$TEST"; r=$(head -c1 "$f" 2>/dev/null); tail -c +2 "$f" >"$f.n" 2>/dev/null; mv "$f.n" "$f" 2>/dev/null
echo "$TEST" >>"$WORK/reruns.log"; [ "$r" != F ]
STUB
export WORK; export RERUN_CMD="bash $WORK/rerun.sh"
printf 'FFP' >"$WORK/seq.real1"; printf 'FPP' >"$WORK/seq.flaky1"; printf 'PP' >"$WORK/seq.pass1"; printf 'F' >"$WORK/seq.base1"
printf 'real1\nflaky1\npass1\nbase1\n' >"$WORK/fails"; echo base1 >"$WORK/baseline"
out=$(bash "$SC/train_flake.sh" "$WORK/fails" "$WORK/baseline"); rc=$?
[ $rc -eq 1 ] && grep -q '^REAL real1$' <<<"$out" && grep -q '^FLAKE flaky1' <<<"$out" && grep -q '^FLAKE pass1' <<<"$out" \
  && ! grep -q base1 <<<"$out" && [ "$(grep -c '^real1$' "$WORK/reruns.log")" -eq 2 ] && ! grep -q '^base1$' "$WORK/reruns.log"
ok $? "flake triage: fail 2 of 3 is REAL (stops at 2), 1 of 3 is FLAKE, baseline ids are skipped"
printf 'FPP' >"$WORK/seq.flaky1"; echo flaky1 >"$WORK/fails1"
bash "$SC/train_flake.sh" "$WORK/fails1" >/dev/null; ok $? "flake triage: flakes only exits 0"

unset RERUN_CMD
# --- (2)+(1) train_land end to end: 3 PRs, #2 really breaks t2, t1 is a load flake ---
R="$WORK/clone"; g() { git -C "$R" -c user.email=t@example.com -c user.name=T "$@"; }
git init -q --bare "$WORK/origin.git" -b main; git clone -q "$WORK/origin.git" "$R" 2>/dev/null
g commit -q --allow-empty -m base; g push -q origin HEAD:main; B=$(g rev-parse HEAD)
for n in 1 2 3; do g checkout -q -b "pr$n" "$B"; echo "$n" >"$R/f$n"; g add "f$n"; g commit -q -m "pr $n"; g push -q origin "pr$n:refs/pull/$n/head"; done
mkunion() { g checkout -q --detach "$B"; for n in "$@"; do g merge -q --no-ff -m "merge-train: #$n" "pr$n"; done; g rev-parse HEAD; }
U123=$(mkunion 1 2 3); U13=$(mkunion 1 3); export B U123 U13
export H1=$(g rev-parse pr1) H3=$(g rev-parse pr3) H2=$(g rev-parse pr2)
mkdir -p "$WORK/bin"; cat >"$WORK/bin/gh" <<'STUB'
#!/usr/bin/env bash
case "$1 $2" in
  "pr view") case "$5" in headRefOid) v=H$3; echo "${!v}" ;; baseRefName) echo main ;; isDraft) echo false ;;
                mergeable) echo MERGEABLE ;; headRefName) echo br$3 ;; esac ;;
  "pr diff") echo changelog.d/x.md ;;
  "pr merge") echo "merged $3" >>"$WORK/merged.log"; echo "merged $3" ;;
esac
STUB
chmod +x "$WORK/bin/gh"; export PATH="$WORK/bin:$PATH"
cat >"$WORK/verify.sh" <<'STUB'
# args: tag prs...; the gate probes the heavy lease while it runs
echo '{"tool_input":{"command":"pytest tests"}}' | python3 "$SC/heavy_gate.py" >>"$WORK/gate-during.log"
case " $* " in *" 2 "*) echo "GREEN base=$B union=$U123" ;; *) echo "GREEN base=$B union=$U13" ;; esac
STUB
cat >"$WORK/browser.sh" <<'STUB'
if [ "$UNION_SHA" = "$U123" ]; then echo "FAIL t1"; echo "FAIL t2"; exit 1; fi; exit 0
STUB
cat >"$WORK/rerun2.sh" <<'STUB'
# t1: load flake (fails once, then passes); t2: fails whenever PR #2's file is present in this checkout
if [ "$TEST" = t1 ]; then [ -e "$WORK/t1.seen" ] || { touch "$WORK/t1.seen"; exit 1; }; exit 0; fi
[ ! -e f2 ]
STUB
export SC; : >"$WORK/gate-during.log"
cd "$R" || exit 2
run() { VERIFY_CMD="bash $WORK/verify.sh \"\$@\"" UNION_DIRS="$R" LOG_DIR="$WORK" BROWSER_CMD="bash $WORK/browser.sh" "$@" bash "$SC/train_land.sh" tt 1 2 3 2>&1; }
out=$(RERUN_CMD="bash $WORK/rerun2.sh" run env); rc=$?
[ $rc -eq 0 ] && grep -q '^FLAKE t1' <<<"$out" && grep -q '^REAL t2$' <<<"$out" && grep -q '^DROP #2 ' <<<"$out" && ! grep -q 'DROP #[13]' <<<"$out"
ok $? "train_land: flake reported, real failure bisected to #2, #2 dropped, rest re-verified"
[ "$(sort "$WORK/merged.log" | tr '\n' ' ')" = "merged 1 merged 3 " ]; ok $? "train_land: lands #1 and #3 only"
grep -q 'gate running: wait' "$WORK/gate-during.log"; ok $? "heavy_gate: denies heavy commands with 'gate running: wait' while the train gate runs"
[ -z "$(echo '{"tool_input":{"command":"pytest tests"}}' | PERUN_GATE_LOAD1=0 PERUN_GATE_CORES=8 PERUN_GATE_FREE_RAM_PCT=80 python3 "$SC/heavy_gate.py")" ]
ok $? "heavy_gate: allows again once the train exits (exclusive lease released)"
: >"$WORK/merged.log"
out=$(run env); rc=$?  # no RERUN_CMD: stays all-or-nothing
[ $rc -eq 1 ] && grep -q 'BROWSER RED' <<<"$out" && [ ! -s "$WORK/merged.log" ]; ok $? "train_land: without RERUN_CMD a red browser gate lands nothing"
mkdir -p "$WORK/hv"; echo "$$ $(date +%s)" >"$WORK/hv/heavy.exclusive"
out=$(run env); rc=$?
[ $rc -eq 1 ] && grep -q 'exclusive heavy lease' <<<"$out"; ok $? "train_land: a second gate is refused while another holds the exclusive lease"
rm -f "$WORK/hv/heavy.exclusive"

# --- (2) one serial push queue: a live holder of the push lock stops the landing, never lands in parallel ---
PQ="$R/.git/train-push.lock"; mkdir "$PQ"; echo $$ >"$PQ/pid"; date +%s >"$PQ/ts"
out=$(VERIFY_CMD="bash $WORK/verify.sh \"\$@\"" UNION_DIRS="$R" LOG_DIR="$WORK" BROWSER_CMD=skip PUSH_WAIT_SECS=0 bash "$SC/train_land.sh" t9 1 3 2>&1); rc=$?
[ $rc -eq 1 ] && grep -q "lock held by pid $$" <<<"$out" && [ ! -s "$WORK/merged.log" ]; ok $? "push queue: a held push lock blocks landing"
rm -f "$PQ/pid" "$PQ/ts"; rmdir "$PQ"

# --- (3) mkdir lock: atomic, stale only when old AND holder dead, never auto-deleted otherwise; no pgrep/ps ---
. "$SC/_lock.sh"; L="$WORK/l.lock"; (:) & DEAD=$!; wait $DEAD
lock_take "$L" 30 0 && [ "$(cat "$L/pid")" = $$ ]; ok $? "lock: first take wins and records pid + timestamp"
lock_take "$L" 30 0 2>/dev/null; [ $? -eq 1 ]; ok $? "lock: second take is refused while held"
lock_drop "$L"; [ ! -e "$L" ]; ok $? "lock: drop releases"
mkdir "$L"; echo "$DEAD" >"$L/pid"; echo $(( $(date +%s) - 60 )) >"$L/ts"
lock_take "$L" 30 0 2>/dev/null; [ $? -eq 1 ] && [ -d "$L" ]; ok $? "lock: young lock with a dead pid is not reclaimed"
echo $(( $(date +%s) - 3600 )) >"$L/ts"
out=$(lock_take "$L" 30 0 2>&1); rc=$?
[ $rc -eq 0 ] && grep -q "STALE-LOCK.*reclaimed" <<<"$out" && [ "$(cat "$L/pid")" = $$ ]; ok $? "lock: old lock with a dead pid is reclaimed and reported"
lock_drop "$L"; mkdir "$L"; echo $$ >"$L/pid"; echo $(( $(date +%s) - 3600 )) >"$L/ts"
out=$(lock_take "$L" 30 0 2>&1); rc=$?
[ $rc -eq 1 ] && grep -q "pid $$ is alive; not deleted" <<<"$out" && [ -d "$L" ]; ok $? "lock: old lock with a live pid is reported, never deleted"
! grep -nE '\b(pgrep|pkill)\b|\bps +-' "$SC/_lock.sh" "$SC/train_land.sh" "$SC/land_train.sh" "$SC/train_flake.sh"; ok $? "train scripts: no pgrep/ps-based waiting"

echo "$pass passed, $fail failed"; [ "$fail" -eq 0 ]
