---
description: Print the weekly value receipt (PRs landed, findings, tokens per PR, spend, holds)
argument-hint: "[--session JSONL] [--baseline N] [--spend EXPORT] [--findings FILE] [--holds FILE]"
disable-model-invocation: true
---
Run `python3 scripts/weekly_receipt.py $ARGUMENTS` from the repo root and show its output verbatim.
Each line names its source; "unknown" means no data was supplied. Do not fill gaps with estimates.
This is an opt-in primitive: nothing runs it automatically.
