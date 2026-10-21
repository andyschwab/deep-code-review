#!/usr/bin/env python3
"""Replay: an applied operating-layer install arms ceo_altitude_guard.py (role ceo, warn) by default.

Bug: the policy default role is `off`, so the guard counted but never warned even when installed. Each case installs
into a fresh temp repo and runs the installed hook command as the host wires it (no PERUN_ROLE, no PERUN_POLICY).
Fixture paths are fictional (/work/acme-app).
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTICE = "CEO-altitude guard now warns (role=ceo); opt out: perun_policy set role off"
DELEGATE = "delegate: spawn a lane with the brief"


@unittest.skipUnless(shutil.which("jq") and shutil.which("bash"), "install.sh needs jq and bash")
class DefaultWarn(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-default-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def env(self, **extra):
        base = {k: v for k, v in os.environ.items() if k not in ("PERUN_POLICY", "PERUN_ROLE")}
        return {**base, "DCR_NO_PROBE": "1", "CLAUDE_CONFIG_DIR": str(self.tmp / "home"), **extra}

    def install(self, name, *flags, **env):
        target = self.tmp / name
        (target / ".claude").mkdir(parents=True, exist_ok=True)
        (self.tmp / "home").mkdir(exist_ok=True)
        (target / ".claude/settings.local.json").write_text("{}")
        p = subprocess.run(["bash", str(ROOT / "install.sh"), "--with-delivery", "--apply-operating-layer", *flags, str(target)],
                           capture_output=True, text=True, env=self.env(**env))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.out = p.stdout
        return target

    def second_edit_output(self, target):
        hooks = json.loads((target / ".claude/settings.local.json").read_text())["hooks"]["PreToolUse"]
        cmd = next(h["command"] for e in hooks for h in e["hooks"] if "ceo_altitude_guard.py" in h["command"])
        env = self.env(CLAUDE_PROJECT_DIR=str(target), PERUN_CEO_DIR=str(self.tmp / "state"))
        out = ""
        for _ in range(2):  # the 2nd direct source edit in one turn is the first flag
            payload = {"session_id": "s1", "prompt_id": "p1", "hook_event_name": "PreToolUse", "cwd": str(target),
                       "tool_name": "Edit", "tool_input": {"file_path": "/work/acme-app/x.py"}}
            p = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, env=env, cwd=target,
                               input=json.dumps(payload))
            self.assertEqual(p.returncode, 0, p.stderr)
            out = p.stdout
        return out

    def test_fresh_install_warns_on_second_main_session_edit(self):
        target = self.install("fresh")
        self.assertEqual(json.loads((target / ".perun/policy.json").read_text())["role"], "ceo")
        self.assertIn(NOTICE, self.out)
        self.assertIn(DELEGATE, self.second_edit_output(target))

    def test_role_off_stays_silent(self):
        target = self.install("off", "--policy", "role=off")
        self.assertEqual(self.second_edit_output(target), "")

    def test_existing_policy_role_is_kept(self):
        target = self.tmp / "keep"
        (target / ".perun").mkdir(parents=True)
        (target / ".perun/policy.json").write_text('{"role": "off"}')
        self.install("keep")
        self.assertEqual(json.loads((target / ".perun/policy.json").read_text())["role"], "off")
        self.assertNotIn(NOTICE, self.out)

    def test_env_role_at_install_writes_no_role(self):
        target = self.install("env", PERUN_ROLE="off")
        policy = target / ".perun/policy.json"
        self.assertNotIn("role", json.loads(policy.read_text()) if policy.exists() else {})
        self.assertNotIn(NOTICE, self.out)

    def test_policy_flag_role_prints_no_notice(self):
        self.install("flag", "--policy", "role=ceo-strict")
        self.assertNotIn(NOTICE, self.out)

    def uninstall(self, target):
        p = subprocess.run(["python3", str(ROOT / "scripts/perun_uninstall.py"), str(target), "--apply"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p

    def test_uninstall_removes_the_policy_install_created(self):
        target = self.install("gone")
        self.uninstall(target)
        self.assertFalse((target / ".perun").exists())

    def test_uninstall_keeps_the_users_policy_and_only_drops_the_armed_role(self):
        target = self.tmp / "mine"
        (target / ".perun").mkdir(parents=True)
        (target / ".perun/policy.json").write_text('{"statusline": "off"}')
        self.install("mine")
        self.uninstall(target)
        self.assertEqual(json.loads((target / ".perun/policy.json").read_text()), {"statusline": "off"})

    def test_uninstall_leaves_a_role_the_user_set(self):
        target = self.tmp / "theirs"
        (target / ".perun").mkdir(parents=True)
        (target / ".perun/policy.json").write_text('{"role": "ceo-strict"}')
        self.install("theirs")
        self.uninstall(target)
        self.assertEqual(json.loads((target / ".perun/policy.json").read_text()), {"role": "ceo-strict"})

    def test_uninstall_keeps_a_policy_the_user_edited_after_install_byte_for_byte(self):
        target = self.install("edited")
        text = '{"role": "ceo", "statusline": "off"}'
        (target / ".perun/policy.json").write_text(text)
        p = self.uninstall(target)
        self.assertEqual((target / ".perun/policy.json").read_text(), text)
        self.assertIn("kept: changed since install", p.stdout)

    def test_uninstall_keeps_a_role_the_user_re_set_after_install(self):
        target = self.install("reset")
        text = '{"role":"ceo"}'  # same value install armed, different bytes: the user rewrote it
        (target / ".perun/policy.json").write_text(text)
        p = self.uninstall(target)
        self.assertEqual((target / ".perun/policy.json").read_text(), text)
        self.assertIn("kept: changed since install", p.stdout)

    def test_uninstall_keeps_a_policy_the_user_set_with_perun_policy_even_if_bytes_match(self):
        target = self.install("explicit")
        before = (target / ".perun/policy.json").read_text()
        env = {k: v for k, v in os.environ.items() if k != "PERUN_POLICY"}
        subprocess.run(["python3", str(ROOT / ".claude/skills/agentic-delivery/scripts/perun_policy.py"), "set", "role", "ceo"],
                       cwd=target, env=env, check=True, capture_output=True)
        self.assertEqual((target / ".perun/policy.json").read_text(), before)  # byte-identical: only the marker can tell
        p = self.uninstall(target)
        self.assertEqual((target / ".perun/policy.json").read_text(), before)
        self.assertIn("kept: changed since install", p.stdout)

    def test_uninstall_removes_an_added_role_from_an_unchanged_policy(self):
        target = self.tmp / "added"
        (target / ".perun").mkdir(parents=True)
        (target / ".perun/policy.json").write_text('{"statusline": "off"}')
        self.install("added")
        p = self.uninstall(target)
        self.assertNotIn("kept:", p.stdout)
        self.assertEqual(json.loads((target / ".perun/policy.json").read_text()), {"statusline": "off"})


if __name__ == "__main__":
    unittest.main()
