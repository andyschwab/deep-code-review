#!/usr/bin/env python3
"""plan_gate.py: one plan approval covers push/pr; everything else parks, batched."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".claude/skills/agentic-delivery/scripts/plan_gate.py"
sys.path.insert(0, str(SCRIPT.parent))
import plan_gate as pg  # noqa: E402


class PlanGate(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        d = Path(self._t.name)
        self.plan, self.led = d / "plan.md", str(d / "led.json")
        self.say("push, pr")

    def tearDown(self):
        self._t.cleanup()

    def say(self, grants):
        self.plan.write_text(f"add a feature\nGrants: {grants}\n")

    def cli(self, *a):
        return subprocess.run([sys.executable, str(SCRIPT), *a], capture_output=True, text=True)

    def test_granted_scope_proceeds_rest_parks_once(self):
        pg.grant(self.led, self.plan, "approve the plan")
        self.assertEqual([pg.check(self.led, self.plan, a) for a in ("push", "pr")], [0, 0])
        for a in ("merge", "deploy", "deploy"):
            self.assertEqual(pg.check(self.led, self.plan, a), 3)
        self.assertEqual(pg._load(self.led)["parked"], ["merge", "deploy"])

    def test_editing_plan_voids_grant(self):
        pg.grant(self.led, self.plan, "approve the plan")
        self.plan.write_text("add a different feature\nGrants: push, pr\n")
        self.assertEqual(pg.check(self.led, self.plan, "push"), 3)

    def test_unquoted_or_unnamed_scope_refused(self):
        for scope, quote in ((["deploy"], "ok"), (["push", "force_push"], "ok"), (["merge"], "ok"), (None, " ")):
            with self.assertRaises(ValueError):
                pg.grant(self.led, self.plan, quote, scope)
        self.plan.write_text("no grants line\n")
        with self.assertRaises(ValueError):
            pg.grant(self.led, self.plan, "ok")

    def test_unnamed_merge_parks_even_if_ledger_lists_it(self):
        pg.grant(self.led, self.plan, "approve the plan")
        rec = json.loads(Path(self.led).read_text())
        rec["scope"].append("merge")  # forged: plan never named merge
        Path(self.led).write_text(json.dumps(rec))
        self.assertEqual(pg.check(self.led, self.plan, "merge"), 3)
        self.assertEqual(self.cli("check", "merge", "--ledger", self.led, "--plan", str(self.plan)).returncode, 3)

    def test_merge_covered_only_when_plan_names_it(self):
        self.say("push, pr, merge")
        pg.grant(self.led, self.plan, "approve merge")
        self.assertEqual(pg.check(self.led, self.plan, "merge"), 0)

    def test_merge_quote_is_fail_closed(self):
        self.say("push, pr, merge")
        for quote, expect in (("approve merge", 0), ("Approve merge.", 0), ("disapprove merge", 3),
                              ("approve merge, nope", 3), ("approve merges later", 3),
                              ("approve merge only after I review it", 3), ("approve merge — ask me first", 3),
                              ("approve, do not merge", 3), ("please merge when green", 3)):
            pg.grant(self.led, self.plan, quote)
            self.assertEqual(pg.check(self.led, self.plan, "merge"), expect, quote)
            Path(self.led).unlink()

    def test_missing_ledger_halts(self):
        self.assertEqual(self.cli("check", "push", "--ledger", self.led, "--plan", str(self.plan)).returncode, 2)
        self.assertEqual(self.cli("parked", "--ledger", self.led).returncode, 2)
        with self.assertRaises(ValueError):
            pg.check(self.led, self.plan, "push")

    def test_merge_needs_the_word_in_the_approval_quote(self):
        self.say("push, pr, merge")
        rec = pg.grant(self.led, self.plan, "approve the plan")
        self.assertEqual(rec["scope"], ["pr", "push"])
        self.assertEqual(pg.check(self.led, self.plan, "merge"), 3)
        with self.assertRaises(ValueError):
            pg.grant(self.led, self.plan, "approve the plan", ["merge"])
        rec = json.loads(Path(self.led).read_text())
        rec["scope"].append("merge")  # forged: quote never said merge
        Path(self.led).write_text(json.dumps(rec))
        self.assertEqual(pg.check(self.led, self.plan, "merge"), 3)

    def test_edited_parked_list_halts_end_of_run_ask(self):
        pg.grant(self.led, self.plan, "approve the plan")
        pg.check(self.led, self.plan, "deploy")
        pg.check(self.led, self.plan, "deploy")
        self.assertEqual(self.cli("parked", "--ledger", self.led).stdout.strip(), "deploy")
        rec = json.loads(Path(self.led).read_text())
        self.assertEqual(rec["log"], ["deploy", "deploy"])
        rec["parked"] = []  # hide a parked action
        Path(self.led).write_text(json.dumps(rec))
        self.assertEqual(self.cli("parked", "--ledger", self.led).returncode, 2)

    def test_never_grantable_parks_even_if_plan_or_ledger_lists_it(self):
        self.say("push, pr, force_push, deploy")
        rec = pg.grant(self.led, self.plan, "approve the plan")
        self.assertEqual(rec["scope"], ["pr", "push"])
        for a in ("force_push", "deploy", "history_rewrite", "settings_edit"):
            self.assertEqual(pg.check(self.led, self.plan, a), 3)

    def test_forged_or_malformed_ledger_fails_closed(self):
        pg.grant(self.led, self.plan, "approve the plan")
        good = json.loads(Path(self.led).read_text())
        bad = [{**good, "scope": ["push", "deploy"]}, {**good, "scope": "push"}, {**good, "quote": ""},
               {k: v for k, v in good.items() if k != "parked"}, {k: v for k, v in good.items() if k != "log"},
               ["push"], {**good, "scope": [["push"]]}]
        for rec in bad:
            Path(self.led).write_text(json.dumps(rec))
            self.assertEqual(self.cli("check", "push", "--ledger", self.led, "--plan", str(self.plan)).returncode, 2)
        Path(self.led).write_text("{not json")
        self.assertEqual(self.cli("check", "push", "--ledger", self.led, "--plan", str(self.plan)).returncode, 2)

    def test_regrant_keeps_parked_and_unrouted_action_parks(self):
        pg.grant(self.led, self.plan, "approve the plan")
        self.assertEqual(pg.check(self.led, self.plan, "yolo"), 3)
        pg.grant(self.led, self.plan, "approve again")
        self.assertEqual(pg._load(self.led)["parked"], ["yolo"])

    def test_two_grants_lines_halt(self):
        self.plan.write_text("add a feature\nGrants: push, pr\nGrants: push, pr, merge\n")
        with self.assertRaises(ValueError):
            pg.grant(self.led, self.plan, "approve merge")
        self.say("push, pr")
        pg.grant(self.led, self.plan, "approve the plan")
        self.plan.write_text("add a feature\nGrants: push, pr\nGrants: deploy\n")
        for cmd in (("grant", "--quote", "approve merge"), ("check", "push")):
            args = [cmd[0], *cmd[1:], "--ledger", self.led, "--plan", str(self.plan)]
            self.assertEqual(self.cli(*args).returncode, 2, cmd)

    def test_unicode_lookalikes_never_approve_merge(self):
        self.say("push, pr, merge")
        for quote in ("approve merge", "approve merge ", "approve​merge", "approve merge​",
                      "аpprove merge", "approve mergе", "approve  merge"):
            pg.grant(self.led, self.plan, quote)
            self.assertEqual(pg.check(self.led, self.plan, "merge"), 3, ascii(quote))
            Path(self.led).unlink()

    def test_forged_ledger_scope_merge_passes_and_is_labelled_advisory(self):
        self.say("push, pr, merge")
        pg.grant(self.led, self.plan, "approve the plan")
        self.assertEqual(self.cli("check", "merge", "--ledger", self.led, "--plan", str(self.plan)).returncode, 3)
        rec = json.loads(Path(self.led).read_text())
        rec.update(scope=["merge"], quote="approve merge")  # agent-written, no real user reply
        Path(self.led).write_text(json.dumps(rec))
        r = self.cli("check", "merge", "--ledger", self.led, "--plan", str(self.plan))
        self.assertEqual((r.returncode, "advisory" in r.stdout), (0, True))
        self.assertIn("advisory", pg.__doc__)

    def test_cli_exit_codes(self):
        led, plan = self.led, str(self.plan)
        self.assertEqual(self.cli("grant", "--ledger", led, "--plan", plan, "--quote", "ok").returncode, 0)
        self.assertEqual(self.cli("check", "push", "--ledger", led, "--plan", plan).returncode, 0)
        self.assertEqual(self.cli("check", "deploy", "--ledger", led, "--plan", plan).returncode, 3)
        self.assertEqual(self.cli("parked", "--ledger", led).stdout.strip(), "deploy")

    def test_simulation_counts_derived_from_plans(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(pg.simulate(t), [("clean", 4, 2, 1), ("one review round", 5, 2, 1),
                                              ("review round + deploy", 6, 2, 2)])


if __name__ == "__main__":
    unittest.main()
