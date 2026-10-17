# Rival-eval baseline, held-out, 2026-10-17

BLUF: first run of `scripts/rival_eval.py` on the frozen held-out sets, n = 10 scenarios per skill, spend $0.00. No skill passes
(PASS needs a 95% CI lower bound above 0.5). Eight skills have a verdict; three (agentic-ceo, agentic-delivery, idea-critic) have none
because neither judge passed the position-bias health gate on them. Treat every row as a baseline to improve, not a claim of superiority.

## Result

| Skill | Rival | Judge used | n | Win rate [95% CI] | Verdict |
|---|---|---|---|---|---|
| agentic-ceo | obra/superpowers using-superpowers (MIT) | none | 0 | no verdict: no judge with a healthy slot-1 rate | n/a |
| agentic-delivery | obra/superpowers subagent-driven-development (MIT) | none | 0 | no verdict: no judge with a healthy slot-1 rate | n/a |
| business-ops | marketingskills pricing (MIT) | DeepSeek-V4-Flash | 10 | 0.400 [0.150, 0.700] | FAIL |
| communication-structure | blader/humanizer | DeepSeek-V4-Flash | 10 | 0.300 [0.100, 0.500] | FAIL |
| contribution | daymade github-contributor (MIT) | GLM-5.2 | 10 | 0.200 [0.000, 0.450] | FAIL |
| deep-code-review | Anthropic pr-review-toolkit code-reviewer | GLM-5.2 | 10 | 0.550 [0.250, 0.850] | FAIL |
| growth-analytics | marketingskills analytics and ab-testing | GLM-5.2 | 10 | 0.350 [0.100, 0.650] | FAIL |
| idea-critic | gstack plan-ceo-review | none | 0 | no verdict: no judge with a healthy slot-1 rate | n/a |
| positioning | deanpeters Product-Manager-Skills positioning-statement (CC BY-NC-SA 4.0, fetched at run time, not vendored) | DeepSeek-V4-Flash | 10 | 0.500 [0.250, 0.750] | FAIL |
| product-discovery | phuryn pm-skills | DeepSeek-V4-Flash | 10 | 0.350 [0.200, 0.500] | FAIL |
| product-output-safety | promptfoo redteam-setup | GLM-5.2 | 10 | 0.400 [0.150, 0.700] | FAIL |

Judge choice matters for one row: product-output-safety is scored by GLM-5.2 (0.400 [0.150, 0.700]) because DeepSeek-V4-Flash's slot-1 rate there (0.632) is outside the
0.4-0.6 band. Replayed from the committed verdicts, the dropped DeepSeek-V4-Flash judge would score it 0.800 [0.650, 0.950]. The gate removes the biased judge's number; it does not
show that the two agree, and for this skill they do not. Treat that row as judge-dependent.

Total spend $0.00. Win rate = mean over scenarios of 1 (Perun answer preferred in both orders), 0 (rival preferred in both
orders) or 0.5 (the two orders disagree, or a tie). CI = percentile bootstrap over scenarios, 10,000 resamples, seed 1. With n = 10 the CI is
wide (about plus or minus 0.3): a row near 0.5 means "not separable at this n", not "equal".

## Method

- Generator for both arms: Qwen3.5-397B-A17B on the PCSS endpoint, thinking disabled, temperature 0.3, no tools. Perun arm = the skill's `SKILL.md`
  as the system prompt; rival arm = the rival's public text. Same scenario text for both.
- Judge: rubric-free blind A/B, every pair judged in both orders (A/B and B/A). Primary DeepSeek-V4-Flash; GLM-5.2 (thinking disabled) is used for a skill only
  when the primary's slot-1 rate for that skill is outside 0.4-0.6. The generator is never a judge.
- Slot-1 rate = share of non-tie verdicts that chose "Response 1". A position-unbiased judge sits near 0.5 because each pair is shown in both orders.
- Scenarios: `scripts/eval-fixtures/rival/<skill>/heldout.json` (hash pinned in `rival.json`, disjoint from the tune set). Raw outputs and every judge
  verdict are in this directory under `<skill>/heldout-<key>/`.
- Reproduce: `python3 scripts/rival_eval.py run --split heldout --jobs 8 --out <dir>` with `PCSS_KEY` in the environment or a repo-root `.env`.

## Judge health (position bias)

Slot-1 rate per skill (20 verdicts each, so a skill-level rate moves in steps of about 0.05):

| Skill | DeepSeek-V4-Flash | GLM-5.2 |
|---|---|---|
| agentic-ceo | 0.7 | 0.65 |
| agentic-delivery | 1.0 | 0.65 |
| business-ops | 0.6 | not run |
| communication-structure | 0.6 | not run |
| contribution | 0.7 | 0.6 |
| deep-code-review | 0.65 | 0.55 |
| growth-analytics | 0.389 | 0.55 |
| idea-critic | 0.625 | 0.737 |
| positioning | 0.556 | not run |
| product-discovery | 0.5 | not run |
| product-output-safety | 0.632 | 0.5 |

Pooled over this baseline:

| Judge | slot 1 | slot 2 | tie | slot-1 rate |
|---|---|---|---|---|
| DeepSeek-V4-Flash | 131 | 74 | 15 | 0.639 |
| GLM-5.2 | 84 | 55 | 1 | 0.604 |

Both judges lean toward slot 1 overall (outside the 0.4-0.6 band when pooled). The gate is applied per skill, so a judge can be used on some skills and
dropped on others; where both fail, the skill gets no verdict rather than a biased number. Because a win needs both orders to agree, slot bias
cannot inflate a win rate; it can only push scenarios toward 0.5 and widen the interval.

## Caveats

- No tools in either arm; the rival texts that assume tools or sub-agents lose that part of their method here.
- Held-out scenarios for positioning, contribution, business-ops, agentic-ceo and agentic-delivery were drawn from a writer brief that never shows skill text;
  the five older text skills reuse the committed `docs/bench` scenarios (held-out ids prefixed `h`); deep-code-review reuses public OSS patches.
- Five rivals (positioning, contribution, business-ops, agentic-ceo, agentic-delivery) are fetched from their public URL at run time and cached outside the repo,
  not vendored; positioning's rival is CC BY-NC-SA and its text is not stored here.
- n = 10 per skill is the minimum the harness accepts; grow the held-out sets before reading small differences.
- Outputs come from one generator model and judges from two other vendors' models; a different generator could change the picture.
