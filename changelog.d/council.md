### Added
- idea-critic council: `scripts/council.py` runs the three hats as independent calls on any model (`--cmd` template, repeatable for mixed models), tallies the verdict deterministically, runs an anonymized critique only on disagreement, verifies `path:line` citations, keeps dissent verbatim, computes confidence, and fails closed with `COULD_NOT_DECIDE` on caps or command failure. `validate_verdict.py` accepts the council record. Kill criterion: keep only if it beats self-consistency-3 at equal budget on the bench.

size-budget-raise: .claude/skills/idea-critic/SKILL.md 16062→16320 routes the council reference
