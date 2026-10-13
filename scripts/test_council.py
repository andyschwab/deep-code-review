#!/usr/bin/env python3
"""Tests for idea-critic council.py using a fake cmd (canned answers). Stdlib only."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SK = ROOT / ".claude/skills/idea-critic/scripts"
FAKE = '''import sys, json
cfg = json.load(open(sys.argv[1])); p = sys.stdin.read()
open(cfg["log"], "a").write(json.dumps(p) + "\\n")
if cfg.get("fail"): sys.exit(2)
if "STAGE: CRITIQUE" in p: print(cfg["critique"]); sys.exit()
for lens, out in cfg["answers"].items():
    if "LENS: " + lens in p: print(out); sys.exit()
'''


def ans(v, ev="README.md:1"):
    return json.dumps({"verdict": v, "claims": [{"text": "c", "evidence": ev}], "would_change_it": "w"})


class T(unittest.TestCase):
    def run_council(self, answers, critique="{}", fail=False, **kw):
        d = Path(tempfile.mkdtemp())
        (d / "README.md").write_text("one\ntwo\n")
        (d / "fake.py").write_text(FAKE)
        log = d / "log"
        (d / "cfg.json").write_text(json.dumps({"answers": dict(zip(("skeptic", "better-way", "kill-criteria"), answers)),
                                              "critique": critique, "log": str(log), "fail": fail}))
        args = ["--cmd", f"{sys.executable} {d/'fake.py'} {d/'cfg.json'}", "--claim", "do X",
                "--steelman", "X helps", "--root", str(d)]
        for k, v in kw.items():
            args += [f"--{k.replace('_', '-')}", str(v)]
        r = subprocess.run([sys.executable, str(SK / "council.py")] + args, capture_output=True, text=True)
        calls = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
        return r.returncode, json.loads(r.stdout), calls, d

    def valid(self, rec, d):
        f = d / "rec.json"
        f.write_text(json.dumps(rec))
        return subprocess.run([sys.executable, str(SK / "validate_verdict.py"), "--file", str(f)]).returncode

    def test_agreement_no_critique(self):
        rc, rec, calls, d = self.run_council([ans("REVISE")] * 3)
        self.assertEqual((rc, rec["verdict"], len(calls), rec["critique_ran"]), (0, "REVISE", 3, False))
        self.assertEqual(rec["confidence"], 1.0)
        self.assertEqual(self.valid(rec, d), 0)

    def test_disagreement_runs_anonymized_critique(self):
        crit = json.dumps({"verdict": "HOLD", "attacks": [{"target": "A", "text": "t", "evidence": "README.md:2"}]})
        rc, rec, calls, d = self.run_council([ans("HOLD"), ans("PASS_TO_USER"), ans("HOLD")], crit)
        self.assertTrue(rec["critique_ran"])
        self.assertEqual(len(calls), 6)
        for p in calls[3:]:
            self.assertEqual(p.count("\nANSWER "), 2)
            for lens in ("LENS:", "skeptic", "better-way", "kill-criteria"):
                self.assertNotIn(lens, p)
        self.assertEqual(rec["verdict"], "HOLD")
        self.assertEqual(self.valid(rec, d), 0)

    def test_unevidenced_critique_cannot_flip_and_is_voided(self):
        crit = json.dumps({"verdict": "HOLD", "attacks": [{"target": "A", "text": "t", "evidence": "nope.py:9"}]})
        _, rec, _, _ = self.run_council([ans("REVISE"), ans("REVISE"), ans("PASS_TO_USER")], crit)
        self.assertEqual(rec["verdict"], "REVISE")
        self.assertEqual(len(rec["voided_objections"]), 3)
        self.assertEqual(len(rec["dissent"]), 1)

    def test_unverifiable_citation_dropped(self):
        _, rec, _, _ = self.run_council([ans("REVISE", "README.md:99")] * 3)
        self.assertEqual(len(rec["unsupported_claims"]), 3)
        self.assertEqual(rec["confidence"], 0.0)

    def test_cap_stops_before_call(self):
        rc, rec, calls, d = self.run_council([ans("REVISE")] * 3, max_calls=2)
        self.assertEqual((rc, rec["verdict"], len(calls)), (3, "COULD_NOT_DECIDE", 2))
        self.assertEqual(self.valid(rec, d), 0)
        rc, rec, calls, _ = self.run_council([ans("REVISE")] * 3, max_chars=10)
        self.assertEqual((rc, len(calls)), (3, 0))

    def test_cmd_failure_fails_closed(self):
        rc, rec, _, _ = self.run_council([ans("REVISE")] * 3, fail=True)
        self.assertEqual((rc, rec["verdict"]), (3, "COULD_NOT_DECIDE"))

    def test_owner_request_never_hold(self):
        _, rec, _, _ = self.run_council([ans("HOLD")] * 3, origin="owner-request")
        self.assertEqual(rec["verdict"], "REVISE")


if __name__ == "__main__":
    unittest.main()
