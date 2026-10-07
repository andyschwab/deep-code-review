#!/usr/bin/env bash
# Test: land-release.sh creates and pushes annotated tag vX.Y.Z to the remote. Temp bare remote, copy of this repo.
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
[ "$(git -C "$R" cat-file -t "v$exp")" = tag ]; ok $? "local tag v$exp is annotated"
[ "$(git -C "$WORK/origin.git" rev-parse "v$exp^{commit}")" = "$(g rev-parse HEAD)" ]; ok $? "remote has v$exp at the release commit"
exit $fail
