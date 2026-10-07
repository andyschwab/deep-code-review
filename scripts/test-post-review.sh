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
mkdir -p "$WORK/repo/src"
printf 'a\nb\nredirect(request.args["next"])\nc\n' >"$WORK/repo/src/app.py"
git -C "$WORK/repo" init -q && git -C "$WORK/repo" add . && git -C "$WORK/repo" -c user.name=t -c user.email=t@example.com commit -qm x
SHA="$(git -C "$WORK/repo" rev-parse HEAD)"
export PATH="$WORK/bin:$PATH" GH_LOG="$WORK/gh.log" BANLIST_DIR="$WORK/bl" GROUND_ROOT="$WORK/repo"
printf 'AKIA[0-9A-Z]{16}\nacme-secret-name\n' >"$WORK/bl/.banlist.txt"

cat >"$WORK/f.json" <<'EOF'
{"start_sha": "SHAHERE", "findings": [
 {"id": "F1", "severity": "High", "title": "Unchecked redirect", "polarity": "gap",
  "observation": "Redirect target comes from the query string.", "fix": "Allowlist hosts.", "evidence": ["src/app.py:3"], "snippet": "redirect(request.args[\"next\"])"},
 {"id": "F3", "severity": "Low", "title": "Strength row", "polarity": "strength", "observation": "z", "evidence": ["a.py:1"]}]}
EOF
sed -i.bak "s/SHAHERE/$SHA/" "$WORK/f.json"

out=$(bash "$PR" 7 "$WORK/f.json" 2>&1); rc=$?
[ "$rc" -eq 0 ] && [ ! -e "$GH_LOG" ] && echo "$out" | grep -q 'DRY RUN' && echo "$out" | grep -q 'pulls/7/reviews'
ok $? "default is a dry run: prints payload, gh never called"
echo "$out" | grep -q '"path": "src/app.py"' && echo "$out" | grep -q '"line": 3' && echo "$out" | grep -q "\"commit_id\": \"$SHA\"" \
  && ! echo "$out" | grep -q 'Strength row'
ok $? "payload: inline comment for grounded row, strength row skipped"
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

# decoded-text scan: probes are JSON-escaped in the findings file, so only a decoded scan sees them
printf '\xc5\xbc\xc3\xb3\xc5\x82w-name\nAcme Capital\n' >>"$WORK/bl/.banlist.txt"
probe() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d["findings"][0]["fix"]=sys.argv[3]; json.dump(d,open(sys.argv[2],"w"))' "$WORK/f.json" "$WORK/p.json" "$1"; }
sed 's/Allowlist hosts/\\u017c\\u00f3\\u0142w-name/' "$WORK/f.json" >"$WORK/p.json"; bash "$PR" 7 "$WORK/p.json" >/dev/null 2>&1; [ "$?" -eq 1 ]
ok $? "non-ASCII banlist name hidden behind a JSON \\u escape refuses"
probe 'see Acme
Capital'; bash "$PR" 7 "$WORK/p.json" >/dev/null 2>&1; [ "$?" -eq 1 ]
ok $? "banlist name split across a line break refuses"
probe 'path C:\Users\jdoe\x'; bash "$PR" 7 "$WORK/p.json" >/dev/null 2>&1; [ "$?" -eq 1 ]
ok $? "Windows home path (backslashes) refuses"

python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d["findings"][0]["snippet"]="not in file"; json.dump(d,open(sys.argv[2],"w"))' "$WORK/f.json" "$WORK/ug.json"
rm -f "$GH_LOG"; bash "$PR" 7 "$WORK/ug.json" --post >/dev/null 2>"$WORK/err"; rc=$?
[ "$rc" -eq 1 ] && [ ! -e "$GH_LOG" ] && grep -q 'ungrounded' "$WORK/err" && grep -q 'F1' "$WORK/err"
ok $? "ungrounded finding refuses --post, gh never called"

python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d["findings"][0]["evidence"]=[]; json.dump(d,open(sys.argv[2],"w"))' "$WORK/f.json" "$WORK/ne.json"
bash "$PR" 7 "$WORK/ne.json" >/dev/null 2>"$WORK/err"; rc=$?
[ "$rc" -eq 1 ] && grep -q 'no path:line evidence' "$WORK/err"
ok $? "gap row with empty evidence refuses"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d["findings"][0]["id"]="F\x1b[31mX"; d["findings"][0]["snippet"]="nope nope nope"; json.dump(d,open(sys.argv[2],"w"))' "$WORK/f.json" "$WORK/esc.json"
bash "$PR" 7 "$WORK/esc.json" >/dev/null 2>"$WORK/err"; ! grep -q "$(printf '\033')" "$WORK/err" && grep -q 'ungrounded' "$WORK/err"
ok $? "control characters in an id are not echoed to the terminal"

# grounding reads start_sha's tree: a checkout that differs from the PR head must not decide the result
printf 'x\ny\nz\n' >"$WORK/repo/src/app.py"
bash "$PR" 7 "$WORK/f.json" >/dev/null 2>&1; rc=$?
sed "s/$SHA/0000000000000000000000000000000000000000/" "$WORK/f.json" >"$WORK/badsha.json"
bash "$PR" 7 "$WORK/badsha.json" >/dev/null 2>&1; rc2=$?
[ "$rc" -eq 0 ] && [ "$rc2" -eq 1 ]
ok $? "start_sha grounds against the PR head tree, not the working tree; unknown sha fails closed"

rm "$WORK/bl/.banlist.txt"
bash "$PR" 7 "$WORK/f.json" --post >/dev/null 2>&1; [ "$?" -eq 2 ] && [ ! -e "$GH_LOG" ]
ok $? "missing banlist fails closed"
bash "$PR" x "$WORK/f.json" >/dev/null 2>&1; [ "$?" -eq 2 ]
ok $? "non-numeric PR is a usage error"
bash "$PR" 7 "$WORK/f.json" --yes >/dev/null 2>&1; [ "$?" -eq 2 ]
ok $? "unknown flag is a usage error"

echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
