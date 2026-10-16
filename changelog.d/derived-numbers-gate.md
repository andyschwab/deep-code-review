### Added
- `deep-code-review/scripts/derived_numbers.py`: a doc number can be bound to the command that derives it with an inline marker, `<!-- derived: COMMAND -->N`. The check fails when `N` differs from the command's single-integer output (a stale "N tests" or "N skills"), and `--fix` rewrites the claim. Use `\|` for a pipe inside a table cell; markers in code fences and inline code are ignored. A repo with no markers passes. The marker commands run with the caller's privileges, so review them like CI scripts.
- `scripts/dcr-gates.sh` (the runner `install.sh --with-gates` installs) runs it by default, plus its selftest; `DCR_DERIVED_NUMBERS=0` turns it off and any other value except 1 fails closed. This repo's CI runs it on its own docs: the skill count in `docs/perun-vs-rivals.md` (two places) is now bound to `ls -d .claude/skills/*/SKILL.md | wc -l`. Tests: `scripts/test_derived_numbers.py` (8 checks, wired into CI). One `deep-code-review` eval: `docs-count-bound-to-source-command`.

### Fixed
- `docs/self-improvement.md` said "the other ~60 evals"; the repo has over a thousand. The count is dropped rather than bound, since it changes with every eval added.

size-budget-raise: .claude/skills/deep-code-review/references/docs-and-dx.md 23466→24013 bind doc counts to a source command
