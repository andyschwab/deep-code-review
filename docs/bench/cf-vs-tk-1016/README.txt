Compact card (CF) against the Anthropic pr-review-toolkit code-reviewer (TK), patch-only, 2026-10-16.

Committed copy of the run that docs/perun-vs-rivals.md H7 cites. CF here is references/compact-mode.md used as a
system prompt (prompts/cf_system.md = that file without its first three lines), not the full deep-code-review skill.

- results.json: 43-case head-to-head. tune-results.json, heldout-results.json: recall-recovery attempt (split.json).
- outputs/<ARM>/<case>.json: findings, strict-match flags and judge verdicts per case. Arms: CF, TK, and the variants CF60, CFDIFF, CFHUNT.
- prompts/: frozen system prompts and their checksums. PREREGISTERED.md and PREREGISTERED-ADDENDUM-1.md: frozen before the first call.
- drive.py (run|verify|report) and tune.py (run|verify|report|hrun|hverify|hreport ARM). Paths resolve from the repo root:
  the corpus is scripts/eval-fixtures/bench/train. The original run used a checkout copy under src/, so PREREGISTERED.md
  still mentions src/ and ORIGIN_MAIN_SHA; those are not in this copy.
- ledger.jsonl: cumulative cost ledger of every run in this directory (about $10.17), so rescoring prints a larger
  "spend" than the value stored at the time (3.504 for results.json, 5.639 tune, 6.383 held-out). The stored values are kept.
- Not included: the repo-access rerun (CF-R, TK-R) and the cloned repositories; docs/perun-vs-rivals.md does not cite them.
