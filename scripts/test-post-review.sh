#!/usr/bin/env bash
# Tests for post_review.sh with a stubbed gh: dry-run default posts nothing, --post makes exactly one
# call with a pending (event-less) review, banlist/secret/home-path hits refuse, missing banlist fails closed.
# Plain bash; prints PASS/FAIL lines and "N passed, M failed"; exits non-zero on any failure.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PR="$ROOT/.claude/skills/deep-code-review/scripts/post_review.sh"
WORK="$(cd "$(mktemp -d "${TMPDIR:-/tmp}/dcr-test-post.XXXXXX")" && pwd -P)"
trap 'rm -rf "$WORK"' EXIT
pass=0 fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; pass=$((pass + 1)); else echo "FAIL  $2"; fail=$((fail + 1)); fi; }

mkdir -p "$WORK/bin" "$WORK/bl"
cat >"$WORK/bin/gh" <<'EOF'
#!/usr/bin/env bash
echo "$*" >>"$GH_LOG"; cat >"$GH_LOG.stdin"
EOF
chmod +x "$WORK/bin/gh"
export PATH="$WORK/bin:$PATH" GH_LOG="$WORK/gh.log" BANLIST_DIR="$WORK/bl"
printf 'AKIA[0-9A-Z]{16}\nacme-secret-name\n' >"$WORK/bl/.banlist.txt"

cat >"$WORK/f.json" <<'EOF'
{"start_sha": "0123abc", "findings": [
 {"id": "F1", "severity": "High", "title": "Unchecked redirect", "polarity": "gap",
  "observation": "Redirect target comes from the query string.", "fix": "Allowlist hosts.", "evidence": ["src/app.py:42"]},
 {"id": "F2", "severity": "Medium", "title": "No evidence row", "polarity": "gap", "observation": "x", "fix": "y", "evidence": []},
 {"id": "F3", "severity": "Low", "title": "Strength row", "polarity": "strength", "observation": "z", "evidence": ["a.py:1"]}]}
EOF

out=$(bash "$PR" 7 "$WORK/f.json" 2>&1); rc=$?
[ "$rc" -eq 0 ] && [ ! -e "$GH_LOG" ] && echo "$out" | grep -q 'DRY RUN' && echo "$out" | grep -q 'pulls/7/reviews'
ok $? "default is a dry run: prints payload, gh never called"
echo "$out" | grep -q '"path": "src/app.py"' && echo "$out" | grep -q '"line": 42' && echo "$out" | grep -q '"commit_id": "0123abc"' \
  && echo "$out" | grep -q 'No evidence row' && ! echo "$out" | grep -q 'Strength row'
ok $? "payload: inline comment for evidence row, loose row in body, strength row skipped"
! echo "$out" | grep -q '"event"'
ok $? "payload has no event (pending review, never approve/request-changes)"

bash "$PR" 7 "$WORK/f.json" --post >/dev/null 2>&1; rc=$?
[ "$rc" -eq 0 ] && [ "$(wc -l <"$GH_LOG" | tr -d ' ')" = 1 ] && grep -q 'api -X POST repos/{owner}/{repo}/pulls/7/reviews --input -' "$GH_LOG" \
  && grep -q '"src/app.py"' "$GH_LOG.stdin"
ok $? "--post makes exactly one gh api call with the payload on stdin"

rm -f "$GH_LOG"
sed 's/Allowlist hosts/key AKI''AABCDEFGHIJKLMNOP/' "$WORK/f.json" >"$WORK/bad.json"
bash "$PR" 7 "$WORK/bad.json" --post >/dev/null 2>"$WORK/err"; rc=$?
[ "$rc" -eq 1 ] && [ ! -e "$GH_LOG" ] && grep -q 'banlist pattern hit' "$WORK/err" && ! grep -q AKIA "$WORK/err"
ok $? "banlist hit refuses --post, names pattern file only, gh never called"
sed 's/Allowlist hosts/see acme-secret-name/' "$WORK/f.json" >"$WORK/bad2.json"
bash "$PR" 7 "$WORK/bad2.json" >/dev/null 2>&1; [ "$?" -eq 1 ]
ok $? "banlist hit refuses even the dry run"
sed 's#Allowlist hosts#at /home/jdoe/x#' "$WORK/f.json" >"$WORK/bad3.json"
bash "$PR" 7 "$WORK/bad3.json" >/dev/null 2>&1; [ "$?" -eq 1 ]
ok $? "absolute home path refuses"

rm "$WORK/bl/.banlist.txt"
bash "$PR" 7 "$WORK/f.json" --post >/dev/null 2>&1; [ "$?" -eq 2 ] && [ ! -e "$GH_LOG" ]
ok $? "missing banlist fails closed"
bash "$PR" x "$WORK/f.json" >/dev/null 2>&1; [ "$?" -eq 2 ]
ok $? "non-numeric PR is a usage error"
bash "$PR" 7 "$WORK/f.json" --yes >/dev/null 2>&1; [ "$?" -eq 2 ]
ok $? "unknown flag is a usage error"

echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
