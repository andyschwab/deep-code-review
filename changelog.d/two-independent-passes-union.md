### Changed
- High-stakes reviews now run two independent passes plus a union, dedupe and verify, replacing the seeded gap-hunt second pass (`method-situational.md`). A 30-case held-out control (issue #1372) found the seeded pass adds no measurable recall over two independent passes (+0.02, interval -0.08 to +0.13) at 1.15x the cost and lower precision. A single pass stays the default. The eval and numbers are updated.

size-budget-raise: .claude/skills/deep-code-review/references/method-situational.md 37028→37367 measured two-pass control table and independent-pass rule replace the seeded-pass text
