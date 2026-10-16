#!/usr/bin/env python3
"""Install UX regressions (temp repos only): doctor exit on a fresh install, bounded backups, complete uninstall."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import perun_doctor, perun_marker, perun_uninstall  # noqa: E402

HAS_JQ = shutil.which("jq") is not None
os.environ["DCR_NO_PROBE"] = "1"


def install(repo, *flags):
    p = subprocess.run(["bash", str(ROOT / "install.sh"), *flags, str(repo)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return p


def uninstall(repo, *a):
    return subprocess.run([sys.executable, str(ROOT / "scripts/perun_uninstall.py"), str(repo), *a], capture_output=True, text=True)


def tree(repo):
    return sorted(str(p.relative_to(repo)) for p in Path(repo).rglob("*"))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo, self.home = self.tmp / "r", self.tmp / "h"
        self.repo.mkdir(); self.home.mkdir()
        self.addCleanup(shutil.rmtree, self.tmp, True)


class DoctorFreshInstall(Base):
    def test_fresh_default_install_exits_zero(self):
        install(self.repo)
        self.assertEqual(perun_doctor.main([str(self.repo), "--home", str(self.home)]), 0)
        r = {c: s for s, c, _ in perun_doctor.check(self.repo, self.home)}
        self.assertEqual((r["janitor/scheduler"], r["policy file"]), ("INFO", "INFO"))  # optional add-ons: shown, never failing

    def test_real_problem_still_fails(self):
        install(self.repo)
        (self.repo / ".claude/skills/deep-code-review/VERSION").write_text("0.0.1\n")
        self.assertEqual(perun_doctor.main([str(self.repo), "--home", str(self.home)]), 1)


class BoundedBackups(Base):
    def backups(self, host=".claude"):
        d = self.repo / host / "skill-backups"
        return sorted(p.name for p in d.iterdir()) if d.is_dir() else []

    def test_unchanged_rerun_keeps_no_backup(self):
        install(self.repo)
        install(self.repo)
        install(self.repo)
        self.assertEqual([self.backups(h) for h in (".claude", ".cursor", ".agents")], [[], [], []])

    def test_changed_reruns_keep_only_the_latest_and_never_the_original(self):
        orig = self.repo / ".claude/skills/deep-code-review"
        orig.mkdir(parents=True)
        (orig / "SKILL.md").write_text("mine\n")  # pre-Perun copy: no VERSION file
        install(self.repo, "--minimal")
        first = self.backups()
        self.assertEqual(len(first), 1)
        for i in range(3):
            (orig / "SKILL.md").write_text(f"edit {i}\n")  # a changed copy each time, so each re-run has something to back up
            install(self.repo, "--minimal")
        left = self.backups()
        self.assertEqual(len(left), 2, left)  # the original plus ONE Perun backup
        self.assertIn(first[0], left)
        self.assertEqual((self.repo / ".claude/skill-backups" / first[0] / "SKILL.md").read_text(), "mine\n")

    def test_prune_ignores_foreign_dirs(self):
        install(self.repo, "--minimal")
        keep = self.repo / ".claude/skill-backups/deep-code-review-notes"
        keep.mkdir(parents=True)
        (keep / "VERSION").write_text("x\n")
        (self.repo / ".claude/skills/deep-code-review/SKILL.md").write_text("changed\n")
        install(self.repo, "--minimal")
        self.assertTrue(keep.is_dir())


@unittest.skipUnless(HAS_JQ, "jq needed to apply the operating layer")
class CompleteUninstall(Base):
    def run_cycle(self, *flags, pre=None):
        for rel, text in (pre or {}).items():
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / rel).write_text(text)
        before = tree(self.repo)
        install(self.repo, *flags)
        install(self.repo, *flags)  # re-run: marker must still cover everything
        p = uninstall(self.repo, "--apply")
        self.assertEqual(p.returncode, 0, p.stderr)
        return before, p

    def test_default_install_leaves_nothing(self):
        before, _ = self.run_cycle()
        self.assertEqual(tree(self.repo), before)

    def test_full_install_leaves_nothing(self):
        before, _ = self.run_cycle("--full")
        self.assertEqual(tree(self.repo), before)

    def test_preexisting_files_survive_untouched(self):
        pre = {"AGENTS.md": "# Mine\n\nkeep me\n", ".claude/settings.local.json": json.dumps({"model": "opus", "sandbox": {"enabled": False}}), ".claude/skills/deep-code-review/SKILL.md": "mine\n"}
        before, _ = self.run_cycle("--full", pre=pre)
        self.assertEqual((self.repo / "AGENTS.md").read_text(), "# Mine\n\nkeep me\n")
        self.assertEqual(json.loads((self.repo / ".claude/settings.local.json").read_text()), {"model": "opus", "sandbox": {"enabled": False}})
        self.assertEqual((self.repo / ".claude/skills/deep-code-review/SKILL.md").read_text(), "mine\n")  # original restored
        self.assertEqual(tree(self.repo), before)  # no .bak, no skill-backups, no empty dirs

    def test_user_changed_files_are_kept_and_listed(self):
        install(self.repo, "--full")
        (self.repo / ".claude/house-defaults.md").write_text("edited\n")
        (self.repo / ".claude/commands/review.md").write_text("edited\n")
        p = uninstall(self.repo, "--apply")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual((self.repo / ".claude/house-defaults.md").read_text(), "edited\n")
        self.assertTrue((self.repo / ".claude/commands/review.md").exists())

    def test_original_backup_kept_when_skill_not_restored(self):
        orig = self.repo / ".claude/skills/deep-code-review"
        orig.mkdir(parents=True)
        (orig / "SKILL.md").write_text("mine\n")
        install(self.repo, "--minimal")
        (orig / "my-notes.md").write_text("added\n")  # user file inside the skill dir: dir is not fully removed
        p = uninstall(self.repo, "--apply")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("original kept", p.stdout)
        kept = [b for b in (self.repo / ".claude/skill-backups").iterdir() if not (b / "VERSION").exists()]
        self.assertEqual((kept[0] / "SKILL.md").read_text(), "mine\n")

    def test_marker_path_outside_repo_is_refused(self):
        install(self.repo, "--minimal")
        victim = self.tmp / "victim.txt"
        victim.write_text("precious\n")
        m = json.loads((self.repo / perun_marker.MARKER).read_text())
        m["files"]["../victim.txt"] = perun_marker.sha(victim)
        (self.repo / perun_marker.MARKER).write_text(json.dumps(m))
        p = uninstall(self.repo, "--apply")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("outside", p.stderr)
        self.assertEqual(victim.read_text(), "precious\n")
        self.assertTrue((self.repo / ".claude/skills/deep-code-review").exists())  # nothing else touched

    def test_symlinked_parent_is_refused(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "f.txt").write_text("precious\n")
        (self.repo / "link").symlink_to(outside)
        self.assertFalse(perun_uninstall.inside(self.repo, "link/f.txt"))
        self.assertFalse(perun_uninstall.inside(self.repo, "/etc/hosts"))
        self.assertTrue(perun_uninstall.inside(self.repo, ".claude/x"))


class SettingsTree(unittest.TestCase):
    def test_added_and_strip_roundtrip(self):
        have = {"sandbox": {"enabled": False, "network": {"allowedDomains": ["mine.example.com"]}}, "permissions": {"deny": ["Bash(a)"]}}
        tpl = {"sandbox": {"enabled": True, "x": 1, "network": {"allowedDomains": ["mine.example.com", "github.com"]}}, "permissions": {"deny": ["Bash(a)", "Bash(b)"], "allow": ["Bash(c)"]}}
        add = perun_marker.added(have["sandbox"], tpl["sandbox"]), perun_marker.added(have["permissions"], tpl["permissions"])
        self.assertEqual(add[0], {"x": 1, "network": {"allowedDomains": ["github.com"]}})  # existing enabled=False wins: not recorded
        self.assertEqual(add[1], {"deny": ["Bash(b)"], "allow": ["Bash(c)"]})
        now = {"sandbox": {"enabled": False, "x": 1, "network": {"allowedDomains": ["mine.example.com", "github.com"]}}, "permissions": {"deny": ["Bash(a)", "Bash(b)"], "allow": ["Bash(c)"]}}
        perun_uninstall.strip(now["sandbox"], add[0]); perun_uninstall.strip(now["permissions"], add[1])
        self.assertEqual(now, have)


if __name__ == "__main__":
    unittest.main()
