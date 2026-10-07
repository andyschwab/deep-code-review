#!/usr/bin/env python3
"""tracker_check.py - flag work-tracker hygiene gaps from PRs (gh) and, optionally, Linear (read-only).

Checks (see references/work-tracking.md):
  no-tracker-id        open or recently merged PR whose title, body and branch carry no tracker ID
  auto-close-hazard    revert/partial/slice/train PR whose TITLE carries an ID (merge would auto-close the issue)
  missing-assignee / missing-priority / missing-status / stale-in-progress
                       open Linear issues of --project (needs LINEAR_API_KEY; skipped with a "not checked" line otherwise)

Usage: tracker_check.py [--key ACME] [--project ID] [--days 14] [--stale-days 14] [--json]
Env: TRACKER_KEY, TRACKER_PROJECT (flag defaults), LINEAR_API_KEY (read-only, never printed), LINEAR_API_URL.
Fail-open: a missing gh or key prints a "not checked" line and exits 0; findings never change the exit code.
Side effects: none (reads only; gh gets </dev/null).
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.request

HAZARD = re.compile(r"\b(revert|partial|part \d|slice|train)\b", re.I)
LINEAR_URL = "https://api.linear.app/graphql"
QUERY = """query($p: ID!) { issues(first: 100, filter: {project: {id: {eq: $p}},
  state: {type: {nin: ["completed", "canceled"]}}}) { nodes { identifier priority updatedAt
  assignee { id } state { name type } } } }"""


def id_regex(key=None):
    """Regex for tracker IDs: ACME-123 for a configured key, else any UPPER-123."""
    return re.compile(r"\b%s-\d+\b" % (re.escape(key) if key else r"[A-Z][A-Z0-9]+"))


def gh_prs(state, since=None):
    """PRs as dicts, or None when gh is missing/fails (caller prints 'not checked')."""
    cmd = ["gh", "pr", "list", "--state", state, "--limit", "100", "--json",
           "number,title,body,headRefName,updatedAt,mergedAt,isDraft,reviewDecision"]
    if since:
        cmd += ["--search", "merged:>=%s" % since]
    try:
        r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def pr_findings(prs, rx):
    out = []
    for p in prs:
        title = p.get("title") or ""
        if not rx.search("%s\n%s\n%s" % (title, p.get("body") or "", p.get("headRefName") or "")):
            out.append({"kind": "no-tracker-id", "ref": "repo PR %d" % p["number"], "detail": title})
        elif HAZARD.search(title) and rx.search(title):
            out.append({"kind": "auto-close-hazard", "ref": "repo PR %d" % p["number"],
                        "detail": "title carries an ID; move it to 'Refs ID' in the body: " + title})
    return out


def linear_issues(project, key, url):
    """Open issues of a project via read-only GraphQL; raises on transport/GraphQL error (never echoes the key)."""
    req = urllib.request.Request(url, json.dumps({"query": QUERY, "variables": {"p": project}}).encode(),
                                 {"Authorization": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:  # ponytail: first 100 issues, add cursor paging if a project exceeds it
        body = json.load(r)
    if body.get("errors"):
        raise ValueError("GraphQL error")
    return body["data"]["issues"]["nodes"]


def issue_findings(nodes, stale_days, now):
    out = []
    for n in nodes:
        i, st = n["identifier"], n.get("state") or {}
        if not n.get("assignee"):
            out.append({"kind": "missing-assignee", "ref": i, "detail": ""})
        if not n.get("priority"):
            out.append({"kind": "missing-priority", "ref": i, "detail": ""})
        if not st or st.get("type") == "triage":
            out.append({"kind": "missing-status", "ref": i, "detail": ""})
        elif st.get("type") == "started":
            age = (now - dt.datetime.fromisoformat(n["updatedAt"].replace("Z", "+00:00"))).days
            if age > stale_days:
                out.append({"kind": "stale-in-progress", "ref": i, "detail": "%d days without update" % age})
    return out


def run(args, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    rx, findings, notes = id_regex(args.key), [], []
    opened = gh_prs("open")
    merged = gh_prs("merged", (now - dt.timedelta(days=args.days)).date().isoformat())
    if opened is None or merged is None:
        notes.append("PRs: not checked (gh missing, unauthenticated, or failed)")
    findings += pr_findings((opened or []) + (merged or []), rx)
    key = os.environ.get("LINEAR_API_KEY")
    if not (key and args.project):
        notes.append("Linear issues: not checked (needs LINEAR_API_KEY and --project/TRACKER_PROJECT)")
    else:
        try:
            findings += issue_findings(linear_issues(args.project, key, os.environ.get("LINEAR_API_URL", LINEAR_URL)),
                                       args.stale_days, now)
        except Exception as e:  # fail-open; class name only so the key can never leak via a URL or header
            notes.append("Linear issues: not checked (%s)" % type(e).__name__)
    return {"findings": findings, "not_checked": notes}


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--key", default=os.environ.get("TRACKER_KEY"))
    a.add_argument("--project", default=os.environ.get("TRACKER_PROJECT"))
    a.add_argument("--days", type=int, default=14)
    a.add_argument("--stale-days", type=int, default=14)
    a.add_argument("--json", action="store_true")
    args = a.parse_args(argv)
    res = run(args)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        for f in res["findings"]:
            print("%s: %s %s" % (f["kind"], f["ref"], f["detail"]))
        for n in res["not_checked"]:
            print("NOT CHECKED: " + n)
        if not res["findings"]:
            print("tracker_check: no findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
