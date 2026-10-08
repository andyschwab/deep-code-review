#!/usr/bin/env python3
"""weekly_receipt.py and token_ratchet.py must report the same tokens-per-PR for one fixture."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / ".claude/skills/agentic-ceo/scripts"
FIX = S / "fixtures/token"


def py(script, *args):
    return subprocess.run([sys.executable, str(S / script), *args], capture_output=True, text=True, check=True).stdout


class Parity(unittest.TestCase):
    def test_same_tokens_per_pr(self):
        with tempfile.TemporaryDirectory() as t:
            repo = Path(t)
            g = ["git", "-C", t, "-c", "user.name=Jane Smith", "-c", "user.email=jane@example.com"]
            subprocess.run([*g, "init", "-q"], check=True)
            for n in (1, 2, 3):
                subprocess.run([*g, "commit", "-q", "--allow-empty", "-m", f"Merge pull request #{n} from acme/x"], check=True)
            base = repo / "b.json"
            subprocess.run([sys.executable, str(S / "token_ratchet.py"), "--dir", str(FIX), "--baseline", str(base),
                            "--since", "2000-01-01T00:00:00Z", "--write-baseline"], cwd=t, check=True, capture_output=True)
            want = json.loads(base.read_text())["tokens_per_pr"]
            out = py("weekly_receipt.py", "--repo", t, "--session", str(FIX / "session.jsonl"), "--days", "36500")
            got = int(re.search(r"Tokens per PR:\s+([\d,]+)", out).group(1).replace(",", ""))
            self.assertEqual(json.loads(base.read_text())["prs"], 3)
            self.assertGreater(want, 0)
            self.assertEqual(got, int(want))


if __name__ == "__main__":
    unittest.main()
