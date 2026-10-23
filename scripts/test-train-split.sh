#!/usr/bin/env bash
# Tests for train_land.sh TRAIN_SPLIT_DEPTH: a red train whose culprit cannot be attributed (the pair 3+4 only fails together, each passes alone)
# splits into halves; each half re-runs the full gate STACKED on the base the previous half left and lands only when its own gate is GREEN;
# leaves keep CANT. The fake gate builds real unions on the bare origin's current main, and a landing (the gh stub) advances that main.
# Plain bash; writes only under $WORK. Env knobs read by the stubs: RED (a PR set whose gate is red), CFLAG (PR 1 breaks t2), ALLRED,
# FAILMERGE (a PR whose merge fails), AGEIT (verify ages the lease), HOLDPID (a merge leaves the lease held by that pid).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SC="$ROOT/.claude/skills/agentic-delivery/scripts"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/dcr-test-trainsplit.XXXXXX")"
trap '[ -n "$WORK" ] && rm -r "$WORK" 2>/dev/null' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null PERUN_HEAVY_DIR="$WORK/hv/heavy" WORK SC
pass=0 fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; pass=$((pass + 1)); else echo "FAIL  $2"; fail=$((fail + 1)); fi; }

R="$WORK/clone" O="$WORK/origin.git"; g() { git -C "$R" -c user.email=t@example.com -c user.name=T "$@"; }
git init -q --bare "$O" -b main; git clone -q "$O" "$R" 2>/dev/null
g commit -q --allow-empty -m base; g push -q origin HEAD:main; B=$(g rev-parse HEAD)
for n in 1 2 3 4; do g checkout -q -b "pr$n" "$B"; echo "$n" >"$R/f$n"; g add "f$n"; g commit -q -m "pr $n"; g push -q origin "pr$n:refs/pull/$n/head"; done
for n in 1 2 3 4; do export "H$n=$(g rev-parse "pr$n")"; done
mkdir -p "$WORK/bin"; cat >"$WORK/bin/gh" <<'STUB'
#!/usr/bin/env bash
case "$1 $2" in
  "pr view") case "$5" in headRefOid) v=H$3; echo "${!v}" ;; baseRefName) echo main ;; isDraft) echo false ;;
                mergeable) echo MERGEABLE ;; headRefName) echo br$3 ;; esac ;;
  "pr diff") echo changelog.d/x.md ;;
  "pr merge") [ "${FAILMERGE:-}" != "$3" ] || exit 1
    echo "$3" >>"$WORK/merged.log"
    # a landing moves origin/main (one commit per PR), so the next half must stack on it
    p=$(git -C "$WORK/origin.git" rev-parse main); t=$(git -C "$WORK/origin.git" rev-parse 'main^{tree}')
    git -C "$WORK/origin.git" update-ref refs/heads/main "$(git -C "$WORK/origin.git" -c user.email=t@example.com -c user.name=T commit-tree "$t" -p "$p" -m "land #$3")"
    [ -z "${HOLDPID:-}" ] || echo "$HOLDPID $(date +%s)" >"$WORK/hv/heavy.exclusive" ;;
esac
STUB
chmod +x "$WORK/bin/gh"; export PATH="$WORK/bin:$PATH"
# Fake full gate: a union of the PRs on the CURRENT origin/main (logged with its base); RED=<set> is red for exactly that set.
cat >"$WORK/verify.sh" <<'V'
shift
gi() { git -c user.email=t@example.com -c user.name=T -c commit.gpgsign=false "$@"; }
gi fetch -q origin main; gi checkout -q --detach origin/main
cur=$(git rev-parse --short HEAD); echo "$* base=$cur" >>"$WORK/gates.log"
[ -z "${AGEIT:-}" ] || python3 -c 'import os,sys,time;t=time.time()-3600;os.utime(sys.argv[1],(t,t))' "$WORK/hv/heavy.exclusive"
[ "${RED:-}" != "$*" ] || { echo RED; exit 1; }
for n in "$@"; do gi merge -q --no-ff -m "merge-train: #$n" "pr$n" >/dev/null || exit 1; done
echo "GREEN base=$cur union=$(git rev-parse --short HEAD)"
V
# Browser: t1 is red on any union holding 3 and 4 together; CFLAG: t2 is red on any union holding 1. A green run records the lease age.
cat >"$WORK/browser.sh" <<'BR'
[ -z "${ALLRED:-}" ] || exit 1
n=0
if [ -n "${CFLAG:-}" ] && [ -e f1 ]; then echo "FAIL t2"; n=$((n + 1)); fi
if [ -e f3 ] && [ -e f4 ]; then echo "FAIL t1"; n=$((n + 1)); fi
[ "$n" -eq 0 ] || { echo "FAILURES $n"; exit 1; }
python3 -c 'import os,sys,time;print(int(time.time()-os.path.getmtime(sys.argv[1])))' "$WORK/hv/heavy.exclusive" >>"$WORK/age.log" 2>/dev/null
exit 0
BR
# Solo re-runs: t1 re-fails whenever 3 and 4 are both present (REAL at the union, passes alone per PR: no culprit can be pinned); t2 whenever 1 is.
cat >"$WORK/rerun.sh" <<'RR'
case "$TEST" in t2) [ ! -e f1 ] ;; *) [ ! -e f3 ] || [ ! -e f4 ] ;; esac
RR
# Flaky t1: on the union (f1 present) it pops $WORK/useq, on the base $WORK/bseq; F = fail.
cat >"$WORK/rerun_seq.sh" <<'RR'
f=$WORK/useq; [ -e f1 ] || f=$WORK/bseq
r=$(head -c1 "$f"); tail -c +2 "$f" >"$f.n"; mv "$f.n" "$f"; [ "$r" != F ] || { echo "FAIL $TEST"; exit 1; }
RR
cd "$R" || exit 2
run() { git -C "$O" update-ref refs/heads/main "$B"; : >"$WORK/merged.log"; : >"$WORK/gates.log"; : >"$WORK/age.log"
  VERIFY_CMD="bash $WORK/verify.sh \"\$@\"" UNION_DIRS="$R" LOG_DIR="$WORK" BROWSER_CMD="bash $WORK/browser.sh" RERUN_CMD="bash ${RERUN:-$WORK/rerun.sh}" FLAKE_RUNS=3 \
    bash "$SC/train_land.sh" tt ${PRSARG:-1 2 3 4} 2>&1; }
landed() { sort "$WORK/merged.log" | tr '\n' ' '; }
base_of() { sed -nE "s/^$1 base=//p" "$WORK/gates.log" | tail -1; }  # the base a gate of exactly this PR set was built on

# (1) depth 0: the old behavior, CANT with nothing landed
out=$(TRAIN_SPLIT_DEPTH=0 run); rc=$?
[ $rc -eq 3 ] && grep -q '^CANT: no culprit pinned' <<<"$out" && ! grep -q 'SPLIT' <<<"$out" && [ ! -s "$WORK/merged.log" ]
ok $? "train_land: TRAIN_SPLIT_DEPTH=0 keeps CANT, nothing landed"
# (2) depth 1: green half {1,2} lands, bad half {3,4} is a CANT leaf; the run exits 3 because #3 #4 are unlanded
out=$(TRAIN_SPLIT_DEPTH=1 run); rc=$?
[ $rc -eq 3 ] && grep -q '^SPLIT: no culprit pinned' <<<"$out" && grep -q '^CANT leaf #3 4' <<<"$out" \
  && grep -q '^SPLIT done: landed #1 2; CANT (not landed) #3 4; gates=3$' <<<"$out" && [ "$(landed)" = "1 2 " ]
ok $? "train_land: unattributed red splits, the green half lands, the bad half's leaf is reported, exit 3"
# (3) stacking: both first-level gates ran on the original base; the later half ran on the main the landing left (not the stale one)
x=$(base_of "1 2 3 4"); [ -n "$x" ] && [ "$(base_of '1 2')" = "$x" ] && [ "$(base_of '3 4')" != "$x" ] && [ "$(base_of '3 4')" = "$(git -C "$O" rev-parse --short main)" ]
ok $? "train_land: a later half is gated on the base the previous landing left (stacked), not the stale one"
# (4) default depth 2: the bad half splits again; {3} alone is red (leaf CANT), {4} alone is green and lands
out=$(RED=3 run); rc=$?
[ $rc -eq 3 ] && grep -q '^CANT leaf #3:' <<<"$out" && grep -q '^SPLIT done: landed #1 2 4; CANT (not landed) #3; gates=5$' <<<"$out" && [ "$(landed)" = "1 2 4 " ]
ok $? "train_land: a red half splits again (default depth 2) down to the single-PR leaf"
# (5) a culprit dropped inside the first pass (#1 breaks t2 alone) is reported as not landed; the rest still split and land
out=$(CFLAG=1 run); rc=$?
[ $rc -eq 3 ] && grep -q '^DROP #1' <<<"$out" && grep -q '^SPLIT done: landed #2 3 4; CANT (not landed) #1; gates=5$' <<<"$out" && [ "$(landed)" = "2 3 4 " ]
ok $? "train_land: a culprit dropped before the split is reported not landed (landed = what land_train merged)"
# (6) a merge failing mid-split: the report names what really landed, the split stops, exit is land_train's 1
out=$(FAILMERGE=2 run); rc=$?
[ $rc -eq 1 ] && grep -q '^SPLIT done: landed #1; CANT (not landed) #2 3 4; gates=2$' <<<"$out" && [ "$(landed)" = "1 " ]
ok $? "train_land: a land failure mid-split still prints SPLIT done with the true landed set and exits non-zero"
# (7) the lease taken by another gate while the first half lands: the later half waits (LEASE_WAIT_SECS=0 -> DEFER, exit 4) and the split stops
sleep 60 & hp=$!
out=$(HOLDPID=$hp LEASE_WAIT_SECS=0 run); rc=$?; kill "$hp" 2>/dev/null; rm -f "$WORK/hv/heavy.exclusive"
[ $rc -eq 4 ] && grep -q '^DEFER: ' <<<"$out" && grep -q '^SPLIT done: landed #1 2; CANT (not landed) #3 4; gates=2$' <<<"$out" && [ "$(landed)" = "1 2 " ]
ok $? "train_land: a later half redoes the lease wait; a held lease aborts the split with exit 4 and a report"
# (8) FLAKY-only red (fails 2 of 3 solo runs, never on the base): the old CANT result, never a split
printf FFP >"$WORK/useq"; printf PPPP >"$WORK/bseq"
out=$(RERUN=$WORK/rerun_seq.sh run); rc=$?
[ $rc -eq 3 ] && grep -q '^FLAKE t1' <<<"$out" && grep -q '^CANT: flake t1 never fails on the base' <<<"$out" && ! grep -q 'SPLIT' <<<"$out" && [ ! -s "$WORK/merged.log" ]
ok $? "train_land: a flaky-only red keeps FLAKE/CANT and never splits"
# (9) a non-numeric depth fails closed: warning, no split
out=$(TRAIN_SPLIT_DEPTH=abc run); rc=$?
[ $rc -eq 3 ] && grep -q "^WARN: TRAIN_SPLIT_DEPTH='abc' is not a number; splitting disabled" <<<"$out" && ! grep -q '^SPLIT' <<<"$out" && [ ! -s "$WORK/merged.log" ]
ok $? "train_land: a non-numeric TRAIN_SPLIT_DEPTH warns and disables splitting"
# (10) the lease is renewed from the train's subshell: verify ages it 1h, the browser step (after a renew) must see it fresh
out=$(AGEIT=1 PRSARG="1 2" run); rc=$?
[ $rc -eq 0 ] && [ "$(landed)" = "1 2 " ] && [ "$(wc -l <"$WORK/age.log" | tr -d ' ')" = 1 ] && [ "$(cat "$WORK/age.log")" -lt 600 ]
ok $? "train_land: heavy-exclusive-renew from the train subshell refreshes the lease"
# (12) PERUN_HOLDER_PID names only an ancestor within two hops: it cannot release, renew or take a lease held by another process, and a bad value falls back to the caller
PY="$SC/perun_policy.py" LF="$WORK/hv/heavy.exclusive"
age() { python3 -c 'import os,sys,time;print(int(time.time()-os.path.getmtime(sys.argv[1])))' "$LF"; }
old() { python3 -c 'import os,sys,time;t=time.time()-3600;os.utime(sys.argv[1],(t,t))' "$LF"; }
sleep 60 & fp=$!; echo "$fp $(date +%s)" >"$LF"; old; s=0
for v in $fp 0 -1 abc; do
  PERUN_HOLDER_PID=$v python3 "$PY" heavy-exclusive-release >/dev/null 2>&1; PERUN_HOLDER_PID=$v python3 "$PY" heavy-exclusive-renew >/dev/null 2>&1
  PERUN_HOLDER_PID=$v python3 "$PY" heavy-exclusive >/dev/null 2>&1 && s=1  # must stay HELD (rc 1), never a steal
done
[ "$s" -eq 0 ] && [ "$(cut -d' ' -f1 "$LF")" = "$fp" ] && [ "$(age)" -gt 1000 ]
ok $? "perun_policy: PERUN_HOLDER_PID (foreign pid, 0, -1, text) cannot release, renew or steal another process's lease"
kill "$fp" 2>/dev/null; rm -f "$LF"; s=0
for v in 0 -1 abc; do
  o=$(PERUN_HOLDER_PID=$v python3 "$PY" heavy-exclusive 2>/dev/null) && [ "$o" -gt 0 ] 2>/dev/null && [ "$(cut -d' ' -f1 "$LF")" = "$o" ] || s=1; rm -f "$LF"
done
ok $s "perun_policy: a bad PERUN_HOLDER_PID falls back to the caller's pid (never 0, -1 or a failure)"
e=$(PERUN_HOLDER_PID=1 python3 "$PY" heavy-exclusive 2>&1 >/dev/null); rm -f "$LF"
case $e in *"ignoring PERUN_HOLDER_PID='1'"*) s=0;; *) s=1;; esac
ok $s "perun_policy: a rejected PERUN_HOLDER_PID (pid 1) warns on stderr"
e=$(sh -c 'PERUN_HOLDER_PID=$$ python3 "$0" heavy-exclusive >/dev/null; :' "$PY" 2>&1); rm -f "$LF"  # python's direct parent is this sh, so hp == ppid exactly (not the grandparent branch)
[ -z "$e" ]
ok $? "perun_policy: PERUN_HOLDER_PID equal to the direct parent (valid) prints no warning"
python3 "$PY" heavy-exclusive >/dev/null; old
( python3 "$PY" heavy-exclusive-renew; true ); a1=$(age)
( PERUN_HOLDER_PID=$$ python3 "$PY" heavy-exclusive-renew; true ); a2=$(age)
[ "$a1" -gt 1000 ] && [ "$a2" -lt 100 ]
ok $? "perun_policy: PERUN_HOLDER_PID=<ancestor> renews from a subshell; the same call without it does not"
python3 "$PY" heavy-exclusive-release; rm -f "$LF"
# (11) nothing green anywhere: exits non-zero, lands nothing
out=$(ALLRED=1 TRAIN_SPLIT_DEPTH=1 run); rc=$?
[ $rc -ne 0 ] && [ ! -s "$WORK/merged.log" ]
ok $? "train_land: every half red lands nothing and exits non-zero"
[ ! -e "$(git rev-parse --git-dir)/train-land.lock" ]; ok $? "train_land: lock released after a split run"

echo "$pass passed, $fail failed"; [ "$fail" -eq 0 ]
