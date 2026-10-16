#!/usr/bin/env python3
"""mutation_changed.py: the selftest (mocked tool output, no real mutation tool needed) passes."""
import subprocess
import sys
from pathlib import Path

S = Path(__file__).resolve().parent.parent / ".claude/skills/agentic-delivery/scripts/mutation_changed.py"
r = subprocess.run([sys.executable, str(S), "--selftest"], capture_output=True, text=True)
assert r.returncode == 0 and "selftest ok" in r.stdout, r.stdout + r.stderr
print("test_mutation_changed: ok")
sys.path.insert(0, str(S.parent))
import mutation_changed as m  # noqa: E402
assert m.run(["/nonexistent-mutation-tool"], ".", 5) == (127, "", False), "missing binary must not crash"
assert m.changed_lines("+++ b/ä x.py\n@@ -1 +2,2 @@\n") == {"ä x.py": {2, 3}}
print("test_mutation_changed: missing-binary and unquoted-path cases ok")
