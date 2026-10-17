idea-critic against its rival, round 6, 2026-10-17. Preregistration: PREREGISTERED.md (hashes in SHA256-frozen.txt, taken before any round-6 generation or judging); tune choice PREREGISTERED-CHOICE.md (SHA256-choice.txt, written before any held-out generation); held-out scenarios hashed in SHA256-scenarios6.txt before any answer; rival answers frozen in RIVAL-sha256-h6.json. Driver bench6.py (derived from ../idea-critic-r5-1017/bench5.py; reuses ../exec-1017/bench.py); judge prompt v2 byte-identical to round 5's.

Result: the one edit (c6, step 6: bounded first step, numeric tripwire at a dated checkpoint, figure error first) is reverted; SKILL.md is unchanged. The bar needed a lower bound above 0.5 and a win rate at least v0's; c6 met the second and missed the first.

1. Tune n=10 (judge v2, GLM-5.1 + GLM-5.2 + gpt-oss_120b, both orders, strict agreement): v0 0.75 [0.55, 0.95] (6/3/1, copied from round 5), c6 0.80 [0.60, 1.00] (7/2/1). c6 strictly above v0, so it went to held-out (a one-scenario gap).
2. Held-out, 40 fresh fictional scenarios (company names absent from all earlier docs/bench files), same frozen RIVAL answers, same judges:
   v0: 0.475, 95% interval [0.362, 0.588], 10 wins / 18 ties / 12 losses, order disagreement 0.392.
   c6: 0.550, 95% interval [0.425, 0.675], 15 wins / 14 ties / 11 losses, order disagreement 0.350.
   c6 is 0.075 above v0 on the same scenarios, but its lower bound 0.425 is not above 0.5, so the edit is not kept. v0 on this set (0.475) is below its round-5 held-out value (0.575) on a different scenario set, with the same judges and prompt: scenario-set variance at n=40 is about +-0.1, as the intervals show.

Caveats: open models on one cluster; system-prompt-only arms; ties count 0.5 and are 14-18 of 40; one run per arm; tune n=10 is a weak selector; gpt-oss_120b wrote the scenarios and also judges; the win-rate difference between c6 and v0 is not tested for significance (the two intervals overlap); no paid call; no key printed. The first scenario-generation attempt failed closed because the privacy gate needs .banlist.local.txt in the worktree; the file was copied (gitignored) and scenario generation rerun before any answer existed.

Disclosures (added after the run, not preregistered):
- Unedited v0 scored 0.575 [0.450, 0.700] on the round-5 held-out set and 0.475 [0.362, 0.588] on this round's fresh held-out set, with the same judge prompt and judges. That 0.10 swing between two held-out sets is as large as the edit effects measured here, so a single n=40 set cannot resolve effects of this size.
- Paired c6 minus v0 on the 40 held-out scenarios: +0.075, bootstrap 95% CI [-0.100, 0.250] (10,000 resamples, seed 1). Computed post hoc for disclosure only; it is not a keep test.
- No null or unparsed judge orders in the round-5 or round-6 records (480 orders per judge).
