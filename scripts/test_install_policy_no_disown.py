#!/usr/bin/env python3
"""install.sh's own `--policy k=v` must not disown the policy file; only a user-run `perun_policy set` does.

Each case installs into a fresh dir under $TMPDIR-style temp. Fixture names are fictional.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY_PY = ROOT / ".claude/skills/agentic-delivery/scripts/perun_policy.py"


@unittest.skipUnless(shutil.which("jq") and shutil.which("bash"), "install.sh needs jq and bash")
class NoDisown(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="no-disown-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.env = {**{k: v for k, v in os.environ.items() if k not in ("PERUN_POLICY", "PERUN_ROLE")},
                    "DCR_NO_PROBE": "1", "CLAUDE_CONFIG_DIR": str(self.tmp / "home")}
        self.target = self.tmp / "app"
        (self.target / ".claude").mkdir(parents=True)
        (self.tmp / "home").mkdir()
        (self.target / ".claude/settings.local.json").write_text("{}")

    def install(self, *flags):
        p = subprocess.run(["bash", str(ROOT / "install.sh"), "--with-delivery", "--apply-operating-layer", *flags, str(self.target)],
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)

    def uninstall(self):
        p = subprocess.run(["python3", str(ROOT / "scripts/perun_uninstall.py"), str(self.target), "--apply"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_install_policy_flag_then_uninstall_is_clean(self):
        self.install("--policy", "statusline=off")
        self.uninstall()
        self.assertFalse((self.target / ".perun").exists())

    def test_reinstall_with_same_policy_flag_then_uninstall_is_clean(self):
        self.install("--policy", "statusline=off")
        self.install("--policy", "statusline=off")  # same bytes: a disown here would make uninstall keep the file
        self.uninstall()
        self.assertFalse((self.target / ".perun").exists())

    def test_user_set_still_disowns(self):
        self.install("--policy", "statusline=off")
        subprocess.run(["python3", str(POLICY_PY), "set", "statusline", "off"], cwd=self.target, env=self.env, check=True, capture_output=True)
        self.uninstall()
        self.assertEqual(json.loads((self.target / ".perun/policy.json").read_text())["statusline"], "off")

    def test_disown_leaves_no_tmp_marker(self):
        self.install()
        subprocess.run(["python3", str(POLICY_PY), "set", "statusline", "off"], cwd=self.target, env=self.env, check=True, capture_output=True)
        marker = self.target / ".claude/.perun-install.json"
        self.assertNotIn("policy_sha", json.loads(marker.read_text()))
        self.assertEqual([p.name for p in marker.parent.glob(".perun-install.json*")], [".perun-install.json"])


if __name__ == "__main__":
    unittest.main()
