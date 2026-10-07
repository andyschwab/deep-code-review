#!/usr/bin/env bash
# post_review.sh <PR-number> <findings.json> [--post] — opt-in PR-native delivery of review findings.
#
# Default is a DRY RUN: prints the `gh api` call and JSON payload, posts nothing. --post (explicit,
# never implied) creates ONE pending review (no `event`: only its author sees it until they submit it
# in the PR UI; never APPROVE or REQUEST_CHANGES) with an inline comment per gap finding.
# findings.json: {"start_sha": "<optional head sha>", "findings": [rows shaped like machine-report.md
# rows: id, severity, title, polarity, observation, fix, evidence: ["path:line", ...]]}. Strength rows
# are skipped. Every gap row must be grounded (finding_ground_check.py: file exists under $GROUND_ROOT
# or the git root, line in range, quoted `snippet` within +-5 lines of the cited line); otherwise the run
# refuses (exit 1, ids and reasons on stderr). A row with no evidence or no snippet is ungrounded. Inline lines
# outside the PR diff make GitHub reject the whole review (422): nothing is created, fix and retry.
# Grounding reads start_sha's tree (git show) when set, else the working tree: then the checkout must be the PR head.
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

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
groot="${GROUND_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("start_sha") or "")' "$FILE" 2>/dev/null)"
ref=(); [ -z "$sha" ] || ref=(--ref "$sha")  # ground against the PR head, not whatever is checked out
grounded="$(python3 "$here/finding_ground_check.py" "$FILE" --root "$groot" ${ref[@]+"${ref[@]}"})" || { echo "post_review: cannot read findings (need {\"findings\": [...]})" >&2; exit 2; }
bad="$(printf '%s' "$grounded" | python3 -c '
import json, re, sys
for f in json.load(sys.stdin)["findings"]:
    if f.get("polarity", "gap") == "gap" and not f.get("grounded"):
        print("  " + re.sub(r"[^\w.-]", "?", str(f.get("id", "?"))) + ": " + f["ground_reason"])')"
[ -z "$bad" ] || { printf 'post_review: REFUSE: ungrounded findings (fix or drop them)\n%s\n' "$bad" >&2; exit 1; }

payload="$(HERE="$here" GROUNDED="$grounded" python3 - <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["HERE"])
from finding_ground_check import parse
d = json.loads(os.environ["GROUNDED"])
inline = []
for f in d["findings"]:
    if f.get("polarity", "gap") != "gap":
        continue
    body = f"**{f['severity']} {f['id']}: {f['title']}**\n\n{f.get('observation', '').strip()}\n\nFix: {f.get('fix', '').strip()}"
    path, line, _ = parse(f["evidence"][0])  # same parse as the grounding check: posted where verified
    inline.append({"path": path, "line": line, "side": "RIGHT", "body": body})
p = {"body": "Review findings (draft; verify before submitting).", "comments": inline}
if d.get("start_sha"):
    p["commit_id"] = d["start_sha"]
print(json.dumps(p, indent=2))
PY
)" || { echo "post_review: cannot build payload" >&2; exit 2; }

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
