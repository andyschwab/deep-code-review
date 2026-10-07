#!/usr/bin/env bash
# Tests for the must-load floor cut (#1343): moved sections stay present and routed, INDEX carries no Headings column.
# Plain bash; read-only. Prints PASS/FAIL lines; exits non-zero on any failure.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
D="$ROOT/.claude/skills/deep-code-review"
fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; else echo "FAIL  $2"; fail=1; fi; }

for h in 'Switch/case control flow' 'Hand-rolled parsing' 'Composed numeric bounds' 'Partition / segmentation validity'; do
  grep -q "^## $h" "$D/references/redflags-situational.md" && ! grep -q "^## $h" "$D/references/language-stack-redflags.md"
  ok $? "section '$h' moved to redflags-situational.md, not duplicated in the floor"
done
grep -q '^\*\*Phase 5' "$D/references/method-report.md" && grep -q '^\*\*Phase 6' "$D/references/method-report.md" \
  && ! grep -q '^\*\*Phase 6 — Imprint standards' "$D/references/method.md"
ok $? "Phase 5/6 procedure lives in method-report.md only"
for r in redflags-situational.md method-report.md; do
  grep -qF "\`$r\`" "$D/SKILL.md" && sed -n 3p "$D/references/$r" | grep -q '^Read this when'
  ok $? "$r is routed from SKILL.md and carries a Read-this-when trigger"
done
grep -qF '`redflags-situational.md` when' "$D/SKILL.md" && grep -q '^phase-conditional.redflags-situational.md$' "$ROOT/scripts/mustload-budgets.tsv"
ok $? "redflags-situational.md is a pinned conditional floor ref"
! grep -q 'Headings' "$D/INDEX.md" "$ROOT/.claude/skills/agentic-delivery/INDEX.md"
ok $? "INDEX.md files carry no Headings column"
exit $fail
