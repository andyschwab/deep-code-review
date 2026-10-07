#!/usr/bin/env python3
"""Tests for perun_doctor.py, perun_uninstall.py and install.sh default-on operating layer (temp repos)."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import perun_doctor, perun_uninstall  # noqa: E402

HAS_JQ = shutil.which("jq") is not None


def install(repo, *flags):
    return subprocess.run(["bash", str(ROOT / "install.sh"), *flags, str(repo)], capture_output=True, text=True)


def rows(repo, home):
    return {c: (s, d) for s, c, d in perun_doctor.check(Path(repo), Path(home))}


@unittest.skipUnless(HAS_JQ, "jq needed to apply the operating layer")
class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo, self.home = self.tmp / "r", self.tmp / "h"
        self.repo.mkdir(); self.home.mkdir()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_default_on_applies_layer_and_prints_summary(self):
        p = install(self.repo, "--with-delivery")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("What changed in", p.stdout)
        self.assertIn("perun_uninstall.py", p.stdout)
        self.assertIn("subagent_start_inject.py", (self.repo / ".claude/settings.local.json").read_text())
        self.assertEqual(rows(self.repo, self.home)["hooks wired"][0], "OK")

    def test_opt_out_leaves_no_settings(self):
        install(self.repo, "--with-delivery", "--no-operating-layer")
        self.assertFalse((self.repo / ".claude/settings.local.json").exists())
        self.assertEqual(rows(self.repo, self.home)["hooks wired"][0], "OK")  # opted out is not a failure

    def test_conflicting_flags_rejected(self):
        self.assertNotEqual(install(self.repo, "--with-delivery", "--apply-operating-layer", "--no-operating-layer").returncode, 0)

    def test_installed_but_never_runs(self):
        install(self.repo, "--with-delivery", "--no-operating-layer")
        (self.repo / ".claude/.dcr-install-flags").write_text("--with-delivery\n")  # not opted out, no hooks
        r = rows(self.repo, self.home)["hooks wired"]
        self.assertEqual(r[0], "FAIL")
        self.assertIn("never runs", r[1])

    def test_missing_hook_file_and_drift(self):
        install(self.repo, "--with-delivery")
        (self.repo / ".claude/skills/agentic-delivery/scripts/handback_cap.py").unlink()
        fork = self.repo / "tools"; fork.mkdir()
        shutil.copy(ROOT / ".claude/skills/agentic-delivery/scripts/lane_cap.py", fork / "lane_cap.py")
        (fork / "lane_cap.py").write_text("# forked\n")
        r = rows(self.repo, self.home)
        self.assertEqual(r["hook files exist"][0], "FAIL")
        self.assertIn("handback_cap.py", r["hook files exist"][1])
        self.assertEqual(r["drifted copies"][0], "WARN")
        self.assertIn("lane_cap.py", r["drifted copies"][1])

    def test_stale_versions_and_policy_janitor(self):
        install(self.repo, "--with-delivery")
        (self.repo / ".claude/skills/deep-code-review/VERSION").write_text("0.0.1\n")
        (self.home / ".claude/skills/deep-code-review").mkdir(parents=True)
        (self.home / ".claude/skills/deep-code-review/VERSION").write_text("0.0.2\n")
        r = rows(self.repo, self.home)
        self.assertEqual(r["installed version"][0], "WARN")
        self.assertEqual(r["global copy"][0], "WARN")
        self.assertEqual(r["policy file"][0], "WARN")
        self.assertEqual(r["janitor/scheduler"][0], "WARN")
        (self.repo / "perun-policy.json").write_text("{}")
        (self.repo / "scripts").mkdir()
        (self.repo / "scripts/janitor.sh").write_text("#!/bin/sh\n")
        r = rows(self.repo, self.home)
        self.assertEqual((r["policy file"][0], r["janitor/scheduler"][0]), ("OK", "OK"))

    def test_fix_repairs_stale_install(self):
        install(self.repo, "--with-delivery")
        (self.repo / ".claude/skills/agentic-delivery/scripts/handback_cap.py").write_text("# stale fork\n")
        (self.repo / ".claude/settings.local.json").unlink()
        rc = perun_doctor.main([str(self.repo), "--fix", "--home", str(self.home)])
        r = rows(self.repo, self.home)
        self.assertEqual((r["hooks wired"][0], r["hook files exist"][0]), ("OK", "OK"))
        self.assertTrue(list((self.repo / ".claude/skill-backups").glob("agentic-delivery-*")))  # fork preserved
        self.assertEqual(rc, 1)  # policy/janitor warnings remain: fix never invents them

    def test_uninstall_restores_backup_and_removes_hooks(self):
        orig = self.repo / ".claude/skills/deep-code-review"
        orig.mkdir(parents=True)
        (orig / "SKILL.md").write_text("mine\n")
        cfg = self.repo / ".claude/settings.local.json"
        cfg.write_text(json.dumps({"hooks": {"SubagentStart": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}, "env": {"KEEP": "1"}}))
        install(self.repo, "--with-delivery")
        install(self.repo, "--with-delivery")  # reinstall: a Perun copy lands in backups too
        perun_uninstall.run(self.repo, dry=True)
        self.assertTrue((self.repo / ".claude/skills/agentic-delivery").exists())  # dry run is inert
        perun_uninstall.run(self.repo)
        self.assertEqual((orig / "SKILL.md").read_text(), "mine\n")  # original, not a Perun copy, restored
        self.assertFalse((orig / "VERSION").exists())
        self.assertFalse((self.repo / ".claude/skills/agentic-delivery").exists())
        c = json.loads(cfg.read_text())
        self.assertEqual(c["hooks"], {"SubagentStart": [{"hooks": [{"type": "command", "command": "echo mine"}]}]})
        self.assertEqual(c["env"], {"KEEP": "1"})
        self.assertFalse((self.repo / ".claude/.dcr-install-flags").exists())


class NoJqTests(unittest.TestCase):
    def test_clean_unrelated_repo_reports_not_installed(self):
        with tempfile.TemporaryDirectory() as t:
            r = rows(t, t)
            self.assertEqual(r["installed version"][0], "FAIL")


if __name__ == "__main__":
    unittest.main()
