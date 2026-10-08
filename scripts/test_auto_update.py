#!/usr/bin/env python3
"""Tests for perun_auto_update.py and its install.sh wiring. Offline: the "remote" is a local git repo
with release tags under $TMPDIR, and its update-installed.sh is a stub that records how it was called."""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time, unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AD = ROOT / ".claude/skills/agentic-delivery/scripts"
sys.path.insert(0, str(AD))
import perun_auto_update as au  # noqa: E402

STUB = """#!/usr/bin/env bash
# Fake update-installed.sh: record the call instead of installing.
printf '%s %s\\n' "${DCR_NO_PULL:-}" "$(cat "$(dirname "$0")/../TAGNAME")" >> "$1/.claude/ran"
"""


def sh(*a, cwd=None):
    subprocess.run(a, cwd=cwd, check=True, capture_output=True)


def fake_remote(base: Path, tags=("v1.2.0", "v1.9.0", "v1.10.0")) -> Path:
    r = base / "remote"
    (r / "scripts").mkdir(parents=True)
    (r / "scripts/update-installed.sh").write_text(STUB)
    sh("git", "init", "-q", str(r))
    for t in tags:
        (r / "TAGNAME").write_text(t)
        sh("git", "add", "-A", cwd=r)
        sh("git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", t, cwd=r)
        sh("git", "tag", t, cwd=r)
    sh("git", "tag", "not-a-release", cwd=r)
    return r


def fake_installed(base: Path, remote: Path, version="1.2.0") -> Path:
    t = base / "proj"
    skill = t / ".claude/skills/deep-code-review"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("name: deep-code-review\n")
    sh("git", "init", "-q", str(t))
    marker = {"version": version, "remote": str(remote),
              "skills": {".claude/skills/deep-code-review": {"SKILL.md": hashlib.sha256(b"name: deep-code-review\n").hexdigest()}}}
    (t / ".claude/.perun-install.json").write_text(json.dumps(marker))
    return t


class AutoUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["XDG_CACHE_HOME"] = str(self.tmp / "cache")
        os.environ.pop("PERUN_POLICY", None)
        self.remote = fake_remote(self.tmp)
        self.proj = fake_installed(self.tmp, self.remote)

    def log(self):
        f = au.cache() / "auto-update.log"
        return f.read_text() if f.is_file() else ""

    def test_newer_tag_applies_newest_semver_tag_via_update_installed(self):
        self.assertEqual(au.run(self.proj), 0)
        self.assertEqual((self.proj / ".claude/ran").read_text(), "1 v1.10.0\n")  # 1.10 > 1.9, DCR_NO_PULL=1
        self.assertIn("updated 1.2.0 -> v1.10.0", self.log())

    def test_up_to_date_does_nothing(self):
        proj = fake_installed(self.tmp / "b", self.remote, version="1.10.0")
        self.assertEqual(au.run(proj), 0)
        self.assertFalse((proj / ".claude/ran").exists())
        self.assertIn("up to date at 1.10.0", self.log())

    def test_merge_and_train_locks_skip_and_log(self):
        for lock in ("MERGE_HEAD", "train-land.lock"):
            proj = fake_installed(self.tmp / lock, self.remote)
            (proj / ".git" / lock).mkdir()
            self.assertEqual(au.run(proj), 0)
            self.assertFalse((proj / ".claude/ran").exists())
            self.assertIn(f"skip: {lock} present", self.log())

    def test_dirty_managed_file_skips_and_logs(self):
        (self.proj / ".claude/skills/deep-code-review/SKILL.md").write_text("edited by the user\n")
        self.assertEqual(au.run(self.proj), 0)
        self.assertFalse((self.proj / ".claude/ran").exists())
        self.assertIn("skip: dirty Perun-managed file .claude/skills/deep-code-review/SKILL.md", self.log())

    def test_marker_without_remote_is_a_logged_skip(self):
        (self.proj / ".claude/.perun-install.json").write_text('{"version": "1.2.0"}')
        self.assertEqual(au.run(self.proj), 0)
        self.assertIn("no remote or version", self.log())

    @mock.patch.object(au.subprocess, "Popen")
    def test_throttle_runs_at_most_once_per_6h(self, popen):
        self.assertTrue(au.hook(self.proj))
        self.assertFalse(au.hook(self.proj))
        self.assertFalse(au.hook(self.proj, now=time.time() + 5 * 3600))
        self.assertTrue(au.hook(self.proj, now=time.time() + 7 * 3600))
        self.assertEqual(popen.call_count, 2)
        self.assertTrue(popen.call_args.kwargs["start_new_session"])  # detached from the session

    @mock.patch.object(au.subprocess, "Popen")
    def test_policy_off_never_spawns(self, popen):
        (self.proj / ".perun").mkdir()
        (self.proj / ".perun/policy.json").write_text('{"auto_update": "off"}')
        self.assertFalse(au.hook(self.proj))
        self.assertFalse(au.stamp(self.proj).exists())
        popen.assert_not_called()

    def test_malformed_policy_fails_closed(self):
        (self.proj / ".perun").mkdir()
        (self.proj / ".perun/policy.json").write_text('{"auto_update": "sometimes"}')
        self.assertFalse(au.hook(self.proj))

    def test_hook_returns_fast_and_the_detached_worker_still_updates(self):
        slow = self.tmp / "bin"
        slow.mkdir()
        real = shutil.which("git")
        (slow / "git").write_text(f"#!/bin/sh\nsleep 2\nexec {real} \"$@\"\n")
        (slow / "git").chmod(0o755)
        env = {**os.environ, "PATH": f"{slow}:{os.environ['PATH']}", "CLAUDE_PROJECT_DIR": str(self.proj)}
        t0 = time.monotonic()
        p = subprocess.run([sys.executable, str(AD / "perun_auto_update.py")], env=env, capture_output=True, text=True)
        elapsed = time.monotonic() - t0
        self.assertEqual((p.returncode, p.stdout), (0, ""))
        self.assertLess(elapsed, 0.3, f"hook took {elapsed:.3f}s")
        deadline = time.monotonic() + 60  # the worker waits on the slow git several times
        while time.monotonic() < deadline and "updated" not in self.log():
            time.sleep(0.2)
        self.assertIn("updated 1.2.0 -> v1.10.0", self.log())


@unittest.skipUnless(shutil.which("jq"), "jq needed to apply the operating layer")
class InstallWiringTests(unittest.TestCase):
    def install(self, repo, *flags):
        env = {**os.environ, "PERUN_REMOTE": "https://example.com/perun.git"}
        return subprocess.run(["bash", str(ROOT / "install.sh"), *flags, str(repo)], capture_output=True, text=True, env=env)

    def test_operating_layer_wires_hooks_and_marker_records_version_and_remote(self):
        repo = Path(tempfile.mkdtemp())
        p = self.install(repo, "--with-delivery")
        self.assertEqual(p.returncode, 0, p.stderr)
        hooks = json.loads((repo / ".claude/settings.local.json").read_text())["hooks"]
        for ev in ("SessionStart", "UserPromptSubmit"):
            self.assertIn("perun_auto_update.py", json.dumps(hooks[ev]))
        m = json.loads((repo / ".claude/.perun-install.json").read_text())
        self.assertEqual(m["remote"], "https://example.com/perun.git")
        self.assertEqual(m["version"], (ROOT / ".claude/skills/deep-code-review/VERSION").read_text().strip())
        self.assertNotIn("restart your", p.stdout.lower())
        self.assertIn("without a restart", p.stdout)
        self.assertFalse((repo / ".perun/policy.json").exists())

    def test_no_auto_update_turns_policy_off_and_keeps_other_keys(self):
        repo = Path(tempfile.mkdtemp())
        (repo / ".perun").mkdir()
        (repo / ".perun/policy.json").write_text('{"tokens": 5}')
        p = self.install(repo, "--no-auto-update")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads((repo / ".perun/policy.json").read_text()), {"tokens": 5, "auto_update": "off"})
        self.assertIn("--no-auto-update", (repo / ".claude/.dcr-install-flags").read_text())


if __name__ == "__main__":
    unittest.main()
