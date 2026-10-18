# Preregistration: growth-analytics answer-first edit, held-out n=60 (2026-10-18)

This file and the frozen texts are hashed (`SHA256-prereg.txt`) after the tuning phase and before any held-out seed, scenario or answer exists. The scenario hashes follow in `SHA256-frozen.txt`; its hash is the first line of `ledger.jsonl`, before any held-out answer or judge call. Every model call goes to the PCSS endpoint ($0); no `claude -p`; all scenarios are fictional.

Scenarios file: scenarios-heldout.json

## Question

The baseline bench (`docs/bench/baseline-gs-1018`) found the shipped `growth-analytics` skill (v0) at 0.442 [0.333, 0.550] against the marketingskills analytics and ab-testing rival on a fresh n=60 set. Re-reading the judge reasons on its 25 losses (re-judged for their text; the cached verdicts hold no reasons) showed a pattern: v0's answer often withholds or defers the call the requester asked for ("pause and redesign", "no baseline, cannot say") and fills the answer with skill vocabulary and boilerplate notes, while the rival gives a usable decision in the requester's terms by their date. The edit (v1) is one added paragraph, "Answer the ask first", at the top of "The method", paid for by deleting one sentence of the Standards section that restated the observability and privacy seam already stated in method step 3. File size is 10794 bytes against 10795 for v0 (no growth). The description is unchanged.

Does v1 beat v0 against the same rival, and does v1 beat the rival?

## Tuning phase (before this file; logged in `ledger-tune.jsonl`)

Two fresh tune sets of 30 scenarios each (ids `gt01` to `gt30` and `gu01` to `gu30`, `scenarios-tune.json` and `scenarios-tune2.json`), drawn like the held-out set. Tune runs used the first judge only (GLM-5.1, both orders, v2 protocol) and are exploratory. Nine candidate texts were tried; per-run results are in `ledger-tune.jsonl` (the candidate texts are not kept except the final one). Paired difference against a v0 arm, n = 60 unless noted, with the tune noise level set by re-running v0 text as the candidate (identical text, different sample): -0.133 on n = 30 and -0.033 on n = 60.

| Candidate | Change | Paired diff vs v0 |
|---|---|---|
| A, B (n=30) | rewrite method step 6 to answer as asked | -0.067, -0.083 |
| C | answer-first paragraph, long | +0.033 |
| D, E | C plus audience close and data-cut list | -0.125, -0.117 |
| F, G | delete Standards and Stage-awareness sections (G with C) | -0.067, -0.083 |
| H | answer-first paragraph, short | +0.058 |
| I (= v1, final) | H reworded 3 bytes shorter, plus the one-sentence deletion | +0.042 [-0.075, 0.158] |

Reading: longer additions did worse, the short paragraph was the only one clearly non-negative, and every tune interval includes 0. The tune data supports at most a small effect; it is not evidence of a win. v1 was chosen as the best short candidate and frozen unchanged.

## Arms and data

- v0 = `.claude/skills/growth-analytics/SKILL.md` on origin/main at 6a301106 (`frozen/growth-analytics.v0.md`). v1 = `frozen/growth-analytics.v1.md`, byte-identical to the edited SKILL.md in this commit. Both are final: no further tuning, no edit after seeing the held-out result.
- Rival: the committed text `docs/bench/growth-analytics-rubricfree-1016/prompts/rival.txt` (the baseline bench's rival), hashed in the frozen list. Its answer to each scenario is generated once and shared by both skill arms, so (v1 minus v0) is paired on identical rival text.
- Scenarios: 60 fresh held-out scenarios (ids `gh01` to `gh60`), seeds drawn by the blind writer model (Qwen3.5-397B-A17B, temperature 0.9) and rejected if close to any seed in `docs/bench` (including both tune seed lists), scenarios written in batches of 10 from the existing writer brief `docs/bench/growth-analytics-rubricfree-1016/prompts/writer_brief.txt` (no skill text shown). Any scenario sharing more than 10% of its 6-word shingles with the `docs/bench` corpus, with the tune scenarios, or with another held-out scenario is regenerated before freezing. `scripts/bench_check.py` must pass.
- Generator for all arms: Qwen3.5-397B-A17B, thinking off, temperature 0.3, no tools, the harness GEN_TASK wrapper, never a judge.
- Judge: protocol v2 of `scripts/rival_eval.py` unchanged (random three-letter labels, analysis before verdict, both orders). The judge is the first of GLM-5.1, GLM-5.2, gpt-oss_120b whose slot-1 rate, pooled over both arms, is in 0.4 to 0.6; the same judge scores both arms. No healthy judge means no verdict, which means do not ship. A scenario scores 1 when the arm wins in both orders, 0 when it loses in both, else 0.5. Other judges are reported as sensitivity only.

## Decision rule (stated before any held-out call)

- KEEP (ship the SKILL.md edit) only if, with at least 54 of 60 scenarios scored by a healthy judge, the paired difference (v1 minus v0 win rate, mean of per-scenario score differences) has a 95% bootstrap CI (10,000 resamples over scenarios, percentile, seed 1) whose lower bound is above 0. Otherwise the SKILL.md edit is reverted and only this bench record is committed.
- Superiority over the rival is claimed only if v1's win-rate CI (same bootstrap) has a lower bound above 0.5.
- One run per arm; no re-runs, no judge swapping, no scenario edits after seeing a result. Records are never overwritten.

## Known limits

Single generator family writes the scenarios and all answers; judges are models; scenarios are fictional. Tune noise is large (identical text moved the paired difference by 0.03 to 0.13), so a true effect of a few points is unlikely to clear the keep rule at n = 60. A FAIL means "not shown better under this judge on this synthetic distribution", not a claim about real users.
