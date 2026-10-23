#!/usr/bin/env bash
# Tests for train_land.sh's disjoint fast path: PRs sharing no path and at most one generated file land back-to-back with no
# union proof (VERIFY_CMD never runs); any overlap, a shared generated file, a gh failure or TRAIN_UNION=always runs the union gate.
# Plain bash; gh is a PATH stub. Writes only under $WORK.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SC="$ROOT/.claude/skills/agentic-delivery/scripts"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/dcr-test-train-disjoint.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
pass=0 fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; pass=$((pass + 1)); else echo "FAIL  $2"; fail=$((fail + 1)); fi; }
g() { git -C "$R" -c user.email=t@example.com -c user.name=T "$@"; }

git init -q --bare "$WORK/origin.git" -b main
R="$WORK/clone"; git clone -q "$WORK/origin.git" "$R" 2>/dev/null
mkdir -p "$R/scripts"; cp "$ROOT/scripts/land-release.sh" "$R/scripts/"; g add scripts; g commit -q -m base; g push -q origin HEAD:main
B=$(g rev-parse HEAD)
for n in 1 2; do g checkout -q -b "pr$n" "$B"; echo "$n" >"$R/f$n"; g add "f$n"; g commit -q -m "pr $n"; done
g checkout -q --detach "$B"

STUB="$WORK/stub"; mkdir -p "$STUB/bin"
cat >"$STUB/bin/gh" <<'STUBEOF'
#!/usr/bin/env bash
echo "gh $*" >>"$STUB/calls.log"
n=$3
case "$1 $2" in
  "pr view") f=${5#.}; case $f in headRefName) echo "br$n";; headRefOid) echo "head$n";; baseRefName) echo main;; mergeable) echo MERGEABLE;; isDraft) echo false;; esac ;;
  "pr diff") [ ! -e "$STUB/diff-fails" ] || exit 1; cat "$STUB/files.$n" ;;
  "pr list") ;;
  "pr merge") echo "merged $n" ;;
esac
STUBEOF
chmod +x "$STUB/bin/gh"
export STUB PATH="$STUB/bin:$PATH"
cd "$R" || exit 2

run() { # run <files-of-1> <files-of-2> [env...]: verify marker lands in $WORK/verified; output in $out
  echo "$1" >"$STUB/files.1"; echo "$2" >"$STUB/files.2"; : >"$STUB/calls.log"; : >"$WORK/verified"
  out=$(env "${@:3}" VERIFY_CMD='echo ran >>'"$WORK"'/verified; echo RED; exit 1' UNION_DIRS="$R" LOG_DIR="$WORK" BACKFILL_FILE="$WORK/b.txt" WAIT_SECS=0 \
    bash "$SC/train_land.sh" t 1 2 2>&1); rc=$?
}

run $'src/a.py\nchangelog.d/a.md' $'src/b.py\nchangelog.d/b.md' X=1
[ $rc -eq 0 ] && [ ! -s "$WORK/verified" ] && grep -q "no union proof" <<<"$out" && grep -q "pr merge 1 --merge --match-head-commit head1" "$STUB/calls.log" \
  && grep -q "pr merge 2 --merge --match-head-commit head2" "$STUB/calls.log"; ok $? "disjoint PRs land back-to-back at their heads, VERIFY_CMD never runs"
run src/a.py $'src/a.py\nsrc/b.py' X=1
[ -s "$WORK/verified" ] && ! grep -q "pr merge" "$STUB/calls.log"; ok $? "a shared path runs the union gate (RED lands nothing)"
run .claude/skills/x/INDEX.md .claude/skills/y/INDEX.md X=1
[ -s "$WORK/verified" ]; ok $? "two PRs touching generated files (land-release.sh GENERATED) run the union gate"
run .claude/skills/x/SKILL.md .claude/skills/y/SKILL.md X=1
[ ! -s "$WORK/verified" ]; ok $? "skill prose is not generated: disjoint skill edits land back-to-back"
run docs/INDEX.md src/b.py X=1
[ ! -s "$WORK/verified" ] && grep -q "pr merge 2" "$STUB/calls.log"; ok $? "one PR touching a generated file is still disjoint"
touch "$STUB/diff-fails"; run src/a.py src/b.py X=1
[ -s "$WORK/verified" ]; ok $? "a failing gh pr diff falls through to the union gate"
rm -f "$STUB/diff-fails"
run src/a.py src/b.py TRAIN_UNION=always
[ -s "$WORK/verified" ]; ok $? "TRAIN_UNION=always forces the union gate"

g rm -q scripts/land-release.sh; g commit -q -m rm; g push -q origin HEAD:main
run src/a.py src/b.py X=1
[ -s "$WORK/verified" ]; ok $? "no land-release.sh (generated list unknown) falls through to the union gate"

echo "Tests: $pass/$((pass + fail))"
[ "$fail" -eq 0 ]
