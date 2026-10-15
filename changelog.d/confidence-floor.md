### Changed
- The compact review card (the method for small diffs) now scores each finding 0-100 for "this change causes a real, reachable failure" and reports only scores of 80 or more; pre-existing issues, hypothetical callers and style score 25. It reads the code a finding depends on instead of emitting "unverified:" findings, and it no longer pushes the reviewer to find at least one bug. On the 2026-10-14 bench the card's precision was 0.567 against 0.862 for the full skill and 0.933 for a rival that uses the same 80-point floor.
- `merge_findings.py` drops gap rows whose numeric `confidence` is below 80 and counts them as `dropped.low_confidence`; rows without a score pass unchanged.

size-budget-raise: .claude/skills/deep-code-review/references/compact-mode.md 2067→2140 confidence floor and schema field
