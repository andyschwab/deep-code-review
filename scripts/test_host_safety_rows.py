#!/usr/bin/env python3
"""Every skill host root install.sh can write has a host-safety row, a gates lookup entry and a gitignored backup dir."""
import re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import perun_doctor  # noqa: E402

TSV = ROOT / ".claude/skills/agentic-delivery/templates/host-safety.tsv"
GATES = ROOT / ".claude/skills/deep-code-review/templates/dcr-gates.sh"
HOSTS = perun_doctor.SKILL_HOSTS


class HostRows(unittest.TestCase):
    def test_tsv_row_per_host(self):
        rows = {l.split("\t")[0] for l in TSV.read_text().splitlines() if l and not l.startswith("#")}
        self.assertEqual(set(HOSTS) - rows, set())

    def test_new_hosts_rows_have_name_and_https_link(self):
        rows = {l.split("\t")[0]: l.split("\t") for l in TSV.read_text().splitlines() if l and not l.startswith("#")}
        for h, name in ((".cline", "Cline"), (".roo", "Roo Code"), (".factory", "Factory Droid")):
            self.assertEqual(rows[h][1], name)
            self.assertTrue(rows[h][4].startswith("https://"))

    def test_gates_lookup_lists_every_host(self):
        m = re.search(r"^HOST_CANDIDATES=\((.*?)\)", GATES.read_text(), re.M)
        self.assertEqual(set(HOSTS) - set(m.group(1).split()), set())

    def test_skill_backups_ignored(self):
        ignore = (ROOT / ".gitignore").read_text().splitlines()
        # .cursor/ is ignored whole, which covers its skill-backups/.
        for h in HOSTS:
            self.assertTrue(f"{h}/skill-backups/" in ignore or f"{h}/" in ignore, h)


if __name__ == "__main__":
    unittest.main()
