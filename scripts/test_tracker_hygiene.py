#!/usr/bin/env python3
"""Tests for tracker_check.py, tracker_weekly_update.py and install.sh --tracker-project (stdlib only)."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SD = os.path.join(ROOT, ".claude/skills/agentic-delivery/scripts")
sys.path.insert(0, SD)
import tracker_check as tc  # noqa: E402

OPEN = [
    {"number": 1, "title": "ACME-1 add widget", "body": "", "headRefName": "a", "reviewDecision": "", "isDraft": False},
    {"number": 2, "title": "tidy docs", "body": "", "headRefName": "docs", "reviewDecision": "CHANGES_REQUESTED", "isDraft": False},
]
MERGED = [
    {"number": 3, "title": "Revert ACME-2 widget", "body": "", "headRefName": "r", "reviewDecision": ""},
    {"number": 4, "title": "Slice one", "body": "Refs ACME-3", "headRefName": "s", "reviewDecision": ""},
    {"number": 5, "title": "ACME-4 finish", "body": "", "headRefName": "f", "reviewDecision": ""},
    {"number": 6, "title": "misc cleanup", "body": "", "headRefName": "m", "reviewDecision": ""},
]
NODES = [
    {"identifier": "ACME-9", "priority": 0, "updatedAt": "2026-01-01T00:00:00Z", "assignee": None,
     "state": {"name": "In Progress", "type": "started"}},
    {"identifier": "ACME-10", "priority": 2, "updatedAt": "2026-01-01T00:00:00Z", "assignee": {"id": "u"}, "state": None},
]
SEEN = {}


class Fake(BaseHTTPRequestHandler):
    def do_POST(self):
        SEEN["auth"] = self.headers.get("Authorization")
        SEEN["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        out = json.dumps({"data": {"issues": {"nodes": NODES}}}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


def w(path, text):
    with open(path, "w") as f:
        f.write(text)


def shim_dir(prs):
    """A PATH dir holding a stub gh that serves canned PR JSON (and fails if stdin is a terminal-less read)."""
    d = tempfile.mkdtemp()
    w(os.path.join(d, "prs.json"), json.dumps(prs))
    g = os.path.join(d, "gh")
    w(g, '#!/bin/sh\nif [ "$3" = "--state" ] && [ "$4" = "merged" ]; then cat "$(dirname "$0")/merged.json"; '
              'else cat "$(dirname "$0")/prs.json"; fi\n')
    w(os.path.join(d, "merged.json"), json.dumps(MERGED))
    os.chmod(g, 0o755)
    return d


def run(script, args, path, env=None):
    e = dict(os.environ, PATH=path + os.pathsep + "/usr/bin:/bin", **(env or {}))
    e.pop("LINEAR_API_KEY", None) if not env or "LINEAR_API_KEY" not in env else None
    return subprocess.run([sys.executable, os.path.join(SD, script)] + args, capture_output=True, text=True, env=e, stdin=subprocess.DEVNULL)


class T(unittest.TestCase):
    def test_pr_findings(self):
        kinds = {(f["kind"], f["ref"]) for f in tc.pr_findings(OPEN + MERGED, tc.id_regex("ACME"))}
        self.assertEqual(kinds, {("no-tracker-id", "repo PR 2"), ("no-tracker-id", "repo PR 6"), ("auto-close-hazard", "repo PR 3")})

    def test_key_scopes_regex(self):
        self.assertFalse(tc.id_regex("ACME").search("OTHER-5"))
        self.assertTrue(tc.id_regex().search("OTHER-5"))

    def test_cli_json_without_key_fails_open(self):
        r = run("tracker_check.py", ["--json", "--key", "ACME"], shim_dir(OPEN))
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertTrue(any("Linear issues: not checked" in n for n in out["not_checked"]))
        self.assertTrue(any(f["kind"] == "no-tracker-id" for f in out["findings"]))

    def test_gh_missing_not_checked(self):
        r = run("tracker_check.py", [], tempfile.mkdtemp())
        self.assertEqual(r.returncode, 0)
        self.assertIn("NOT CHECKED: PRs", r.stdout)

    def test_linear_fake_server_and_key_never_logged(self):
        srv = HTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        env = {"LINEAR_API_KEY": "lin_secret_xyz", "LINEAR_API_URL": "http://127.0.0.1:%d/" % srv.server_port}
        r = run("tracker_check.py", ["--project", "p1", "--json"], shim_dir([]), env)
        srv.shutdown()
        srv.server_close()
        kinds = {(f["kind"], f["ref"]) for f in json.loads(r.stdout)["findings"]}
        self.assertTrue({("missing-assignee", "ACME-9"), ("missing-priority", "ACME-9"),
                         ("stale-in-progress", "ACME-9"), ("missing-status", "ACME-10")} <= kinds)
        self.assertEqual(SEEN["auth"], "lin_secret_xyz")
        self.assertEqual(SEEN["body"]["variables"], {"p": "p1"})
        self.assertNotIn("lin_secret_xyz", r.stdout + r.stderr)

    def test_linear_error_fails_open_without_leak(self):
        env = {"LINEAR_API_KEY": "lin_secret_xyz", "LINEAR_API_URL": "http://127.0.0.1:9/"}
        r = run("tracker_check.py", ["--project", "p1"], shim_dir([]), env)
        self.assertEqual(r.returncode, 0)
        self.assertIn("NOT CHECKED: Linear issues: not checked (", r.stdout)
        self.assertNotIn("lin_secret_xyz", r.stdout + r.stderr)

    def test_weekly_draft(self):
        r = run("tracker_weekly_update.py", ["--key", "ACME"], shim_dir(OPEN))
        self.assertEqual(r.returncode, 0)
        for s in ("Suggested health: At risk", "ACME-4: ACME-4 finish (repo PR 5)", "### Blockers\n- tidy docs (repo PR 2)",
                  "### Untracked", "misc cleanup (repo PR 6)"):
            self.assertIn(s, r.stdout)
        self.assertNotIn("#", r.stdout.replace("### ", "").replace("## ", ""))

    def test_weekly_no_gh(self):
        r = run("tracker_weekly_update.py", [], tempfile.mkdtemp())
        self.assertEqual(r.returncode, 0)
        self.assertIn("NOT CHECKED", r.stdout)


class Install(unittest.TestCase):
    def install(self, d, *a):
        return subprocess.run(["bash", os.path.join(ROOT, "install.sh"), *a, d], capture_output=True, text=True)

    def test_block_idempotent_marker_and_replay(self):
        d = tempfile.mkdtemp()
        for _ in range(2):
            self.assertEqual(self.install(d, "--with-delivery", "--tracker-project", "ACME-PROJ").returncode, 0)
        ag = open(os.path.join(d, "AGENTS.md")).read()
        self.assertEqual(ag.count("<!-- dcr-tracker:begin -->"), 1)
        block = ag.split("<!-- dcr-tracker:begin -->")[1].split("<!-- dcr-tracker:end -->")[0]
        self.assertLessEqual(block.count("\n") + 2, 12)
        self.assertIn("linear", block)
        flags = open(os.path.join(d, ".claude/.dcr-install-flags")).read().split()
        self.assertEqual(flags, ["--with-delivery", "--tracker-project=ACME-PROJ", "--tracker=linear"])
        # replay of the marker lines yields the same block
        self.assertEqual(self.install(d, *flags).returncode, 0)
        self.assertEqual(open(os.path.join(d, "AGENTS.md")).read(), ag)

    def test_no_flag_no_block_and_bad_values_rejected(self):
        d = tempfile.mkdtemp()
        self.install(d)
        self.assertNotIn("dcr-tracker", open(os.path.join(d, "AGENTS.md")).read())
        self.assertEqual(self.install(d, "--tracker-project", "a b;c").returncode, 2)
        self.assertEqual(self.install(d, "--tracker-project", "X", "--tracker", "trello").returncode, 2)
        self.assertEqual(subprocess.run(["bash", os.path.join(ROOT, "install.sh"), d, "--tracker-project"]).returncode, 2)


if __name__ == "__main__":
    unittest.main()
