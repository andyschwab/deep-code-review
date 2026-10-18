# Preregistration: product-output-safety round 1, one targeted edit (2026-10-18)

Hashed (SHA256-prereg.txt) before any seed, scenario or answer is generated. Base commit: origin/main at 6a301106.

## Question

The unedited `product-output-safety` scored 0.467 [0.350, 0.583] against the promptfoo redteam-setup rival on a fresh n=60 held-out set
(`docs/bench/baseline-gs-1018`). Reading the 27 scenarios it lost: the skill answers in its own vocabulary (MAP / MANAGE labels, model
card, "critical finding / do not ship") and relitigates the constraint the team stated (fixed budget, fixed deadline), while the rival
hands over the concrete, constraint-fitting controls the requester asked for. The scenarios the skill won are mostly those where the rival
answered thinly. Hypothesis: one instruction to lead with controls the team can ship inside the stated budget, deadline and stage, with the
safety floors untouched, closes part of that gap.

## The edit

One new bullet in the MANAGE section of `.claude/skills/product-output-safety/SKILL.md` ("Answer inside the stated constraint"), paid for
by two de-duplications (the opening paragraph, and the Standards paragraph that restated the Kent and Admiralty text already in the MANAGE
confidence bullet, plus a duplicated human-in-the-loop fragment). The file ends 3 bytes under its budget, so no size growth. The
description (296 characters) is unchanged. `prompts/v0.md` is the file at the base commit; `prompts/edit.md` is the edited file. If tuning
changes the edit, `prompts/edit.md` and `SKILL.md` change together before the freeze; the number of variants tried is logged in
`ledger-tune.jsonl`.

## Design

- Harness: `scripts/rival_eval.py` unchanged (judge protocol v2: reason-first JSON, neutral random labels, both orders, a scenario scores
  1 or 0 only when both orders agree, else 0.5; judge chain GLM-5.1, GLM-5.2, gpt-oss_120b, the first whose slot-1 rate is inside 0.4 to
  0.6). `bench.py` only supplies fixtures, the freeze hashes, the ledgers and the three-arm loop. Generator Qwen3.5-397B-A17B (non-thinking,
  temperature 0.3), never a judge. PCSS only, spend $0, no `claude -p`.
- Arms: V0 (unedited skill as system prompt), EDIT, RIVAL (`prompts/rival.txt`, the committed rival text). Each answers every scenario
  once; no tools. The rival answers are generated once and shared by both comparisons. EDIT and V0 are each judged against RIVAL;
  the paired difference is per scenario (EDIT score minus V0 score). One judge model scores both comparisons: the first of the chain whose
  slot-1 rate over both comparisons together is inside the band.
- Scenarios: 20 tune (`sr1t01`..) and 60 held-out (`sr1h01`..), all fresh, written from the skill's own writer brief in batches of 10
  (`prompts/writer_brief.txt`). Rejected and regenerated if more than 10% of 6-word shingles appear in the rest of `docs/bench` or in
  another new scenario (per position: a batch is redrawn, up to 25 times, until each of its 10 positions holds a passing draft, so the
  brief's per-position pressure rule is kept), so the sets are disjoint from every earlier set and from each other by id and text. Seeds are rejected if close to
  any earlier bench seed. The held-out set is written before any tuning; tuning reads tune outputs only.
- Tuning: tune runs log to `ledger-tune.jsonl`. At most three edit variants; the final one is the best tune paired mean. The held-out run
  happens once, after `SHA256-frozen.txt` (which includes the final `SKILL.md` text) and the first line of `ledger.jsonl`
  ("preregistered", sha256 of `SHA256-frozen.txt`). Scenario writing and tune generation happen before that line and are outside
  `ledger.jsonl`; no held-out answer or judge call does.

## Analysis and decision rule

- Win rate = mean per-scenario score against the rival. CI = percentile bootstrap over scenarios, 10,000 resamples, seed 1. Paired
  difference = mean of (EDIT minus V0) per scenario with the same bootstrap.
- Ship the edit only if the paired (EDIT minus V0) 95% CI lower bound is above 0. Claim superiority over the rival only if EDIT's win-rate
  CI lower bound is above 0.5. Otherwise the edit does not ship, `SKILL.md` stays unchanged on main, and the bench is published as is.
- A failed generation or unusable verdict removes that scenario from n and is reported. Nothing is regenerated, re-judged or dropped
  afterwards.

## Known limits

One generator family wrote scenarios and all answers; judges are other models; scenarios are fictional; the rival is a tool-driven
red-team skill run without its tools. A win here means "better than the unedited skill on this synthetic distribution under this judge",
not a claim about real users.
