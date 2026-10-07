#!/usr/bin/env bash
# Test: tagging happens only after the release commit is on origin/main (`land-release.sh tag`), never at land time;
# an existing local tag is skipped, not fatal. Temp bare remote, copy of this repo.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/dcr-test-tag.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null RELEASE_DATE=2026-01-01
fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; else echo "FAIL  $2"; fail=1; fi; }
R="$WORK/repo"; mkdir "$R"
g() { git -C "$R" -c user.email=t@example.com -c user.name=T "$@"; }
git init -q --bare -b main "$WORK/origin.git"
rsync -a --exclude=.git --exclude=.claude/worktrees --exclude=changelog.d "$ROOT/" "$R/"
git -C "$R" init -q -b main; g remote add origin "$WORK/origin.git"
g add -A; g commit -q -m base; g push -q origin main
V0=$(cat "$R/.claude/skills/deep-code-review/VERSION"); exp="${V0%%.*}.$(( $(echo "$V0" | cut -d. -f2) + 1)).0"
g checkout -q -b lane main
mkdir "$R/changelog.d"; printf '### Added\n- tag test.\n' >"$R/changelog.d/t.md"
g add -A; g commit -q -m lane
(cd "$R" && bash scripts/land-release.sh) >/dev/null; ok $? "land succeeds"
[ -z "$(git -C "$R" tag -l "v$exp")" ] && [ -z "$(git -C "$WORK/origin.git" tag -l "v$exp")" ]; ok $? "land creates no tag"
(cd "$R" && bash scripts/land-release.sh tag) >/dev/null 2>&1; [ $? -ne 0 ]; ok $? "tag before the release is on origin/main is refused"
[ -z "$(git -C "$WORK/origin.git" tag -l)" ] || [ -z "$(git -C "$WORK/origin.git" tag -l "v$exp")" ]; ok $? "nothing pushed by the refused tag"
g push -q origin HEAD:main
(cd "$R" && bash scripts/land-release.sh tag) >/dev/null; ok $? "tag after merge succeeds"
[ "$(git -C "$R" cat-file -t "v$exp")" = tag ]; ok $? "local tag v$exp is annotated"
[ "$(git -C "$WORK/origin.git" rev-parse "v$exp^{commit}")" = "$(g rev-parse HEAD)" ]; ok $? "remote has v$exp at the release commit"
out=$(cd "$R" && bash scripts/land-release.sh tag 2>&1); rc=$?
[ $rc -eq 0 ] && grep -q "already exists locally; skipping" <<<"$out"; ok $? "existing local tag is skipped with a message, exit 0"
g tag -d "v$exp" >/dev/null; git -C "$WORK/origin.git" tag -d "v$exp" >/dev/null
g tag "v$exp" "$(g rev-parse HEAD~1)"   # stale local tag on the wrong commit
(cd "$R" && bash scripts/land-release.sh tag) >/dev/null 2>&1; [ $? -ne 0 ]; ok $? "local tag on a different commit is refused"
exit $fail
