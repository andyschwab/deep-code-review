import sys
from pathlib import Path
d = Path(sys.argv[1])
s = (d / "SKILL.md").read_text()
i = s.index("# Deep Code Review")
fm, body = s[:i], s[i:]
(d / "references/full-map.md").write_text("Read this when the review is not a small DIFF: scope `FULL` or `FILE`, a diff over 300 changed lines, any blast-radius flag below, or you are unsure. It is the skill's full body.\n\n" + body)
stub = """# Deep Code Review

A language- and stack-agnostic **review bar**. Evidence-grounded: every finding names `file:line`, the mechanism and a failing input.

**Lean path (check first).** Scope `DIFF <base>` (or a pasted patch) of at most 300 changed lines and no blast-radius flag (removed guard or middleware matcher, widened route matcher or CORS origin, new route with no gate, permission check moved client-side, data path dropped from `.gitignore`, loosened `Cache-Control` on an identity-bearing response, a producer wired across a trust boundary): read `references/compact-mode.md` and follow it as the whole method; read nothing else, and batch all reads in one turn.

**Everything else** (`FULL`, `FILE`, over 300 lines, any flag above, or unsure): read `references/full-map.md` and follow it. It holds the scope modes, principles, method map, domain map, severity rubric, report template and definition of done.
"""
(d / "SKILL.md").write_text(fm + stub)
