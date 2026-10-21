#!/usr/bin/env python3
"""Tests for agentic-ceo/scripts/context_audit.py: byte/percent accounting, per-kind advice, duplicates, exit codes. Fictional fixtures, offline."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude/skills/agentic-ceo/scripts"))
import context_audit as C  # noqa: E402


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = C.main(list(args))
    return rc, out.getvalue(), err.getvalue()


class Audit(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        self.addCleanup(self._t.cleanup)
        (self.d / "home").mkdir()
        (self.d / "cwd").mkdir()
        old = os.getcwd()  # hermetic: defaults resolve against the fixture home and cwd, never the real ones
        os.chdir(self.d / "cwd")
        self.addCleanup(os.chdir, old)
        h = mock.patch.object(Path, "home", return_value=self.d / "home")
        h.start()
        self.addCleanup(h.stop)
        e = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.d / "home/.claude")})
        e.start()
        self.addCleanup(e.stop)

    def w(self, rel, text):
        p = self.d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def test_bytes_tokens_and_percent(self):
        a, b = self.w("a/CLAUDE.md", "x" * 300), self.w("b/CLAUDE.md", "y" * 100)
        rc, out, _ = run(str(a), str(b), "--json")
        r = json.loads(out)
        self.assertEqual((rc, r["total_bytes"], r["total_tokens_approx"]), (0, 400, 100))
        self.assertEqual([(t["bytes"], t["tokens_approx"], t["pct"]) for t in r["top"]], [(300, 75, 75.0), (100, 25, 25.0)])
        self.assertEqual(r["by_kind"]["claude"], {"sources": 2, "bytes": 400, "tokens_approx": 100, "pct": 100.0})

    def test_memory_index_long_line_advice(self):
        m = self.w("mem/MEMORY.md", "- short\n- " + "z" * 250 + "\n")
        _, out, _ = run(str(self.w("CLAUDE.md", "hi")), "--memory-dir", str(m.parent))
        self.assertIn("shorten 1 index line(s) over 200 chars (first: line 2)", out)
        self.assertIn("saves ~52 bytes", out)  # "- " + 250 = 252 chars, 52 over

    def test_memory_short_lines_no_savings(self):
        m = self.w("mem/MEMORY.md", "- " + "z" * 198 + "\n")  # exactly 200 chars: not over
        _, out, _ = run(str(self.w("CLAUDE.md", "hi")), "--memory-dir", str(m.parent))
        self.assertIn("index lines already short", out)

    def test_memory_dir_finds_nested_memory_md(self):
        self.w("p1/memory/MEMORY.md", "- one\n")
        self.w("p2/memory/MEMORY.md", "- two\n")
        r = json.loads(run(str(self.w("CLAUDE.md", "hi")), "--memory-dir", str(self.d), "--json")[1])
        self.assertEqual(r["by_kind"]["memory"]["sources"], 2)

    def test_big_section_moved_to_reference(self):
        t = "# Acme\n## Small\nok\n## Release runbook\n" + "step\n" * 1000
        _, out, _ = run(str(self.w("CLAUDE.md", t)))
        self.assertIn("move section '## Release runbook' to an on-demand reference", out)
        self.assertIn("saves ~4919 bytes", out)  # section 5000 + 19 header bytes - 100 pointer
        _, out, _ = run(str(self.w("C2.md", "## A\nsmall\n")))
        self.assertIn("no section over 4000 bytes", out)

    def test_skill_description_counts_description_only(self):
        self.w("sk/acme-one/SKILL.md", "---\nname: acme-one\ndescription: " + "d" * 400 + "\n---\n" + "body " * 5000)
        self.w("sk/acme-two/SKILL.md", "---\nname: acme-two\ndescription: >\n  folded text\n  second line\n---\nbody\n")
        r = json.loads(run("--skills-dir", str(self.d / "sk"), "--json")[1])
        self.assertEqual(r["by_kind"]["skill"]["bytes"], 400 + len("folded text second line"))
        self.assertIn("cut this description from 400 to 300 chars", r["top"][0]["cut"])
        self.assertEqual(r["top"][0]["saves_bytes"], 100)

    def test_short_skill_description_advice(self):
        self.w("sk/acme-one/SKILL.md", "---\nname: acme-one\ndescription: Short.\n---\n")
        self.assertIn("uninstall the skill if unused", run("--skills-dir", str(self.d / "sk"))[1])

    def test_skill_description_parser(self):
        self.assertEqual(C.skill_description("---\nname: a\ndescription: 'Quoted one'\n---\n"), "Quoted one")
        self.assertEqual(C.skill_description("---\r\nname: a\r\ndescription: CRLF one\r\n---\r\n"), "CRLF one")
        self.assertEqual(C.skill_description("no frontmatter"), "")
        self.assertEqual(C.skill_description("---\nname: a\n---\n"), "")

    def test_duplicates_across_files_not_within_or_short(self):
        line = "- Always run the Acme gates before you commit anything."
        a = self.w("a/CLAUDE.md", line + "\n" + line + "\nshort\n")
        b = self.w("b/CLAUDE.md", "* " + line[2:].upper() + "\nshort\n")
        r = json.loads(run(str(a), str(b), "--json")[1])
        self.assertEqual(len(r["duplicates"]), 1)
        self.assertEqual(len(r["duplicates"][0]["in"]), 2)
        self.assertIn("duplicate lines across files: 1", run(str(a), str(b))[1])
        c = self.w("c/CLAUDE.md", line + "\n" + line + "\n")
        self.assertEqual(json.loads(run(str(c), "--json")[1])["duplicates"], [])

    def test_missing_explicit_path_exits_2(self):
        rc, _, err = run(str(self.d / "nope.md"))
        self.assertEqual(rc, 2)
        self.assertIn("not found", err)
        self.assertEqual(run("--memory-dir", str(self.d / "nope"))[0], 2)

    def test_top_limits_rows_and_text_is_labelled_approximate(self):
        ps = [str(self.w(f"{i}/CLAUDE.md", "x" * (10 + i))) for i in range(4)]
        _, out, _ = run(*ps, "--top", "2")
        self.assertEqual(out.count("cut:"), 2)
        self.assertIn("approximate", out)

    def test_defaults_found_in_cwd_and_home(self):
        (self.d / "cwd/.claude").mkdir()
        (self.d / "cwd/CLAUDE.md").write_text("a" * 40)
        (self.d / "cwd/.claude/CLAUDE.md").write_text("b" * 20)
        (self.d / "home/.claude").mkdir()
        (self.d / "home/.claude/CLAUDE.md").write_text("c" * 10)
        r = json.loads(run("--json")[1])
        self.assertEqual((r["by_kind"]["claude"]["sources"], r["total_bytes"]), (3, 70))

    def test_boundaries_are_not_over(self):
        self.w("sk/acme-one/SKILL.md", "---\nname: acme-one\ndescription: " + "d" * 300 + "\n---\n")
        self.assertIn("description already short", run("--skills-dir", str(self.d / "sk"))[1])
        _, out, _ = run(str(self.w("CLAUDE.md", "## Big\n" + "x" * 3993)))  # section is exactly 4000 bytes
        self.assertIn("no section over 4000 bytes", out)

    def test_skill_without_description_skipped_and_skill_dups_ignored(self):
        self.w("sk/acme-none/SKILL.md", "---\nname: acme-none\n---\nbody\n")
        d = "description: This identical description is long enough to count as a duplicate line."
        self.w("sk/acme-a/SKILL.md", f"---\nname: acme-a\n{d}\n---\n")
        self.w("sk/acme-b/SKILL.md", f"---\nname: acme-b\n{d}\n---\n")
        r = json.loads(run("--skills-dir", str(self.d / "sk"), "--json")[1])
        self.assertEqual((r["by_kind"]["skill"]["sources"], r["duplicates"]), (2, []))

    def test_default_skills_dir_in_cwd(self):
        (self.d / "cwd/.claude/skills/acme-x").mkdir(parents=True)
        (self.d / "cwd/.claude/skills/acme-x/SKILL.md").write_text("---\nname: acme-x\ndescription: Does X.\n---\n")
        self.assertEqual(json.loads(run("--json")[1])["by_kind"]["skill"]["bytes"], 7)
        (self.d / "home/.claude/skills/acme-y").mkdir(parents=True)  # user-level skills come from the config dir
        (self.d / "home/.claude/skills/acme-y/SKILL.md").write_text("---\nname: acme-y\ndescription: Does YY.\n---\n")
        self.assertEqual(json.loads(run("--json")[1])["by_kind"]["skill"]["bytes"], 7 + 8)

    def test_bytes_not_chars_and_headings_never_duplicate(self):
        self.assertEqual(json.loads(run(str(self.w("CLAUDE.md", "é" * 10)), "--json")[1])["total_bytes"], 20)
        self.assertIn("move section '## Big'", run(str(self.w("C2.md", "## Big\n" + "é" * 2100 + "\n## Z\nok")))[1])  # 4200 bytes, 2100 chars
        h = "## " + "Acme heading that is long enough to pass the length floor"
        a, b = self.w("a/CLAUDE.md", h + "\n```" + "x" * 40 + "\n"), self.w("b/CLAUDE.md", h + "\n```" + "x" * 40 + "\n")
        self.assertEqual(json.loads(run(str(a), str(b), "--json")[1])["duplicates"], [])

    def test_default_discovery_matches_token_report_candidates(self):
        (self.d / "cwd/AGENTS.md").write_text("a" * 8)
        mem = Path(next(p for l, p, _ in C.tr.instruction_candidates(".") if l.endswith("MEMORY.md")))
        mem.parent.mkdir(parents=True)
        mem.write_text("- hook\n")
        r = json.loads(run("--json")[1])
        self.assertEqual((r["by_kind"]["claude"]["bytes"], r["by_kind"]["memory"]["bytes"]), (8, 7))

    def test_no_resolvable_home_skips_user_level_files(self):
        (self.d / "cwd/CLAUDE.md").write_text("a" * 12)
        env = {k: v for k, v in os.environ.items() if k not in ("HOME", "CLAUDE_CONFIG_DIR")}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(Path, "home", side_effect=RuntimeError("no home")), \
                mock.patch("os.path.expanduser", side_effect=lambda p: p):  # what expanduser does with no HOME and no passwd entry
            rc, out, _ = run("--json")
            self.assertEqual(len(C.tr.instruction_candidates(".")), 3)
            with mock.patch("os.path.isfile", return_value=False) as isfile:
                C.tr.load_settings(".")
            self.assertFalse([c for c in isfile.call_args_list if c.args[0].startswith("~")])  # no "~/.claude/settings.json" probe
        self.assertEqual((rc, json.loads(out)["total_bytes"]), (0, 12))

    def test_same_file_via_symlink_or_repeat_counts_once(self):
        a = self.w("a/CLAUDE.md", "- Always run the Acme gates before you commit anything.\n")
        link = self.d / "la.md"
        link.symlink_to(a)
        r = json.loads(run(str(a), str(link), str(a), "--json")[1])
        self.assertEqual((r["total_bytes"], r["by_kind"]["claude"]["sources"], r["duplicates"]), (56, 1, []))

    def test_directory_inputs_exit_2_or_are_skipped(self):
        rc, _, err = run(str(self.d))
        self.assertEqual(rc, 2)
        self.assertIn("not a file", err)
        (self.d / "sk/acme-dir/SKILL.md").mkdir(parents=True)
        self.w("sk/acme-ok/SKILL.md", "---\nname: acme-ok\ndescription: Does X.\n---\n")
        r = json.loads(run("--skills-dir", str(self.d / "sk"), "--json")[1])
        self.assertEqual(r["by_kind"]["skill"]["sources"], 1)
        (self.d / "mem/MEMORY.md").mkdir(parents=True)
        self.assertEqual(run("--memory-dir", str(self.d / "mem"))[0], 0)

    def test_unreadable_file_exits_2(self):
        p = self.w("CLAUDE.md", "hi")
        with mock.patch.object(Path, "read_bytes", side_effect=PermissionError(13, "Permission denied", str(p))):
            rc, _, err = run(str(p))
        self.assertEqual(rc, 2)
        self.assertIn("cannot read", err)

    def test_crlf_skill_is_counted(self):
        self.w("sk/acme-crlf/SKILL.md", "---\r\nname: acme-crlf\r\ndescription: Does X.\r\n---\r\nbody\r\n")
        self.assertEqual(json.loads(run("--skills-dir", str(self.d / "sk"), "--json")[1])["by_kind"]["skill"]["bytes"], 7)

    def test_bytes_are_raw_on_disk_size_for_non_utf8(self):
        p = self.d / "CLAUDE.md"
        p.write_bytes(b"\xff\xfe\xfd" * 10)  # 30 raw bytes; decoding gives 30 U+FFFD, which re-encode to 90
        self.assertEqual(json.loads(run(str(p), "--json")[1])["total_bytes"], 30)

    def test_empty_sources_report_zero(self):
        r = json.loads(run("--skills-dir", str(self.d), "--json")[1])
        self.assertEqual((r["total_bytes"], r["top"], r["duplicates"]), (0, [], []))

    def test_skills_dir_naming_a_file_exits_2(self):
        rc, _, err = run("--skills-dir", str(self.w("f.txt", "x")))
        self.assertEqual(rc, 2)
        self.assertIn("not a directory", err)
        rc, _, err = run("--memory-dir", str(self.w("g.txt", "x")))
        self.assertEqual(rc, 2)
        self.assertIn("not a directory", err)

    def test_small_section_max_never_reports_negative_savings(self):
        r = json.loads(run(str(self.w("CLAUDE.md", "## Big\n" + "x" * 60)), "--section-max", "50", "--json")[1])
        self.assertEqual(r["top"][0]["saves_bytes"], 0)
        self.assertNotIn("saves ~-", run(str(self.d / "CLAUDE.md"), "--section-max", "50")[1])

    def test_skill_rows_are_labelled_description_bytes(self):
        self.w("sk/acme-one/SKILL.md", "---\nname: acme-one\ndescription: Does X.\n---\n")
        out = run("--skills-dir", str(self.d / "sk"))[1]
        self.assertEqual(out.count("description bytes"), 2)  # kind total and top row
        self.assertIn("description bytes", C.__doc__)


if __name__ == "__main__":
    unittest.main()
