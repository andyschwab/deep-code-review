# Preregistration: communication-structure outcome bench, round 2 (2026-10-19)

Written and hashed (SHA256-frozen.txt, ledger event `preregistered`) before any new held-out call. Free PCSS models only; no `claude -p`; all data synthetic and fictional. Builds on `../comms-outcome-1019` (r1); r1's scripts are reused unchanged and listed in SHA256-frozen.txt.

## Question
r1 found a tuned edit (E4: name the options in the ask, add a `Key figure:` line) gained +0.041 [+0.001, +0.078] held-out accuracy over the shipped skill (V0) but was reverted because a regex invented-figure rate rose from 24 to 25 of 90 messages. The regex flags any numeric token or weekday absent from the notes, so it also flags a correctly derived figure (a sum, a difference, 12,000 for $12k): it measures a proxy. r2 replaces the guard with a measure of real fabrication and re-tests E4 once on fresh scenarios.

## Real-fabrication guard
- Flagging is r1's rule (`fixed.numbers` through `bench.invented`: tokens in the message and not in the notes). A blind judge (GLM-5.2, the r1 grader; a different model from the generator; prompts/fab_judge.txt) sees the notes, the message and the flagged tokens, never the arm, and labels each token `supported` (same figure in another form, correct arithmetic on notes figures, a count of listed items, list numbering, a period the notes' dates imply, a statement about the message itself) or `fabricated` (a quantity, date, year or weekday the notes neither state nor allow to derive, a contradiction, or wrong arithmetic).
- A message is really fabricated when at least one flagged token is labelled fabricated. A scenario's real-fab rate is the share of its 3 samples that are. A flagged token the judge leaves unlabelled is counted and must be zero for the keep rule.
- Validation, done on r1 outputs before this file was frozen (not on any r2 data): 91 flagged tokens (every V0 and E4 token of r1 held-out plus 14 random from each of RIVAL and NONE; make_sample.py, sample.json) were labelled by hand before any judge call, with the notes in view (labels.json). The labeller was the lane agent (a model), not a human, so the labels are one rater's. The sample was split at random into dev (51 tokens, 3 fabricated) and test (40 tokens, 8 fabricated). The prompt was edited once on dev, for a JSON-format fault (a list in place of a string voided 2 of 51 answers), then judged once on the test split against the bar in validation_bar.txt (written before that run). Results are in validation.jsonl: dev agreement 50/51 (0.980); test agreement 39/40 (0.975), recall of hand-labelled fabricated tokens 7/8, precision 8/8 of tokens the judge called fabricated; both clear the bar (agreement >= 0.90, recall >= 0.75).

## Arms (each arm's whole text is the generator's system prompt, as in r1)
- V0: the shipped skill v1.2.4 (prompts/V0.txt, byte-identical to r1's).
- E4: the frozen edit from r1 (prompts/E4.txt, byte-identical to r1's); no further tuning.
- RIVAL: humanizer v3.1.0, the text r1 reuses from `../comms-r5-1017/prompts/RIVAL.txt`. Descriptive only; no keep rule involves it.

## Scenarios
Written after this file is frozen, by gen.py: r1's writer brief and validity checks (every listed literal occurs in the notes, at least four figures, gold figures occur in the notes, gold action is not the drafting task); (kind, domain) pairs disjoint from r1 tune and held; every pair tried up to 4 times; the first 80 valid kept (at least 60 required, otherwise the bench stops and reports no verdict). scenarios_held.json is hashed into SHA256-frozen.txt with a ledger event before any arm generation. `bench_check.py --changed origin/main` must pass (disjointness and shingle overlap against r1 and every other bench).

## Measurement
As r1: generator Qwen3.5-397B-A17B (temperature 0.7, 3 samples per arm and scenario), readers GLM-5.1 and gpt-oss_120b, grader GLM-5.2, five questions, accuracy per scenario averaged over samples x readers x questions; paired percentile bootstrap, 10,000 resamples, seed 1. Words and the dropped-fact rate are reported as in r1.

## Keep rule for E4 (all must hold on the r2 held-out set; otherwise REVERT and no SKILL.md edit ships)
1. Accuracy, E4 minus V0, paired 95% CI lower bound above 0.
2. Real-fab rate, E4 minus V0 (per-scenario paired): the 95% CI upper bound is at most +0.02. The margin is 0.02, about one message in fifty. It is strict by design: with about 80 scenarios the interval will usually be wider than 0.02, so an E4 with a truly equal rate often fails; a pass needs E4 to be measurably no worse. This is the owner-specified non-inferiority test, kept despite its cost in power.
3. Mean words, E4 at most 1.25 x V0 (r1's budget).
4. Judge completeness: no flagged figure left unlabelled in V0 or E4, and no missing grade.

The dropped-fact rate, per-reader differences and the regex invented rate are reported, not gating. Kill criterion: any of 1 to 4 failing is REVERT; there is no re-run on the same scenarios and no second tuning pass.

## Procedure
1. Freeze (SHA256-frozen.txt and the ledger `preregistered` line). 2. gen.py writes scenarios; hash them into SHA256-frozen.txt with a ledger event. 3. `run_held.py` drives r1's `bench.run` for V0, E4, RIVAL with `bench.D` pointed at this directory; a record is never overwritten; re-running only fills records lost to transport errors, before the first report. 4. `report.py held V0 E4 RIVAL`. 5. Descriptive extra, after the verdict inputs are fixed: `report.py r1 V0 E4 RIVAL NONE` re-scores r1's already-seen held-out outputs with the real-fab judge; it carries no verdict.

## Known limits
One generator and two reader families; scenarios model-written; the judge is one model (GLM-5.2) validated on 91 tokens labelled by one model-rater, 11 of them fabricated, so recall on fabricated tokens rests on 8 test cases; the judge's labels follow the definition above, and a gray case (for example 9% for an actual 9.2% gain) can flip; the skill is written for Claude and run on another model; RIVAL's text is shared from r1's neighbour and not snapshotted here. A result is evidence for this reader, judge and scenario set, not a general claim.
