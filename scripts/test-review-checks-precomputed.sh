#!/usr/bin/env bash
# review_checks.sh with REVIEW_PRECOMPUTED=<dir>: semgrep's result is read from the <dir>/semgrep.json envelope and no
# semgrep process starts. status ran goes through the sjson semgrep parser (changed files only, rule ids as given) and is
# reported as precomputed; failed, skipped, a non-zero exit, a missing or malformed envelope or report land in NOT RUN with a
# not-checked row, never clean, and never fall back to a live run. Without the env var, semgrep runs as before. Stub semgrep, no network.
set -euo pipefail
RC=${REVIEW_CHECKS:-$(cd "$(dirname "$0")/.." && pwd)/.claude/skills/deep-code-review/scripts/review_checks.sh}
T=$(mktemp -d "${TMPDIR:-/tmp}/sgp.XXXXXX") && [ -n "$T" ] && [ -d "$T" ] || { echo "no temp dir" >&2; exit 1; }
trap 'rm -rf "$T"' EXIT; fail=0
export DCR_CACHE_ROOT="$T/nocache" DCR_USER_BIN= REVIEW_SEMGREP_REGISTRY=0 PERUN_HEAVY_DIR="$T/heavy" SG_LOG="$T/sg.log"
ok() { echo "ok - $1"; }; bad() { echo "FAIL - $1"; fail=1; }
mkdir -p "$T/stub" "$T/repo" "$T/pre"
cat >"$T/stub/semgrep" <<'S'
#!/usr/bin/env bash
echo "semgrep $*" >>"$SG_LOG"
echo '{"results":[{"path":"app.py","start":{"line":1},"check_id":"perun.py.sqli","extra":{"message":"live"}}],"errors":[]}'
S
chmod +x "$T/stub/semgrep"
cd "$T/repo" || exit 1
git init -q . && case "$(git rev-parse --show-toplevel)" in "$(cd "$T" && pwd -P)"/*) ;; *) echo "refusing: repo not under temp dir" >&2; exit 1 ;; esac
printf 'old\n' >other.py; git add . && git -c user.email=t@example.com -c user.name=t commit -q -m base && git branch base
printf 'x\ny\n' >app.py; git add . && git -c user.email=t@example.com -c user.name=t commit -q -m f
rec=$(git rev-parse --git-common-dir)/review-checks-last.json
# envl TOOL STATUS EXIT REPORT(JSON: a string or null) REASON -> $T/pre/semgrep.json
envl() { python3 -c 'import json, sys; t, s, e, r, w, o = sys.argv[1:]
json.dump({"envelope": 1, "scanner": "deep-code-review", "tool": t, "status": s, "exit": int(e), "version": "1.182.1",
           "rules": "bundled taint rules", "report": json.loads(r), "reason": w}, open(o, "w"))' "$@" "$T/pre/semgrep.json"; }
rep() { python3 -c 'import json, sys; print(json.dumps(json.dumps({"results": [
  {"path": "app.py", "start": {"line": 2}, "check_id": "taint.py.sqli", "extra": {"message": "pre"}},
  {"path": "./other.py", "start": {"line": 1}, "check_id": "taint.py.sqli", "extra": {"message": "unchanged file"}}], "errors": json.loads(sys.argv[1])})))' "${1:-[]}"; }
run() { : >"$SG_LOG"; rm -f "$rec"; PATH="$T/stub:$PATH" bash "$RC" --base base 2>"$T/err" >"$T/out"; }
pre() { REVIEW_PRECOMPUTED="$T/pre/" run; }
nosg() { [ ! -s "$SG_LOG" ]; }
# notclean WHY: no semgrep finding, a not-checked row, NOT RUN names the reason, the closing line counts semgrep as not run, no "precomputed"
notclean() {
  nosg && ! jq -e 'any(.[]; .tool=="semgrep" and .rule!="not-checked")' "$T/out" >/dev/null \
    && jq -e 'any(.[]; .tool=="semgrep" and .rule=="not-checked")' "$T/out" >/dev/null \
    && grep -qF "NOT RUN: semgrep (precomputed $1" "$T/err" && grep -Eq 'wired [0-9]+ scanners; not run: [^;]*semgrep' "$T/err" \
    && ! grep -q 'precomputed: semgrep' "$T/err"
}

envl semgrep ran 0 "$(rep)" ""; pre
nosg && ok "ran: no semgrep process" || bad "ran: semgrep was started"
jq -e 'any(.[]; .tool=="semgrep" and .rule=="taint.py.sqli" and .file=="app.py" and .line==2)' "$T/out" >/dev/null \
  && ok "ran: finding read from the envelope, rule id as given" || bad "ran: finding read from the envelope"
! jq -e 'any(.[]; .file=="other.py" or .file=="./other.py")' "$T/out" >/dev/null && ok "ran: unchanged file dropped" || bad "ran: unchanged file dropped"
grep -Eq 'analyzers ran: [^;]*semgrep \(precomputed\)' "$T/err" && grep -Eq 'wired [0-9]+ scanners.*; precomputed: semgrep' "$T/err" \
  && ! grep -Eq 'not run: [^;]*semgrep' "$T/err" && ok "ran: summary says precomputed and read" || bad "ran: summary says precomputed and read"
jq -e '.precomputed == ["semgrep"] and (.not_run | index("semgrep") | not)' "$rec" >/dev/null && ok "ran: record lists semgrep as precomputed" || bad "ran: record"

envl semgrep failed 2 null "semgrep crashed"; pre
notclean "failed: semgrep crashed" && ok "failed: not run with the reason" || bad "failed: not run with the reason"
envl semgrep skipped 0 null "no source files"; pre
notclean "skipped: no source files" && ok "skipped: not run with the reason" || bad "skipped: not run with the reason"
envl semgrep ran 2 "$(rep)" ""; pre
notclean "exit 2" && ok "ran with a non-zero exit: not run" || bad "ran with a non-zero exit: not run"
envl semgrep ran 0 '"not json"' ""; pre
notclean "report unparseable" && ok "unparseable report: not run" || bad "unparseable report: not run"
envl semgrep ran 0 null ""; pre
notclean "envelope invalid" && ok "ran with a null report: not run" || bad "ran with a null report: not run"
envl trivy ran 0 "$(rep)" ""; pre
notclean "envelope invalid" && ok "wrong tool: not run" || bad "wrong tool: not run"
printf '{"envelope": 1,' >"$T/pre/semgrep.json"; pre
notclean "envelope invalid" && ok "truncated JSON: not run" || bad "truncated JSON: not run"
rm -f "$T/pre/semgrep.json"; pre
notclean "envelope missing" && ok "missing envelope: not run, no fallback to a live run" || bad "missing envelope"

envl semgrep ran 0 "$(rep '[{"path": "app.py", "message": "parse error"}]')" ""; pre
nosg && jq -e 'any(.[]; .tool=="semgrep" and .rule=="taint.py.sqli")' "$T/out" >/dev/null && grep -Eq 'partial: [^;]*semgrep\(errors\)' "$T/err" \
  && ok "report with errors: findings kept, partial" || bad "report with errors: findings kept, partial"

run
[ -s "$SG_LOG" ] && jq -e 'any(.[]; .tool=="semgrep" and .message=="live")' "$T/out" >/dev/null && ! grep -q precomputed "$T/err" \
  && jq -e 'has("precomputed") | not' "$rec" >/dev/null && ok "unset: semgrep runs as before" || bad "unset: semgrep runs as before"
exit $fail
