### Added
- idea-critic: standing skeptic checks for self-proposed work (user value vs replay, verify operational advice against host docs, who is worse off by a new default, simpler safe-by-design alternative, restate the real constraint), plus six eval fixtures for real decision misses and two PASS controls. Refs #1380.

- idea-critic: calibration rule (named evidence + measured kill criterion + safe rollback + no concrete flaw = PASS_TO_USER with at most one note) and four PASS controls.
- Live A/B (claude -p, sonnet, no tools, 3 replicates, 11 cases, keyword predicates because idea-critic binds no eval_predicates; 95% bootstrap CI): plain vs skill verdict accuracy 0.70 [0.55-0.85] vs 0.85 [0.73-0.97]; miss-case accuracy 0.90 vs 0.95; PASS-control accuracy 0.33 [0.08-0.58] vs 0.67 [0.42-0.92]; objection recall 0.57 [0.38-0.76] vs 0.86 [0.71-1.00]. Point estimates favor the skill on every metric; CIs overlap on accuracy, so the accuracy gain is not statistically established. Skill still returns REVISE on 4 of 12 PASS-control runs.

size-budget-raise: .claude/skills/idea-critic/SKILL.md 13997→15011 five standing skeptic checks, calibration rule and Veles title
