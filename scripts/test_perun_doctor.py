#!/usr/bin/env python3
"""Tests for perun_doctor.py, perun_uninstall.py and install.sh default-on operating layer (temp repos)."""
import contextlib, io, json, os, shutil, subprocess, sys, tempfile, unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import perun_doctor  # noqa: E402

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

    def test_install_ends_with_three_plain_lines(self):
        p = install(self.repo, "--with-delivery")
        last = p.stdout.rstrip("\n").split("\n")[-3:]
        self.assertRegex(last[0], r"^Perun installed \d+ skill\(s\) into \d+ tool folder\(s\)")
        self.assertIn("Next, run this one command", last[1])
        self.assertIn("perun_doctor.py", last[1])
        self.assertIn("To undo everything", last[2])
        self.assertIn("perun_uninstall.py", last[2])

    def test_doctor_leads_with_verdict(self):
        install(self.repo, "--with-delivery")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            perun_doctor.main([str(self.repo), "--home", str(self.home)])
        first = out.getvalue().splitlines()[0]
        self.assertRegex(first, r"^(Healthy|\d+ things? needs? attention: )")
        (self.repo / ".claude/skills/agentic-delivery/scripts/handback_cap.py").unlink()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            perun_doctor.main([str(self.repo), "--home", str(self.home)])
        self.assertRegex(out.getvalue().splitlines()[0], r"^\d+ things? needs? attention: run python3 .*--fix")

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

    def _break(self):
        (self.repo / ".claude/skills/agentic-delivery/scripts/handback_cap.py").write_text("# stale fork\n")
        (self.repo / ".claude/settings.local.json").unlink()

    def test_fix_needs_confirmation(self):
        install(self.repo, "--with-delivery")
        self._break()
        with mock.patch("sys.stdin.isatty", return_value=False):  # no TTY, no --yes: refuse, change nothing
            self.assertEqual(perun_doctor.main([str(self.repo), "--fix", "--home", str(self.home)]), 2)
        self.assertFalse((self.repo / ".claude/settings.local.json").exists())
        with mock.patch("sys.stdin.isatty", return_value=True), mock.patch("builtins.input", return_value="y"):
            self.assertEqual(perun_doctor.main([str(self.repo), "--fix", "--home", str(self.home)]), 2)
        self.assertFalse((self.repo / ".claude/settings.local.json").exists())
        with mock.patch("sys.stdin.isatty", return_value=True), mock.patch("builtins.input", return_value="yes"):
            perun_doctor.main([str(self.repo), "--fix", "--home", str(self.home)])
        self.assertEqual(rows(self.repo, self.home)["hooks wired"][0], "OK")

    def test_fix_yes_warns_repairs_and_previews_default_on(self):
        install(self.repo, "--with-delivery")
        self._break()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = perun_doctor.main([str(self.repo), "--fix", "--yes", "--home", str(self.home)])
        self.assertIn("without an interactive confirmation", err.getvalue())
        self.assertIn("Default-on operating layer", out.getvalue())
        self.assertIn("model:", out.getvalue())
        r = rows(self.repo, self.home)
        self.assertEqual((r["hooks wired"][0], r["hook files exist"][0]), ("OK", "OK"))
        self.assertTrue(list((self.repo / ".claude/skill-backups").glob("agentic-delivery-*")))  # fork preserved
        self.assertEqual(rc, 1)  # policy/janitor warnings remain: fix never invents them

    def test_fix_fails_loudly_when_reinstall_fails(self):
        install(self.repo, "--with-delivery")
        self._break()
        err = io.StringIO()
        with mock.patch("subprocess.run", return_value=mock.Mock(returncode=1)), contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            rc = perun_doctor.main([str(self.repo), "--fix", "--yes", "--home", str(self.home)])
        self.assertEqual(rc, 2)
        self.assertIn("update-installed.sh failed", err.getvalue())

    def test_bak_is_timestamped_never_overwritten(self):
        cfg = self.repo / ".claude/settings.local.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(json.dumps({"mine": 1}))
        install(self.repo, "--with-delivery")
        c = json.loads(cfg.read_text()); c["hooks"].pop("PreToolUse"); cfg.write_text(json.dumps(c))
        install(self.repo, "--with-delivery")
        baks = sorted(cfg.parent.glob("settings.local.json.bak.*"))
        self.assertEqual(len(baks), 2)
        self.assertEqual(json.loads(baks[0].read_text()), {"mine": 1})  # first backup survived the second install

    def test_summary_names_model_pin(self):
        self.assertIn("sonnet, set only if you had none", install(self.repo, "--with-delivery").stdout)
        r2 = self.tmp / "r2"; r2.mkdir(); (r2 / ".claude").mkdir()
        (r2 / ".claude/settings.local.json").write_text('{"model": "opus"}')
        self.assertIn("your existing model kept", install(r2, "--with-delivery").stdout)


@unittest.skipUnless(HAS_JQ, "jq needed to apply the operating layer")
class UninstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "r"
        self.repo.mkdir()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = self.repo / ".claude/settings.local.json"

    def cli(self, *a):
        return subprocess.run([sys.executable, str(ROOT / "scripts/perun_uninstall.py"), str(self.repo), *a], capture_output=True, text=True)

    def test_dry_run_is_default_and_inert(self):
        install(self.repo, "--with-delivery")
        before = self.cfg.read_text()
        p = self.cli()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("dry run", p.stdout)
        self.assertEqual(self.cfg.read_text(), before)
        self.assertTrue((self.repo / ".claude/skills/agentic-delivery").exists())
        self.assertTrue((self.repo / ".claude/.perun-install.json").exists())

    def test_apply_restores_backup_keeps_user_files_and_foreign_hooks(self):
        orig = self.repo / ".claude/skills/deep-code-review"
        orig.mkdir(parents=True)
        (orig / "SKILL.md").write_text("mine\n")
        self.cfg.write_text(json.dumps({"hooks": {"SubagentStart": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}, "env": {"KEEP": "1"}}))
        install(self.repo, "--with-delivery")
        install(self.repo, "--with-delivery")  # reinstall: a Perun copy lands in backups too
        ad = self.repo / ".claude/skills/agentic-delivery"
        (ad / "my-notes.md").write_text("user file\n")                         # added by user: kept
        (ad / "SKILL.md").write_text((ad / "SKILL.md").read_text() + "\nedit\n")  # edited: kept
        p = self.cli("--apply")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("my-notes.md", p.stdout)
        self.assertEqual((ad / "my-notes.md").read_text(), "user file\n")
        self.assertTrue((ad / "SKILL.md").exists())
        self.assertFalse((ad / "references").exists())  # untouched installed files are gone
        self.assertEqual((orig / "SKILL.md").read_text(), "mine\n")  # fully removed dir -> original restored
        self.assertFalse((orig / "VERSION").exists())
        c = json.loads(self.cfg.read_text())
        self.assertEqual(c["hooks"], {"SubagentStart": [{"hooks": [{"type": "command", "command": "echo mine"}]}]})
        self.assertEqual(c["env"], {"KEEP": "1"})
        self.assertNotIn("model", c)  # Perun set it, so it is reverted
        self.assertFalse((self.repo / ".claude/.perun-install.json").exists())

    def test_preexisting_model_and_identical_hook_are_kept(self):
        t = json.loads((ROOT / ".claude/skills/agentic-delivery/templates/operating-layer.settings.json").read_text())
        self.cfg.parent.mkdir(parents=True)
        self.cfg.write_text(json.dumps({"model": "opus", "hooks": {"PreToolUse": t["hooks"]["PreToolUse"]}}))
        install(self.repo, "--with-delivery")
        self.assertEqual(self.cli("--apply").returncode, 0)
        c = json.loads(self.cfg.read_text())
        self.assertEqual(c["model"], "opus")
        self.assertEqual(c["hooks"], {"PreToolUse": t["hooks"]["PreToolUse"]})  # was yours before install: not removed by template equality
        self.assertNotIn("SubagentStart", c["hooks"])

    def test_invalid_settings_abort_with_no_change(self):
        install(self.repo, "--with-delivery")
        self.cfg.write_text("{not json")
        p = self.cli("--apply")
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(self.cfg.read_text(), "{not json")
        self.assertTrue((self.repo / ".claude/skills/agentic-delivery").exists())  # nothing else touched
        self.assertFalse(list(self.cfg.parent.glob("*.perun-tmp")))

    def test_no_marker_removes_nothing(self):
        install(self.repo, "--with-delivery")
        (self.repo / ".claude/.perun-install.json").unlink()
        p = self.cli("--apply")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("marker", p.stderr)
        self.assertTrue((self.repo / ".claude/skills/agentic-delivery").exists())


class NoJqTests(unittest.TestCase):
    def test_clean_unrelated_repo_reports_not_installed(self):
        with tempfile.TemporaryDirectory() as t:
            r = rows(t, t)
            self.assertEqual(r["installed version"][0], "FAIL")


if __name__ == "__main__":
    unittest.main()
