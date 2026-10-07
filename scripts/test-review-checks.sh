#!/usr/bin/env bash
# Tests for .claude/skills/deep-code-review/scripts/review_checks.sh: a throwaway git repo holds files with
# known defects; each installed analyzer must flag them, clean files must stay silent, a missing tool must be
# a "not run" line (not a failure), and the output must score through scripts/score_review.py.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RC="$ROOT/.claude/skills/deep-code-review/scripts/review_checks.sh"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
fail=0
ok() { printf 'ok   %s\n' "$1"; }
bad() { printf 'FAIL %s\n' "$1"; fail=1; }

cd "$T"
git init -q . && git -c user.email=t@example.com -c user.name=t commit -q --allow-empty -m base
git branch base
printf '#!/bin/bash\nfor f in $(ls); do rm $f; done\n' >bad.sh
printf '#!/bin/bash\nif [ 1 = 1 ]; then\n' >syntax.sh
printf 'import os\ndef f(:\n' >syntax.py
printf 'import os\nx = 1\n' >unused.py
printf '{"a": 1,}\n' >bad.json
printf 'let = = 1;\n' >bad.js
printf '#!/usr/bin/env bash\necho "ok"\n' >clean.sh
printf '{"a": 1}\n' >clean.json
git add . && git -c user.email=t@example.com -c user.name=t commit -q -m files

run() { bash "$RC" --base base "$@" 2>"$T/err" >"$T/out"; }
has() { jq -e --arg f "$1" --arg t "$2" 'any(.[]; .file==$f and .tool==$t and .line>0)' "$T/out" >/dev/null; }

run
jq -e 'type=="array"' "$T/out" >/dev/null && ok "valid JSON array" || bad "valid JSON array"
if command -v shellcheck >/dev/null; then has bad.sh shellcheck && ok shellcheck || bad shellcheck; fi
has syntax.sh bash-n && ok "bash -n" || bad "bash -n"
has syntax.py py_compile && ok py_compile || bad py_compile
if command -v ruff >/dev/null; then has unused.py ruff && ok ruff || bad ruff; fi
has bad.json jq && ok jq || bad jq
if command -v node >/dev/null; then has bad.js node-check && ok node-check || bad node-check; fi
jq -e 'any(.[]; .file=="clean.sh" or .file=="clean.json")' "$T/out" >/dev/null && bad "clean files silent" || ok "clean files silent"
jq -e 'all(.[]; has("file") and has("line") and has("rule") and has("message") and has("tool") and has("text"))' "$T/out" >/dev/null &&
  ok "schema keys" || bad "schema keys"

# score_review.py compatibility: a shellcheck finding scores against a ground truth naming its rule.
if command -v shellcheck >/dev/null; then
  printf '{"matcher_version":1,"bugs":[{"id":"B1","file":"bad.sh","match":"SC2045|SC2086","example":"x"}]}' >gt.json
  python3 "$ROOT/scripts/score_review.py" gt.json "$T/out" | jq -e '.recall==1.0' >/dev/null && ok "score_review recall 1.0" || bad "score_review"
fi

# Missing tool => "not run" line, exit 0. Hide shellcheck/ruff/jq by pruning PATH to python3+git+core only.
mkdir bin
for c in git python3 bash sed grep head tail mktemp rm cat dirname perl env; do ln -s "$(command -v "$c")" bin/ 2>/dev/null || true; done
if PATH="$T/bin" bash "$RC" --base base >"$T/out2" 2>"$T/err2"; then ok "missing tools exit 0"; else bad "missing tools exit 0"; fi
grep -q 'not run: shellcheck (not installed)' "$T/err2" && ok "not-run line" || bad "not-run line"

# Timebox: a declared test command that sleeps past --timeout is "not run", not a failure.
REVIEW_TEST_CMD='sleep 5' run --tests --timeout 1 && grep -q 'not run: tests (timeout' "$T/err" && ok timebox || bad timebox
REVIEW_TEST_CMD='echo boom; exit 3' run --tests
jq -e 'any(.[]; .tool=="tests" and .rule=="test-failed")' "$T/out" >/dev/null && ok "--tests failure finding" || bad "--tests failure finding"
run --tests; grep -q 'REVIEW_TEST_CMD not set' "$T/err" && ok "--tests opt-in needs cmd" || bad "--tests opt-in needs cmd"

bash "$RC" --base nosuchref >/dev/null 2>&1 && bad "bad base exits 2" || ok "bad base exits non-zero"
exit "$fail"
