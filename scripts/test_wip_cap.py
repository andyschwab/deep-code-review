#!/usr/bin/env python3
"""Tests for the wip_cap warning in landing_watchdog.py: open PRs over the cap add a second warn line (opt-in, off by default), at or under the
cap stay silent, the line is independent of the stall line, the policy key validates, and the cap change rechecks.

Reuses the throwaway origin and fake `gh` fixtures of test_landing_watchdog.py; no network, no real policy or cache.
"""
import json
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_landing_watchdog as base  # noqa: E402

lw, pp = base.lw, base.pp
WIP = "WIP: 3 open PRs > cap 2. Drain (review, land) before spawning."


class WipCap(base.Base):
    def prompt_cap(self, cap, prs):
        self.commit(minutes_ago=10)  # a recent landing: only the WIP line can fire
        self.push()
        self.set_prs(prs)
        with mock.patch.object(lw, "wip_cap", return_value=cap):
            return self.prompt()

    def test_over_cap_warns(self):
        self.assertEqual(self.prompt_cap(2, [base.GREEN] * 3), WIP)

    def test_at_or_under_cap_is_silent(self):
        self.assertIsNone(self.prompt_cap(3, [base.GREEN] * 3))

    def test_drafts_do_not_count(self):
        draft = base.NOT_GREEN[0]
        self.assertIsNone(self.prompt_cap(2, [base.GREEN, base.GREEN, draft, draft]))
        shutil.rmtree(self.cache)
        self.assertEqual(self.prompt_cap(2, [base.GREEN, base.GREEN, base.NOT_GREEN[1], draft]), WIP)

    def test_off_by_default(self):
        self.commit(minutes_ago=10)
        self.push()
        self.set_prs([base.GREEN] * 30)
        self.assertEqual(lw.wip_cap(), 0)
        self.assertIsNone(self.prompt())

    def test_cap_is_read_from_a_real_policy_file(self):
        self.commit(minutes_ago=10)
        self.push()
        self.set_prs([base.GREEN] * 3)
        pol = self.tmp / "policy.json"
        pol.write_text(json.dumps({"wip_cap": 2}))
        os.environ["PERUN_POLICY"] = str(pol)
        self.assertEqual(lw.wip_cap(), 2)
        self.assertEqual(self.prompt(), WIP)

    def test_stall_and_wip_lines_both_emit(self):
        self.set_prs([base.GREEN] * 3)
        with mock.patch.object(lw, "wip_cap", return_value=2):
            lines = self.prompt().split("\n")
        self.assertEqual((len(lines), lines[0][:15], lines[1]), (2, "Landing stalled", WIP))

    def test_cap_change_rechecks(self):
        self.assertIsNone(self.prompt_cap(3, [base.GREEN] * 3))
        with mock.patch.object(lw, "wip_cap", return_value=2):
            self.assertEqual(self.prompt(), WIP)

    def test_default_cap_and_validation(self):
        self.assertEqual(pp.validate({})["wip_cap"], 0)
        self.assertEqual(pp.validate({"wip_cap": 4})["wip_cap"], 4)
        self.assertIsNone(pp.validate({"wip_cap": None})["wip_cap"])
        for bad in (True, "4", -1, 1.5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                pp.validate({"wip_cap": bad})


if __name__ == "__main__":
    unittest.main()
