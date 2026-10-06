#!/usr/bin/env bash
# Loop templates (#1332): every script a templates/loops/*.md file names exists, every loop is >= 20 min
# (no tighter interval anywhere), the three templates ship via install.sh --with-delivery, and SKILL.md
# routes them. Exit non-zero on any failure.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
L="$ROOT/.claude/skills/agentic-delivery/templates/loops"
fail=0
bad() { echo "FAIL: $*" >&2; fail=1; }

for n in coordinator peer cleanup; do [ -f "$L/$n.md" ] || bad "missing $n.md"; done

# every named script exists
while read -r s; do
  [ -f "$ROOT/.claude/skills/agentic-delivery/scripts/$s" ] || bad "referenced script missing: $s"
done < <(grep -ohE '[a-z_]+\.(sh|py)\b' "$L"/*.md | sort -u)

# no /loop interval or schedule under 20 minutes
while read -r m; do
  [ "$m" -ge 20 ] || bad "interval ${m}m under 20-minute floor"
done < <(grep -ohE '(/loop|every) [0-9]+ ?m' "$L"/*.md | grep -oE '[0-9]+')
grep -qE '/loop [0-9]+s|every [0-9]+ ?(s|sec)' "$L"/*.md && bad "seconds-level interval"

# installed by --with-delivery
dest="$(mktemp -d)"
trap 'rm -rf "$dest"' EXIT
bash "$ROOT/install.sh" --with-delivery "$dest" >/dev/null 2>&1
for n in coordinator peer cleanup; do
  [ -f "$dest/.claude/skills/agentic-delivery/templates/loops/$n.md" ] || bad "install.sh did not land loops/$n.md"
done

# routed
grep -q 'templates/loops/' "$ROOT/.claude/skills/agentic-delivery/SKILL.md" || bad "SKILL.md does not route templates/loops/"
grep -q 'templates/loops/' "$ROOT/.claude/skills/agentic-delivery/references/operating-discipline.md" || bad "operating-discipline.md does not route templates/loops/"

[ "$fail" -eq 0 ] && echo "loop templates: ok"
exit "$fail"
