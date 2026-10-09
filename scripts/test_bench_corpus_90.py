#!/usr/bin/env python3
"""Offline checks for the 90-case TEST expansion of the review benchmark: size, language spread, held-out hygiene, TRAIN fixture quality."""
import collections
import hashlib
import json
import re
import unittest
from pathlib import Path

BENCH = Path(__file__).resolve().parent / "eval-fixtures/bench"
MAN = json.loads((BENCH / "manifest.json").read_text(encoding="utf-8"))
TEST = [m for m in MAN if m["split"] == "test"]
TRAIN = [m for m in MAN if m["split"] == "train" and not m["id"].startswith("heldout-")]
SECRET = re.compile(r"AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|-----BEGIN [A-Z ]*PRIVATE KEY-----")


class Expansion(unittest.TestCase):
    def test_sizes_and_language_spread(self):
        self.assertGreaterEqual(len(TEST), 90)
        self.assertGreaterEqual(len(TRAIN), 40)
        langs = collections.Counter(m["lang"] for m in TEST)
        self.assertEqual(set(langs), {"go", "js", "python", "shell"})
        self.assertTrue(all(n >= 10 for n in langs.values()), langs)
        self.assertLessEqual(max(langs.values()) / len(TEST), 0.4, langs)

    def test_ids_unique_and_test_entries_opaque(self):
        ids = [m["id"] for m in MAN]
        self.assertEqual(len(ids), len(set(ids)))
        for m in TEST:
            self.assertRegex(m["id"], r"^test-[0-9a-f]{10}$")
            self.assertFalse({"fix_sha", "intro_sha", "source", "files"} & set(m), m["id"])

    def test_train_fixtures_unique_small_and_secret_free(self):
        fixes, patches = set(), set()
        for m in TRAIN:
            d = BENCH / "train" / m["id"]
            patch = (d / "change.patch").read_text(encoding="utf-8")
            self.assertLessEqual(patch.count("\n"), 600, m["id"])
            self.assertFalse(SECRET.search(patch), m["id"])
            self.assertNotIn(m["fix_sha"], fixes, "duplicate fix: " + m["id"])
            h = hashlib.sha256(patch.encode()).hexdigest()
            self.assertNotIn(h, patches, "duplicate patch: " + m["id"])
            fixes.add(m["fix_sha"]); patches.add(h)


if __name__ == "__main__":
    unittest.main()
