#!/usr/bin/env bash
# post_review.sh <PR-number> <findings.json> [--post] — opt-in PR-native delivery of review findings.
#
# Default is a DRY RUN: prints the `gh api` call and JSON payload, posts nothing. --post (explicit,
# never implied) creates ONE pending review (no `event`: only its author sees it until they submit it
# in the PR UI; never APPROVE or REQUEST_CHANGES) with an inline comment per gap finding.
# findings.json: {"start_sha": "<optional head sha>", "findings": [rows shaped like machine-report.md
# rows: id, severity, title, polarity, observation, fix, evidence: ["path:line", ...]]}. Strength rows
# are skipped; a gap row with no parsable evidence goes into the review body, not inline. Inline lines
# outside the PR diff make GitHub reject the whole review (422): nothing is created, fix and retry.
# Refuses (exit 1) when the payload hits .banlist.txt/.banlist.local.txt (resolved from the git root or
# $BANLIST_DIR, same semantics as the contribution skill's prefile_check.sh), a secret-shaped token or
# an absolute home path; exit 2 on usage error or a missing/empty banlist (fail closed). Prints
# pattern NAMES only, never matched text. Posting is outward-facing: only run --post after the human
# has read the dry run. Side effects: --post only; one network call through `gh`.
set -u
usage() { echo "usage: post_review.sh <PR-number> <findings.json> [--post]" >&2; exit 2; }
[ "$#" -ge 2 ] && [ "$#" -le 3 ] && [ -f "$2" ] || usage
case "$1" in ''|*[!0-9]*) usage ;; esac
[ "$#" -eq 2 ] || [ "$3" = "--post" ] || usage
PR=$1 FILE=$2 POST=0
[ "${3:-}" = "--post" ] && POST=1
dir="${BANLIST_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
[ -s "$dir/.banlist.txt" ] || { echo "post_review: $dir/.banlist.txt missing or empty (fail closed)" >&2; exit 2; }

payload="$(python3 - "$FILE" <<'PY'
import json, re, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
inline, loose = [], []
for f in d["findings"]:
    if f.get("polarity", "gap") != "gap":
        continue
    body = f"**{f['severity']} {f['id']}: {f['title']}**\n\n{f.get('observation', '').strip()}\n\nFix: {f.get('fix', '').strip()}"
    m = re.match(r"^(.+):(\d+)$", (f.get("evidence") or [""])[0])
    if m:
        inline.append({"path": m[1], "line": int(m[2]), "side": "RIGHT", "body": body})
    else:
        loose.append(body)
p = {"body": "\n\n".join(["Review findings (draft; verify before submitting)."] + loose), "comments": inline}
if d.get("start_sha"):
    p["commit_id"] = d["start_sha"]
print(json.dumps(p, indent=2))
PY
)" || { echo "post_review: cannot read findings (need {\"findings\": [...]})" >&2; exit 2; }

# Scan the DECODED text, not the JSON: escapes hide non-ASCII names (\u017c), backslash paths (C:\\Users)
# and line-split names. Scan the strings as written, then again with all whitespace collapsed to one space.
scan="$(printf '%s' "$payload" | python3 -X utf8 -c '
import json, re, sys
p = json.load(sys.stdin)
t = "\n".join([p["body"], p.get("commit_id", "")] + [c["path"] + "\n" + c["body"] for c in p["comments"]])
print(t); print(re.sub(r"\s+", " ", t))')" || { echo "post_review: cannot decode payload" >&2; exit 2; }
hits=0
flag() { echo "post_review: REFUSE: $1" >&2; hits=1; }
for f in "$dir/.banlist.txt" "$dir/.banlist.local.txt"; do
  [ -f "$f" ] || continue
  while IFS= read -r p || [ -n "$p" ]; do
    p="${p#"${p%%[![:space:]]*}"}"
    case "$p" in ''|'#'*) continue ;; esac
    printf '%s' "$scan" | grep -qE -e "$p" 2>/dev/null; rc=$?
    [ "$rc" -eq 0 ] && flag "banlist pattern hit in $(basename "$f") (content withheld)"
    [ "$rc" -ge 2 ] && flag "invalid regex in $(basename "$f") (fail closed, content withheld)"
  done < "$f"
done
printf '%s' "$scan" | grep -qE 'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|-----BEGIN [A-Z ]*PRIVATE KEY-----' && flag "secret-shaped token"
printf '%s' "$scan" | grep -qE '(/Users/|/home/|[A-Za-z]:\\Users\\)[A-Za-z0-9._-]+' && flag "absolute home path"
[ "$hits" -eq 0 ] || exit 1

if [ "$POST" -eq 0 ]; then
  echo "post_review: DRY RUN (nothing posted; add --post to create a pending review)"
  printf 'gh api -X POST repos/{owner}/{repo}/pulls/%s/reviews --input - <<EOF\n%s\nEOF\n' "$PR" "$payload"
  exit 0
fi
printf '%s' "$payload" | gh api -X POST "repos/{owner}/{repo}/pulls/$PR/reviews" --input -
