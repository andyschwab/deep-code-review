#!/usr/bin/env bash
# Tests for templates/perun-review.yml: parses, passes actionlint when installed, trigger and permission
# assertions (least privilege, no pull_request_target, secret only in the read-only job), and that
# install.sh never ships or enables it. Prints PASS/FAIL lines; exits non-zero on any failure.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WF="$ROOT/.claude/skills/deep-code-review/templates/perun-review.yml"
pass=0 fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; pass=$((pass + 1)); else echo "FAIL  $2"; fail=$((fail + 1)); fi; }

[ -f "$WF" ]; ok $? "template exists"

if command -v actionlint >/dev/null 2>&1; then
  actionlint "$WF"; ok $? "actionlint clean"
else
  echo "SKIP  actionlint not installed"
fi

python3 - "$WF" <<'PY'
import sys, yaml
w = yaml.safe_load(open(sys.argv[1]))
on = w.get(True, w.get("on"))          # YAML 1.1 parses bare `on` as True
jobs = w["jobs"]
checks = [
    ("trigger is only pull_request", set(on) == {"pull_request"}),
    ("top-level permissions empty", w["permissions"] == {}),
    ("review job: contents read only", jobs["review"]["permissions"] == {"contents": "read"}),
    ("post job: pull-requests+checks write, contents read",
     jobs["post"]["permissions"] == {"contents": "read", "pull-requests": "write", "checks": "write"}),
    ("review skips fork PRs", "head.repo.full_name == github.repository" in jobs["review"]["if"]),
    ("post depends on review", jobs["post"]["needs"] == "review"),
    ("jobs have timeouts", all("timeout-minutes" in j for j in jobs.values())),
    ("spend cap env present and passed to CLI",
     "DCR_MAX_BUDGET_USD" in w["env"] and "--max-budget-usd" in str(jobs["review"])),
    ("review tools are read-only", '--allowedTools "Read,Grep,Glob"' in str(jobs["review"])),
    ("post checks out base sha, not head",
     "base.sha" in str(jobs["post"]["steps"][0]) and "head.sha" not in str(jobs["post"]["steps"][0].get("with"))),
    ("model secret only in review job", "secrets." not in str(jobs["post"]) and "ANTHROPIC_API_KEY" in str(jobs["review"])),
    ("post posts via post_review.sh --post", "post_review.sh" in str(jobs["post"]) and "--post" in str(jobs["post"])),
    ("no PR text interpolated in run lines",
     not any("github.event.pull_request.title" in s.get("run", "") or "github.event.pull_request.body" in s.get("run", "")
             or "${{" in s.get("run", "") for j in jobs.values() for s in j["steps"])),
    ("persist-credentials false on every checkout",
     all(s.get("with", {}).get("persist-credentials") is False
         for j in jobs.values() for s in j["steps"] if str(s.get("uses", "")).startswith("actions/checkout"))),
]
bad = 0
for name, good in checks:
    print(("PASS  " if good else "FAIL  ") + name)
    bad += not good
sys.exit(bad)
PY
rc=$?; [ "$rc" -eq 0 ] && pass=$((pass + 1)) || fail=$((fail + rc))
echo "(python assertion block rc=$rc)"

! grep -q "perun-review" "$ROOT/install.sh"; ok $? "install.sh never references the template (opt-in)"
! grep -q "pull_request_target" <(grep -v '^ *#' "$WF"); ok $? "no pull_request_target outside comments"

echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
