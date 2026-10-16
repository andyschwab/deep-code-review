#!/usr/bin/env python3
"""mutation_changed.py: the selftest (mocked tool output, no real mutation tool needed) passes."""
import subprocess
import sys
from pathlib import Path

S = Path(__file__).resolve().parent.parent / ".claude/skills/agentic-delivery/scripts/mutation_changed.py"
r = subprocess.run([sys.executable, str(S), "--selftest"], capture_output=True, text=True)
assert r.returncode == 0 and "selftest ok" in r.stdout, r.stdout + r.stderr
print("test_mutation_changed: ok")
