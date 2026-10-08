"""Tests for perun_policy.py set/skip-ci, install.sh --policy, and the preamble/policy agreement."""
import json, os, re, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PP = ROOT / ".claude/skills/agentic-delivery/scripts/perun_policy.py"
PRE = (ROOT / ".claude/skills/agentic-delivery/templates/lane-preamble.md").read_text()
ENV = {k: v for k, v in os.environ.items() if k != "PERUN_POLICY"}


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=ENV)


class PolicyUx(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def pp(self, *a):
        return run([sys.executable, str(PP), *a], self.d)

    def test_set_creates_validates_and_prints(self):
        r = self.pp("set", "github_actions", "off")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["github_actions"], "off")
        self.assertEqual(json.loads((Path(self.d) / ".perun/policy.json").read_text()), {"github_actions": "off"})
        self.assertEqual(self.pp("get", "github_actions").stdout.strip(), "off")
        self.assertEqual(self.pp("skip-ci").stdout.strip(), "[skip ci]")
        self.assertEqual(self.pp("set", "tokens", "500").returncode, 0)
        self.assertEqual(self.pp("get", "tokens").stdout.strip(), "500")

    def test_set_rejects_bad_input_and_keeps_file(self):
        self.pp("set", "local_cpu", "maximize")
        for a in (("tokens", "lots"), ("nope", "1"), ("share_learnings", "yes")):
            self.assertEqual(self.pp("set", *a).returncode, 2, a)
        self.assertEqual(self.pp("get", "local_cpu").stdout.strip(), "maximize")
        self.assertEqual(self.pp("skip-ci").stdout.strip(), "")

    def test_preamble_agrees_with_tokens_and_ci_policy(self):
        self.assertEqual(self.pp("get", "tokens").stdout.strip(), "efficient")
        self.assertIn("`efficient` (default) means the cheapest model tier that fits, at most 2 parallel lanes, "
                      "no duplicate review passes, terse hand-backs", PRE)
        self.assertIn("perun_policy.py get tokens", PRE)
        self.assertRegex(PRE, r"`off`, end every commit message you push with `\[skip ci\]`")

    def test_install_policy_flag(self):
        t = tempfile.mkdtemp()
        r = run(["bash", str(ROOT / "install.sh"), "--policy", "local_cpu=maximize,github_actions=off,share_learnings=auto", t], ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads((Path(t) / ".perun/policy.json").read_text()),
                         {"local_cpu": "maximize", "github_actions": "off", "share_learnings": "auto"})
        self.assertRegex(r.stdout, r'Policy: \{.*"github_actions": "off"')
        bad = run(["bash", str(ROOT / "install.sh"), "--policy", "tokens=lots", tempfile.mkdtemp()], ROOT)
        self.assertEqual(bad.returncode, 2)

    def test_perun_run_auto_shares_after_policy_check(self):
        s = (ROOT / "commands/perun-run.md").read_text()
        self.assertRegex(s, r"get share_learnings` prints `auto`.*share_learning\.py.*--send")


if __name__ == "__main__":
    unittest.main()
