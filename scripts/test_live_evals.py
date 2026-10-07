#!/usr/bin/env python3
"""Offline tests for live_evals.py: a stub OpenAI-compatible HTTP server on loopback, no other network."""
import http.server
import json
import os
import subprocess
import sys
import threading
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SCRIPT = SCRIPTS / "live_evals.py"
sys.path.insert(0, str(SCRIPTS))
import live_evals as le  # noqa: E402

KEY = "sk-test-secret-123"
SEEN = []


class Stub(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append((self.path, self.headers.get("Authorization"), body))
        sysmsg = body["messages"][0]["content"]
        # routing prompt -> NONE; judge prompt -> PASS; else a refusal-ish answer
        reply = "NONE" if "route a user task" in sysmsg else "PASS" if "grade an assistant" in sysmsg else (SCRIPTS / "eval-fixtures/positioning/refuses-fabricated-market-facts/good.txt").read_text()
        fin = "length" if body["max_tokens"] < 100 else "stop"
        out = json.dumps({"choices": [{"message": {"content": reply}, "finish_reason": fin}], "usage": {"total_tokens": 50}}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


class LiveEvals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def cli(self, *args, **env):
        e = {**os.environ, "LLM_BASE_URL": self.base, "LLM_API_KEY": KEY, "LLM_MODEL": "m1", **env}
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=e)

    def test_report_and_no_key_leak(self):
        r = self.cli("--budget-tokens", "100000", "--skill", "positioning", "--per-skill", "2", LLM_JUDGE_MODEL="j1")
        self.assertIn(r.returncode, (0, 1), r.stderr)
        rep = json.loads(r.stdout)
        self.assertEqual(rep["subject_model"], "m1")
        self.assertGreater(rep["graded"], 0)
        self.assertEqual({c["kind"] for c in rep["cases"]}, {"refusal", "trigger"})
        self.assertNotIn(KEY, r.stdout + r.stderr)
        self.assertTrue(all(a == f"Bearer {KEY}" and p == "/v1/chat/completions" for p, a, _ in SEEN))

    def test_hard_predicate_grades_without_judge(self):
        r = self.cli("--budget-tokens", "100000", "--skill", "positioning", "--per-skill", "1")
        c = next(c for c in json.loads(r.stdout)["cases"] if c["kind"] == "refusal")
        self.assertEqual((c["grader"], c["result"]), ("predicate", "pass"))

    def test_budget_fails_closed(self):
        n = len(SEEN)
        r = self.cli("--budget-tokens", "100", "--skill", "positioning")
        self.assertEqual(r.returncode, 3)
        self.assertEqual(len(SEEN), n, "no call may be made when the worst case exceeds the budget")
        self.assertIsNotNone(json.loads(r.stdout)["stopped_budget"])

    def test_config_errors(self):
        self.assertEqual(self.cli("--budget-tokens", "0").returncode, 2)
        self.assertEqual(self.cli("--budget-tokens", "10", LLM_API_KEY="").returncode, 2)
        self.assertEqual(self.cli("--budget-tokens", "10", LLM_JUDGE_MODEL="m1").returncode, 2)

    def test_truncated_is_invalid_not_fail(self):
        r = self.cli("--budget-tokens", "100000", "--skill", "positioning", "--per-skill", "1", "--max-tokens", "50")
        rep = json.loads(r.stdout)
        self.assertEqual(rep["graded"], 0)
        self.assertEqual(rep["truncated"], rep["total"])
        self.assertTrue(all(c["result"] == "invalid" and c["finish_reason"] == "length" for c in rep["cases"]))
        self.assertEqual(r.returncode, 0)

    def test_default_max_tokens_6000(self):
        self.cli("--budget-tokens", "100000", "--skill", "positioning", "--per-skill", "1")
        self.assertEqual(SEEN[-1][2]["max_tokens"], 6000)

    def test_trigger_grading(self):
        self.assertTrue(le.grade_trigger("idea-critic", "idea-critic", True))
        self.assertTrue(le.grade_trigger("<think>idea-critic?</think>NONE", "idea-critic", False))
        self.assertFalse(le.grade_trigger("NONE", "idea-critic", True))


if __name__ == "__main__":
    unittest.main()
