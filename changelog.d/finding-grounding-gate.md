### Added
- Noise and grounding gate for review findings: `finding_ground_check.py` marks each gap finding grounded only when its file exists, the cited line is in range, and its quoted snippet appears within +-5 lines; `merge_findings.py` drops ungrounded rows, dedupes by file and mechanism, ranks by severity and caps per review.
- `post_review.sh` now refuses any ungrounded gap finding before posting (loose no-evidence rows are no longer posted in the review body).
- Evals: a clean diff reports NONE, and ungrounded findings are refused at posting. Tests in `scripts/test_finding_gates.py`, wired into CI and `test-ci-gates.sh`.

size-budget-raise: .claude/skills/deep-code-review/references/machine-report.md 10261→10498 documents the snippet field and grounding gate for findings rows
size-budget-raise: .claude/skills/deep-code-review/references/review-config.md 5205→5996 documents the grounding gate and merge step beside post_review.sh
