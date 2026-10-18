# growth-analytics answer-first edit, held-out n = 60, 2026-10-18

BLUF: DO NOT SHIP. The edit (v1) scored 0.308 [0.217, 0.408] against the marketingskills rival, the shipped text (v0) 0.467 [0.367, 0.567]; paired difference (v1 minus v0) -0.158, 95% bootstrap CI [-0.275, -0.033] (n = 60 of 60 scored, judge GLM-5.1, slot-1 rate 0.592, healthy). The preregistered keep rule (paired lower bound above 0) is not met, and the paired interval excludes 0 on the wrong side. Superiority over the rival is not claimed (win-rate lower bound 0.217 is not above 0.5). Spend $0.00 (PCSS only). `.claude/skills/growth-analytics/SKILL.md` is unchanged in this commit (byte-identical to origin/main at 6a301106); only this bench record is committed.

- Rule, arms, scenario drawing, tuning log: `PREREGISTERED.md`. Hash lists: `SHA256-prereg.txt` (after the tuning phase, before any held-out seed) and `SHA256-frozen.txt` (after the held-out scenarios, before any held-out answer). `ledger.jsonl` records the hash of `SHA256-frozen.txt` first, then `run_start`, then the results hash. Tuning runs are in `ledger-tune.jsonl`, never in `ledger.jsonl`.
- Tested text: `frozen/growth-analytics.v1.md`, one added paragraph ("Answer the ask first") plus one deleted sentence, 10794 bytes against 10795. v0 is `frozen/growth-analytics.v0.md`. The rival text is the committed `docs/bench/growth-analytics-rubricfree-1016/prompts/rival.txt`.
- Scenarios: `scenarios-heldout.json` (ids gh01 to gh60) from `prompts/seeds-heldout.txt`, disjoint by id and by text (6-word shingle overlap at most 0.10) from every earlier `docs/bench` set and from the tune sets; `scripts/bench_check.py` passes.
- Raw outputs and verdicts: `results/outputs`, `results/judge-verdicts.json` (every verdict kept), `results/verdict.json`. Reproduce: `python3 docs/bench/growth-r1-1018/bench.py run <out>` then `fold <out>` (PCSS key from the repo `.env`).

| Judge | Slot-1 | v0 | v1 | Paired diff [95% CI] |
|---|---|---|---|---|
| GLM-5.1 (used) | 0.592 | 0.467 | 0.308 | -0.158 [-0.275, -0.033] |
| GLM-5.2 (sensitivity) | 0.571 | 0.400 | 0.358 | -0.042 [-0.167, 0.075] |
| gpt-oss_120b (sensitivity, outside the 0.4 to 0.6 gate) | 0.642 | 0.325 | 0.308 | -0.017 [-0.133, 0.108] |

Strict result under the used judge: v1 11 wins, 15 ties or splits, 34 losses; v0 17 wins, 22 ties or splits, 21 losses. All three judges give a negative point estimate for v1 minus v0; only GLM-5.1's interval excludes 0.

## What this says

- The hypothesis behind the edit (v0 loses because it defers the call and recites skill vocabulary, so an answer-first line helps) did not hold on a fresh set. The tune result (+0.042 [-0.075, 0.158], n = 60) was inside noise and did not replicate; identical text moved the tune paired difference by 0.03 to 0.13, so selecting the best of nine short candidates on a noisy tune set was a winner's-curse risk that the held-out set exposed.
- v0 against this rival on this set is 0.467 [0.367, 0.567], consistent with the baseline's 0.442 [0.333, 0.550] on a different set. growth-analytics is still not shown to beat the rival.
- Next idea, not tried: the rival's winning answers carry a longer audience-ready rationale and a dated plan; additions that tried that on the tune set (candidates D and E) did worse, so a prompt-only fix may not exist at this skill size.

## Caveats

Qwen3.5-397B-A17B generates every arm (not necessarily the model the skill runs on); judges are PCSS models; one rival; one run per arm; scenarios are fictional and written by one blind writer model. The judge-reason pattern that motivated the edit was read from re-judged losses of the baseline run (the baseline's cached verdicts hold no reasons).
