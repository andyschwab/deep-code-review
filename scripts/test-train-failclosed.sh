#!/usr/bin/env bash
# Tests that train test-result parsing fails closed: a missing failed-ids list is not "no failures" (train_flake.sh),
# and a GREEN log line from a verify step that exited non-zero is not a pass (train_land.sh). Plain bash; writes under $WORK.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SC="$ROOT/.claude/skills/agentic-delivery/scripts"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/dcr-test-train-fc.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
pass=0 fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; pass=$((pass + 1)); else echo "FAIL  $2"; fail=$((fail + 1)); fi; }

out=$(RERUN_CMD=true bash "$SC/train_flake.sh" "$WORK/nope" 2>&1); rc=$?
[ $rc -eq 2 ] && grep -q "could not check" <<<"$out"; ok $? "train_flake: missing failed-ids file exits 2 (not 0)"
: >"$WORK/empty"; RERUN_CMD=true bash "$SC/train_flake.sh" "$WORK/empty" >/dev/null 2>&1; ok $? "train_flake: present empty list still exits 0"

R="$WORK/r"; git init -q --bare "$WORK/o.git" -b main; git clone -q "$WORK/o.git" "$R" 2>/dev/null
git -C "$R" -c user.email=t@example.com -c user.name=T commit -q --allow-empty -m base; git -C "$R" push -q origin HEAD:main
mkdir "$WORK/bin"; printf '#!/usr/bin/env bash\ncase "$1 $2" in "pr view") echo main ;; esac\n' >"$WORK/bin/gh"; chmod +x "$WORK/bin/gh"
cd "$R" || exit 2
out=$(PATH="$WORK/bin:$PATH" GH="$WORK/bin/gh" VERIFY_CMD='echo "GREEN base=aaa union=bbb"; exit 137' UNION_DIRS="$R" LOG_DIR="$WORK" bash "$SC/train_land.sh" t1 1 2 2>&1); rc=$?
[ $rc -eq 3 ] && grep -q "could not check: verify printed GREEN but exited rc=137" <<<"$out"; ok $? "train_land: GREEN line with non-zero verify rc lands nothing (exit 3)"
echo "failclosed: $pass passed, $fail failed"; [ "$fail" -eq 0 ]
