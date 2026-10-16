"""Max pace spends more only where it buys speed or quality: one source of truth, a waste filter, knobs that match perun_policy.py."""
import importlib.util, json, os, re, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AD = ROOT / ".claude/skills/agentic-delivery"
PP = AD / "scripts/perun_policy.py"
PRE = (AD / "templates/lane-preamble.md").read_text()
OD = (AD / "references/operating-discipline.md").read_text()
RUN = (ROOT / "commands/perun-run.md").read_text()
EVAL_ID = "max-pace-mechanical-rename-stays-cheap"
ENV = {k: v for k, v in os.environ.items() if k != "PERUN_POLICY"}


def policy_module():
    spec = importlib.util.spec_from_file_location("perun_policy", PP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class MaxPaceNoWaste(unittest.TestCase):
    def test_preamble_carries_the_whole_rule(self):
        for phrase in ("only where it buys speed or quality", "parallel lanes up to the load gate",
                       "a stronger model or deeper verification on hard steps", "The waste filter holds in both modes",
                       "no duplicate run of the same gate on the same tree", "no idle polling", "no courtesy messages",
                       "no restating", "the cheapest model that keeps quality for mechanical work",
                       "keep reporting spend", "do not pause for approval inside any granted budget"):
            self.assertIn(phrase, PRE)

    def test_no_licence_to_waste_survives(self):
        for text in (PRE, OD, RUN):
            for old in ("outranks token and cost discipline", "the model-tier economy", "stronger models, extra passes"):
                self.assertNotIn(old, text)

    def test_other_spots_point_instead_of_restating(self):
        self.assertIn("`templates/lane-preamble.md` **Drive to the goal**", OD)
        self.assertTrue((AD / "templates/lane-preamble.md").is_file())
        for restated in ("Maximum pace:", "duplicate run of the same gate", "set tokens maximize"):
            self.assertNotIn(restated, OD)
        self.assertIn("`templates/lane-preamble.md` **Drive to the goal**", RUN)
        self.assertNotIn("`operating-discipline.md` **Drive to the goal**", RUN)

    def test_trigger_list_does_not_read_a_git_push_as_max_pace(self):
        triggers = re.search(r'\("max speed".*?\)', PRE).group(0)
        self.assertIn('"push at max"', triggers)
        self.assertNotIn('"push"', triggers)

    def test_documented_knobs_match_perun_policy(self):
        def pp(d, *a):
            r = subprocess.run([sys.executable, str(PP), *a], cwd=d, capture_output=True, text=True, env=ENV)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout.strip()

        with tempfile.TemporaryDirectory() as d:
            for dim in ("tokens", "local_cpu"):
                self.assertIn(f"set {dim} maximize", PRE)
                self.assertIn(f"set {dim} efficient", PRE)  # the documented way back to the cautious default
                pp(d, "set", dim, "maximize")
                self.assertEqual(pp(d, "get", dim), "maximize")
                pp(d, "set", dim, "efficient")
                self.assertEqual(pp(d, "get", dim), "efficient")
        m = policy_module()
        self.assertEqual((m.token_cap(8, "efficient"), m.token_cap(8, "maximize")), (2, 8))  # "the 2-lane cap"
        self.assertEqual(m.lanes("maximize", 8, 99.0, "maximize"), 1)  # "still behind the load gate"

    def test_eval_pins_a_cheap_tier_rename_at_max_pace(self):
        cases = json.loads((AD / "evals/evals.json").read_text())["evals"]
        case = next(e for e in cases if e["id"] == EVAL_ID)
        self.assertIn("max speed", case["prompt"])
        self.assertIn("rename", case["prompt"])
        self.assertRegex(case["expected_output"], r"(?i)cheapest")
        self.assertRegex(case["expected_output"], r"(?i)waste")
        self.assertGreaterEqual(len(case["expectations"]), 3)


if __name__ == "__main__":
    unittest.main()
