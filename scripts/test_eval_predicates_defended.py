#!/usr/bin/env python3
"""no_fabricated_finding: a CWE named as the class a safe pattern defends against is not a finding."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_predicates as ep  # noqa: E402


class Defended(unittest.TestCase):
    def test_defended_against_passes(self):
        t = "There are none.\nThe parameterized query is the standard defense against SQL injection (CWE-89). There is no vulnerability to report."
        self.assertTrue(ep.no_fabricated_finding(t)[0])

    def test_asserted_cwe_still_fails(self):
        self.assertFalse(ep.no_fabricated_finding("Found SQL injection (CWE-89); use parameterized queries to prevent it. No other issues.")[0])
        self.assertFalse(ep.no_fabricated_finding("CWE-89 at line 4. A parameterized query would protect against it. No other issues.")[0])


if __name__ == "__main__":
    unittest.main()
