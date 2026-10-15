### Changed
- The full DIFF method (`method.md` Phase 4 anti-slop) now scores each gap finding 0-100 for "this change causes a real, reachable failure" (25 for pre-existing issues, hypothetical callers or style; 80 for a trace verified on a normal path), reports only 80 or more, and logs the rest in the coverage ledger as `declined: <reason>`.
- `machine-report.md` gains an optional integer `confidence_score` (0-100). The numeric field is named apart from the existing string tier `confidence` (CONFIRMED, CORROBORATED, PLAUSIBLE, unverified), which is unchanged. `merge_findings.py` and the compact card use `confidence_score`, so the floor never reads a tier as a score.
- The DIFF quick-path now says to batch all reads in one turn.

size-budget-raise: .claude/skills/deep-code-review/SKILL.md 23735→23764 batch-reads note
size-budget-raise: .claude/skills/deep-code-review/references/machine-report.md 11250→11543 confidence_score field
size-budget-raise: .claude/skills/deep-code-review/references/method.md 42880→43171 confidence floor rule
size-budget-raise: .claude/skills/deep-code-review/references/compact-mode.md 2140→2146 confidence_score rename
