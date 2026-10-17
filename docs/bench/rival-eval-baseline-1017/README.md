# Rival-eval baseline, held-out, 2026-10-17 (re-run with the neutral-label judge)

BLUF: re-ran `scripts/rival_eval.py` on the frozen held-out sets (n = 10 per skill, spend $0.00) after replacing the position-biased judge setup. No skill passes
(PASS needs a 95% CI lower bound above 0.5). Ten of eleven skills now have a verdict (agentic-ceo and agentic-delivery gained one); idea-critic still has none. Treat every row as a
baseline to improve, not a claim of superiority. Two things changed since the first run of this baseline and both move numbers: the judge protocol, and, for five skills, the
Perun `SKILL.md` text (outputs for those five were regenerated), so a before/after difference in those rows is not a judge effect alone.

## Result (current, judge protocol v2)

| Skill | Rival | Judge used (slot-1 rate of each judge tried) | n | Win rate [95% CI] | Verdict | First run (judge protocol v1) | Outputs |
|---|---|---|---|---|---|---|---|
| agentic-ceo | obra/superpowers using-superpowers (MIT) | GLM-5.1 (0.60) | 10 | 0.600 [0.350, 0.850] | FAIL | no verdict | reused |
| agentic-delivery | obra/superpowers subagent-driven-development (MIT) | GLM-5.1 (0.55) | 10 | 0.250 [0.050, 0.450] | FAIL | no verdict | regenerated |
| business-ops | marketingskills pricing (MIT) | GLM-5.1 (0.40) | 10 | 0.200 [0.000, 0.400] | FAIL | 0.400 [0.150, 0.700] | reused |
| communication-structure | blader/humanizer | GLM-5.1 (0.40) | 10 | 0.300 [0.100, 0.500] | FAIL | 0.300 [0.100, 0.500] | reused |
| contribution | daymade github-contributor (MIT) | GLM-5.1 (0.40) | 10 | 0.200 [0.000, 0.400] | FAIL | 0.200 [0.000, 0.450] | reused |
| deep-code-review | Anthropic pr-review-toolkit code-reviewer | GLM-5.1 (0.50) | 10 | 0.700 [0.450, 0.950] | FAIL | 0.550 [0.250, 0.850] | regenerated |
| growth-analytics | marketingskills analytics and ab-testing | GLM-5.1 (0.55) | 10 | 0.250 [0.050, 0.450] | FAIL | 0.350 [0.100, 0.650] | regenerated |
| idea-critic | gstack plan-ceo-review | none (GLM-5.1 0.70, GLM-5.2 0.75, gpt-oss_120b 0.65) | 0 | no verdict: no judge with a healthy slot-1 rate | n/a | no verdict | regenerated |
| positioning | deanpeters Product-Manager-Skills positioning-statement (CC BY-NC-SA 4.0, fetched at run time, not vendored) | gpt-oss_120b (GLM-5.1 0.70, GLM-5.2 0.70, gpt-oss_120b 0.50) | 10 | 0.400 [0.200, 0.650] | FAIL | 0.500 [0.250, 0.750] | reused |
| product-discovery | phuryn pm-skills | GLM-5.1 (0.50) | 10 | 0.500 [0.250, 0.750] | FAIL | 0.350 [0.200, 0.500] | regenerated |
| product-output-safety | promptfoo redteam-setup | gpt-oss_120b (GLM-5.1 0.35, GLM-5.2 0.65, gpt-oss_120b 0.55) | 10 | 0.350 [0.100, 0.650] | FAIL | 0.400 [0.150, 0.700] | reused |

"Reused" = same Perun and rival text as the first run, so the same generated answers were judged again and only the judge changed. "Regenerated" = the Perun `SKILL.md` changed
on main after the first run (the rival text is unchanged), so both arms were regenerated; those rows compare a new skill text under a new judge.
The current directory per skill is `<skill>/heldout-<key>/` named in `summary.json`; the superseded first-run directories (`agentic-delivery/heldout-b9e6ca6c`, `deep-code-review/heldout-067073fa`,
`growth-analytics/heldout-270af892`, `idea-critic/heldout-ac4d4d61`, `product-discovery/heldout-208a9951`) are kept as history and their `results.json` are the first-run results.

Total spend $0.00. Win rate = mean over scenarios of 1 (Perun answer preferred in both orders), 0 (rival preferred in both orders) or 0.5 (the two orders disagree, or a tie).
CI = percentile bootstrap over scenarios, 10,000 resamples, seed 1. With n = 10 the CI is wide (about plus or minus 0.3): a row near 0.5 means "not separable at this n", not "equal".

## What changed in the judge, and what it measured (tune split only)

Problem: every PCSS judge typically picked the first-shown response 60 to 80 percent of the time, so the 0.4-0.6 slot-1 gate dropped them and three skills got no verdict.
Method: judge variants were tried on the tune split only (86 scenarios over 11 skills, both orders, so 172 verdicts per judge cell), never on the held-out set. Slot-1 rate = share of
non-tie verdicts that picked the first-shown response; the standard error of one cell is about 0.04, so differences under 0.05 are noise.
The variants were: neutral labels (random three-letter tokens instead of "Response 1"/"Response 2"), reason-first (the old prompt asked for the verdict before the reason, which gives a
reasoning model nothing to reason with), both together, a tie-encouraging prompt, a length-trimmed view (both answers cut to the shorter one's word count), other PCSS models, and
a control on identical answer pairs.

Slot-1 rate, tune split, per judge (old protocol "v1" = "Response 1/2" labels, verdict first; new "v2" = neutral labels, analysis first):

| Judge | v1 | v2 (shipped protocol) | Status |
|---|---|---|---|
| DeepSeek-V4-Flash | 0.650 | 0.817 | dropped: the reasoning reply made it worse |
| GLM-5.2 | 0.626 | 0.559 | fallback judge 2 |
| GLM-5.1 | 0.571 | 0.509 in the experiment harness, 0.439 in the shipped code (a different random label draw) | default judge |
| MiniMax-M2.5 | 0.690 | 0.580 | not used (no better than the three kept) |
| gpt-oss_120b | 0.612 | 0.592 | fallback judge 3 |

Which change helped, on the first four scenarios of each skill (about 85 verdicts per cell):

| Judge | v1 | neutral labels only | analysis first only | both (v2) |
|---|---|---|---|---|
| DeepSeek-V4-Flash | 0.722 | 0.613 | 0.845 | 0.817 |
| GLM-5.2 | 0.678 | 0.570 | 0.627 | 0.529 |
| MiniMax-M2.5 | 0.718 | 0.566 | 0.612 | 0.512 |
| gpt-oss_120b | 0.640 | 0.628 | 0.593 | 0.588 |

Neutral labels do most of the work; analysis-first helps the non-thinking and mid-size judges but makes DeepSeek-V4-Flash lean harder to slot 1. The other models tried with v2 on those
four-per-skill cells: GLM-5.3-Flash 0.450 but 57 percent of its calls returned no usable verdict; Qwen3.8-27B 0.667; MiMo-V2.5 0.882; DeepSeek-V3.1 0.843; gemma-4-26B-A4B-it 0.839.
Not shipped: a tie-encouraging prompt (GLM-5.2 0.494, GLM-5.1 0.455, gpt-oss_120b 0.642: mixed, inside the noise) and the length-trimmed view (GLM-5.2 0.558, gpt-oss_120b 0.557 on
the four-per-skill cells: no gain for GLM, a small one for gpt-oss, at the cost of cutting the answers). The identical-pair control is not informative: every judge answered "tie" on 93 to 100 percent
of identical pairs, so it shows no positional pull when there is nothing to choose, and no calibration pass was added.

Tune split, shipped code, per skill: all 11 skills get a used judge inside 0.4-0.6 (eight on GLM-5.1, three on GLM-5.2); under v1, four of the eleven had no judge.

## Judge health on the held-out run (position bias)

Pooled over the eleven held-out directories, verdicts from the v2 protocol:

| Judge | slot 1 | slot 2 | slot-1 rate | Runs |
|---|---|---|---|---|
| GLM-5.1 | 113 | 107 | 0.514 | all 11 skills |
| GLM-5.2 | 42 | 18 | 0.700 | the 3 skills where GLM-5.1 failed the gate: idea-critic, positioning, product-output-safety (a selection effect) |
| gpt-oss_120b | 34 | 26 | 0.567 | the same 3 skills, where GLM-5.2 failed too |

The judge actually used for a skill (the one inside the band) contributes 99 slot-1 and 101 slot-2 verdicts: pooled 0.495. First-run pooled rates for comparison: DeepSeek-V4-Flash 0.639, GLM-5.2 0.604.
The gate is applied per skill with at most 20 verdicts, so an unbiased judge still lands outside 0.4-0.6 on about one skill in three by chance; the three-judge chain exists for that.
idea-critic is the exception: the Perun and rival answers recommend the same decision in almost the same words (about 320 to 540 words each), the judges cannot separate them, and all three
fall back on slot 1 (0.65 to 0.75). That is a fixture problem (near-identical answers), not something a judge prompt fixes; the skill stays with no verdict rather than a biased number.
Because a win needs both orders to agree, slot bias cannot create a win on its own, but it can soften a true loss toward 0.5 (raising a losing rate) and widen the interval.

## Method

- Generator for both arms: Qwen3.5-397B-A17B on the PCSS endpoint, thinking disabled, temperature 0.3, no tools. Perun arm = the skill's `SKILL.md`
  as the system prompt; rival arm = the rival's public text. Same scenario text for both.
- Judge: rubric-free blind A/B, every pair judged in both orders. The two answers carry random three-letter labels (seeded per pair, so cached verdicts stay valid) and the judge writes a
  short comparison before the verdict. Judges in order: GLM-5.1, GLM-5.2 (both thinking disabled), gpt-oss_120b; the first whose slot-1 rate for the skill is inside 0.4-0.6 scores it.
  The generator is never a judge.
- Slot-1 rate = share of non-tie verdicts that chose the first-shown response. A position-unbiased judge sits near 0.5 because each pair is shown in both orders.
- Scenarios: `scripts/eval-fixtures/rival/<skill>/heldout.json` (hash pinned in `rival.json`, disjoint from the tune set). Raw outputs and every judge
  verdict are in this directory under `<skill>/heldout-<key>/`.
- Reproduce: `python3 scripts/rival_eval.py run --split heldout --jobs 8 --out <dir>` with `PCSS_KEY` in the environment or a repo-root `.env`. Hosted models are not bit-reproducible; the committed verdict files are.

## Caveats

- No tools in either arm; the rival texts that assume tools or sub-agents lose that part of their method here.
- Held-out scenarios for positioning, contribution, business-ops, agentic-ceo and agentic-delivery were drawn from a writer brief that never shows skill text;
  the five older text skills reuse the committed `docs/bench` scenarios (held-out ids prefixed `h`); deep-code-review reuses public OSS patches.
- Five rivals (positioning, contribution, business-ops, agentic-ceo, agentic-delivery) are fetched from their public URL at run time and cached outside the repo,
  not vendored; positioning's rival is CC BY-NC-SA and its text is not stored here.
- n = 10 per skill is the minimum the harness accepts; grow the held-out sets before reading small differences. Between the first run and this one, win rates moved by up to 0.2 on reused outputs
  (business-ops 0.400 to 0.200) purely from the judge change: single-run rows carry judge noise on top of the bootstrap interval.
- The judges were chosen on the tune split, by slot-1 rate and order agreement; none was checked against human labels. Slot-1 rate near 0.5 shows the judge is not position-driven, not that it is right.
- Outputs come from one generator model and judges from two other vendors' models (Zhipu GLM, an OpenAI-weights model); a different generator could change the picture.
