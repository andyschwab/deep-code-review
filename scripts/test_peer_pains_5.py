#!/usr/bin/env python3
"""Peer-pains 5: default house-defaults file, selfcheck RED/heavy-slot WARN, SIGPIPE-safe skip-ci scan, idle-aware heavy admission."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AD = ROOT / ".claude/skills/agentic-delivery/scripts"
sys.path.insert(0, str(AD))
import host_probe  # noqa: E402
import operating_selfcheck as sc  # noqa: E402
import perun_policy  # noqa: E402

HOOK = {"hooks": {"SubagentStart": [{"hooks": [{"type": "command", "command":
        'HOUSE_DEFAULTS_FILE="$CLAUDE_PROJECT_DIR/.claude/house-defaults.md" python3 x/subagent_start_inject.py'}]}]}}


def sh(*a, **kw):
    return subprocess.run(list(a), capture_output=True, text=True, **kw)


class HouseDefaults(unittest.TestCase):
    def test_install_writes_default_once_and_keeps_existing(self):
        with tempfile.TemporaryDirectory() as d:
            r = sh("bash", str(ROOT / "install.sh"), "--with-delivery", "--with-operating-layer", d)
            self.assertEqual(r.returncode, 0, r.stderr)
            f = Path(d) / ".claude/house-defaults.md"
            txt = f.read_text()
            for key in ("token cap", "caveman", "Hand-back", "MINIMAL-CODE: "):
                self.assertIn(key, txt)
            f.write_text("mine\n")
            self.assertEqual(sh("bash", str(ROOT / "install.sh"), "--with-delivery", "--with-operating-layer", d).returncode, 0)
            self.assertEqual(f.read_text(), "mine\n")

    def test_selfcheck_red_when_file_absent_or_empty(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".claude").mkdir()
            s = Path(d) / ".claude/settings.local.json"
            s.write_text(json.dumps(HOOK))
            st = lambda: sc.check_settings(str(s))["subagent-start-injector"]  # noqa: E731
            self.assertTrue(st().startswith("MISSING RED"), st())
            (Path(d) / ".claude/house-defaults.md").write_text("")
            self.assertTrue(st().startswith("MISSING RED"), st())
            (Path(d) / ".claude/house-defaults.md").write_text("rule\n")
            self.assertEqual(st(), "PRESENT")
            s.write_text(json.dumps({"hooks": {"SubagentStart": [{"hooks": [{"command": "python3 x/subagent_start_inject.py"}]}]}}))
            self.assertTrue(st().startswith("MISSING RED"), "hook with no HOUSE_DEFAULTS_FILE fails open")


class HeavySlots(unittest.TestCase):
    def test_warn_multi_slot_and_env_source(self):
        self.assertEqual(sc.heavy_slot_lines(1, 1, {}), ["heavy-slots: 1 (lanes 1; source: repo policy)"])
        out = sc.heavy_slot_lines(3, 2, {"PERUN_POLICY": "/x/p.json"})
        self.assertIn("source: env PERUN_POLICY=/x/p.json", out[0])
        self.assertEqual(sum("WARN" in l for l in out), 2)

    def test_idle_cpu_beats_io_inflated_load(self):
        self.assertEqual(perun_policy.heavy_slots(8, 30.0), 2)  # load1 fallback
        self.assertEqual(perun_policy.heavy_slots(8, 30.0, idle_pct=75.0), 6)
        self.assertEqual(perun_policy.lanes("maximize", 8, 30.0, idle_pct=50.0), 4)
        kw = dict(swap_samples=(1, 1), free_ram_pct=50, lane_type="heavy", load1=30.0, cores=8)
        self.assertEqual(host_probe.decide(**kw), "HOLD load-high")  # no idle reading: fallback
        self.assertEqual(host_probe.decide(cpu_idle_pct=70.0, **kw), "SPAWN")
        self.assertEqual(host_probe.decide(cpu_idle_pct=5.0, **kw), "HOLD load-high")


class SkipCiSigpipe(unittest.TestCase):
    def test_marker_found_in_multi_commit_huge_range(self):
        fn = sh("sed", "-n", "/^skip_ci_marker_in_range() {/,/^}/p",
                str(ROOT / ".claude/skills/deep-code-review/templates/integrator-gate.sh")).stdout
        with tempfile.TemporaryDirectory() as d:
            g = lambda *a: sh("git", "-C", d, "-c", "user.name=T", "-c", "user.email=t@example.com", *a)  # noqa: E731
            g("init", "-q")
            g("commit", "-q", "--allow-empty", "-m", "base")
            for i, body in enumerate(("plain", "[skip ci] first\n\n" + "x" * 400000, "tail")):
                g("commit", "-q", "--allow-empty", "-m", f"c{i}\n\n{body}")
            run = lambda base: subprocess.run(["bash", "-c", f"set -euo pipefail; cd {d}; {fn}\nskip_ci_marker_in_range {base}"]).returncode  # noqa: E731
            self.assertEqual(run("HEAD~3"), 0)
            self.assertEqual(run("HEAD~1"), 1)


if __name__ == "__main__":
    unittest.main()
