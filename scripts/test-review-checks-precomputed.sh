#!/usr/bin/env bash
# review_checks.sh with REVIEW_PRECOMPUTED=<dir>: semgrep's result is read from the <dir>/semgrep.json envelope and no
# semgrep process starts. ran -> the sjson semgrep path (changed files only); failed, skipped, missing, malformed or a
# non-zero exit -> not-run with a reason, never clean. Every run prints one "analyzer <tool>: <status>" line per
# analyzer. Without the env var, semgrep runs as before. Stub semgrep, no network.
set -euo pipefail
RC=${REVIEW_CHECKS:-$(cd "$(dirname "$0")/.." && pwd)/.claude/skills/deep-code-review/scripts/review_checks.sh}
T=$(mktemp -d "${TMPDIR:-/tmp}/sgp.XXXXXX") && [ -n "$T" ] && [ -d "$T" ] || { echo "no temp dir" >&2; exit 1; }
trap 'rm -rf "$T"' EXIT; fail=0
ok() { echo "ok - $1"; }; bad() { echo "FAIL - $1"; fail=1; }
mkdir -p "$T/stub" "$T/repo" "$T/pre"
cat >"$T/stub/semgrep" <<'S'
#!/usr/bin/env bash
echo "semgrep $*" >>"$SG_LOG"
echo '{"results":[{"path":"app.py","start":{"line":1},"check_id":"perun.py.sqli","extra":{"message":"live"}}],"errors":[]}'
S
chmod +x "$T/stub/semgrep"; export SG_LOG="$T/sg.log" PERUN_HEAVY_DIR="$T/heavy" REVIEW_SEMGREP_REGISTRY=0; : >"$SG_LOG"
cd "$T/repo" || exit 1
git init -q . && case "$(git rev-parse --show-toplevel)" in "$(cd "$T" && pwd -P)"/*) ;; *) echo "refusing: repo not under temp dir" >&2; exit 1 ;; esac
printf 'old\n' >other.py; git add . && git -c user.email=t@example.com -c user.name=t commit -q -m base && git branch base
printf 'x\ny\n' >app.py; git add . && git -c user.email=t@example.com -c user.name=t commit -q -m f
# env TOOL STATUS EXIT REPORT(json string or null) REASON -> $T/pre/semgrep.json
envl() { jq -n --arg t "$1" --arg s "$2" --argjson e "$3" --argjson r "$4" --arg why "$5" \
  '{envelope:1, scanner:"deep-code-review", tool:$t, status:$s, exit:$e, version:"1.182.1", rules:"bundled taint rules", report:$r, reason:$why}' >"$T/pre/semgrep.json"; }
REP=$(jq -n '{results:[{path:"app.py",start:{line:2},check_id:"taint.py.sqli",extra:{message:"pre"}},
                       {path:"other.py",start:{line:1},check_id:"taint.py.sqli",extra:{message:"unchanged file"}}],errors:[]} | tojson')
run() { : >"$SG_LOG"; PATH="$T/stub:$PATH" bash "$RC" --base base 2>"$T/err" >"$T/out"; }
pre() { REVIEW_PRECOMPUTED="$T/pre" run; }
nosg() { [ ! -s "$SG_LOG" ]; }
notclean() { ! jq -e 'any(.[]; .tool=="semgrep")' "$T/out" >/dev/null && grep -q "analyzer semgrep: not-run ($1" "$T/err"; }

envl semgrep ran 0 "$REP" ""; pre
nosg && ok "ran: no semgrep process" || bad "ran: semgrep was started"
jq -e 'any(.[]; .tool=="semgrep" and .rule=="taint.py.sqli" and .file=="app.py" and .line==2)' "$T/out" >/dev/null \
  && ok "ran: finding read from the envelope" || bad "ran: finding read from the envelope"
! jq -e 'any(.[]; .file=="other.py")' "$T/out" >/dev/null && ok "ran: unchanged file dropped" || bad "ran: unchanged file dropped"
grep -q 'analyzer semgrep: precomputed (read ' "$T/err" && ok "ran: reported precomputed" || bad "ran: reported precomputed"
grep -Eq 'analyzers ran: [^;]*semgrep' "$T/err" && bad "ran: precomputed listed as ran" || ok "ran: precomputed not listed as ran"

envl semgrep failed 2 null "semgrep crashed"; pre
nosg && notclean "precomputed failed: semgrep crashed" && ok "failed: not-run with reason" || bad "failed: not-run with reason"
envl semgrep skipped 0 null "no source files"; pre
nosg && notclean "precomputed skipped: no source files" && ok "skipped: not-run with reason" || bad "skipped: not-run with reason"
envl semgrep ran 2 "$REP" ""; pre
nosg && notclean "precomputed exit 2" && ok "ran with non-zero exit: not-run" || bad "ran with non-zero exit: not-run"
envl semgrep ran 0 '"not json"' ""; pre
nosg && notclean "precomputed report unparseable" && ok "unparseable report: not-run" || bad "unparseable report: not-run"
envl semgrep ran 0 null ""; pre
nosg && notclean "precomputed envelope invalid" && ok "ran with null report: not-run" || bad "ran with null report: not-run"
envl trivy ran 0 "$REP" ""; pre
nosg && notclean "precomputed envelope invalid" && ok "wrong tool: not-run" || bad "wrong tool: not-run"
rm -f "$T/pre/semgrep.json"; pre
nosg && notclean "precomputed envelope missing" && ok "missing envelope: not-run, no fallback run" || bad "missing envelope"

run
[ -s "$SG_LOG" ] && jq -e 'any(.[]; .tool=="semgrep" and .message=="live")' "$T/out" >/dev/null \
  && grep -q 'analyzer semgrep: ran$' "$T/err" && ok "unset: semgrep runs as before" || bad "unset: semgrep runs as before"
grep -q 'analyzer py_compile: ran$' "$T/err" && ok "per-analyzer row for another tool" || bad "per-analyzer row for another tool"
exit $fail
