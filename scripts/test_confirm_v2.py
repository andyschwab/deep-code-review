#!/usr/bin/env python3
"""Tests for docs/bench/confirm-v2-1017: fresh held-out sets are 60 each, frozen, disjoint from every older bench scenario, and
the recorded results (once present) recompute from their per-scenario scores. Offline; no model is called."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
D = REPO / "docs/bench/confirm-v2-1017"
sys.path.insert(0, str(D))
import confirm as c  # noqa: E402

R = c.R
SHINGLES = None


def corpus():
    """The corpus as it stood at this bench's freeze: a later bench (wins-rep-1018) is left out, because its 450 scenarios jointly
    cover more than 10% of an older scenario's shingles without any one of them copying it."""
    global SHINGLES
    later = REPO / "docs/bench/wins-rep-1018"
    skip = {p.read_text(errors="ignore").replace("\\n", " ") for p in later.rglob("*") if p.is_file() and p.suffix in (".json", ".txt", ".md", ".py", ".jsonl")}
    SHINGLES = SHINGLES or c.corpus_shingles([t for t in c.corpus_text() if t not in skip])
    return SHINGLES


class Sets(unittest.TestCase):
    def test_sixty_fresh_frozen_disjoint(self):
        for s in c.SKILLS:
            held = R.load_scenarios(s, "heldout")
            self.assertEqual(len(held), c.N, s)
            self.assertEqual(R.check_split(s), [], s)  # frozen hash, disjoint from tune, no duplicates
            old = {R.norm(x["prompt"]) for sp in ("heldout", "tune") for x in json.loads((c.ORIG / s / f"{sp}.json").read_text())}
            seen = set()
            for x in held:
                self.assertNotIn(R.norm(x["prompt"]), old, f"{s} {x['id']} repeats an old scenario")
                self.assertLessEqual(c.overlap(x["prompt"], corpus()), c.MAX_OVERLAP, f"{s} {x['id']} overlaps the bench corpus")
                seen |= R.shingles(x["prompt"])
            self.assertTrue(seen)

    def test_frozen_hashes_match(self):
        rec = {l.split("  ", 1)[1]: l.split("  ", 1)[0] for l in (D / "SHA256-frozen.txt").read_text().splitlines()}
        for s in c.SKILLS:
            for f in ("heldout.json", "seeds.txt"):
                rel = f"docs/bench/confirm-v2-1017/fixtures/{s}/{f}"
                self.assertEqual(rec[rel], hashlib.sha256((REPO / rel).read_bytes()).hexdigest(), rel)

    def test_arms_are_the_shipped_skill(self):
        for s in c.SKILLS:
            self.assertEqual(c.cfg(s)["perun"], f".claude/skills/{s}/SKILL.md")


class Helpers(unittest.TestCase):
    def test_as_list_shapes(self):
        one = {"id": "01", "prompt": "a b c"}
        for txt in (json.dumps([one]), json.dumps({"array": [one]}), json.dumps(one), "01\na b c\n"):
            self.assertEqual([x["prompt"] for x in c.as_list(txt)], ["a b c"], txt)

    def test_overlap_and_near(self):
        sh = R.shingles("one two three four five six seven eight")
        self.assertEqual(c.overlap("one two three four five six seven eight", sh), 1.0)
        self.assertEqual(c.overlap("alpha beta gamma delta epsilon zeta eta theta", sh), 0.0)
        self.assertTrue(c.near("Migrate the billing service quickly", ["migrate billing service"]))
        self.assertFalse(c.near("Open a bakery", ["migrate billing service"]))


class Records(unittest.TestCase):
    def test_results_recompute(self):
        for p in D.glob("run/*/heldout-*/results.json"):
            r = json.loads(p.read_text())
            v = list(r["per_scenario"].values())
            self.assertEqual(r["n"], len(v))
            self.assertEqual(r["win_rate"], round(sum(v) / len(v), 3))
            lo, hi = R.boot(v)
            self.assertEqual(r["ci95"], [round(lo, 3), round(hi, 3)])
            self.assertEqual(r["verdict"], "PASS" if lo > 0.5 and len(v) >= R.MIN_HELDOUT else "FAIL")
            self.assertEqual(len(list((p.parent / "outputs" / "RIVAL").glob("*.txt"))), len(list((p.parent / "outputs" / "PERUN").glob("*.txt"))))


if __name__ == "__main__":
    unittest.main()
