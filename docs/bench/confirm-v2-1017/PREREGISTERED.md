# Preregistration: confirmation run, judge protocol v2 (2026-10-17)

This file is hashed (SHA256-prereg.txt) before any seed, scenario or answer is generated.

## Question

Do the currently shipped `agentic-ceo`, `positioning` and `product-discovery` skills beat their public rivals on a fresh held-out
set, judged blind with `scripts/rival_eval.py` judge protocol v2? This is a confirmation run, not an improvement run: no skill text,
rival text, harness code, judge prompt or generator setting is edited between this file and the result.

## Fixed design

- Harness: `scripts/rival_eval.py` at the commit recorded in the run's git history, unchanged. `confirm.py` only supplies fixtures
  (it points `rival_eval.FIX` at `fixtures/`) and writes the freeze hashes.
- Perun arm: the skill's `SKILL.md` as the system prompt, as shipped on origin/main at the base commit. Rival arm: each skill's
  configured rival text (`rival.json`, hash recorded in SHA256-prereg.txt). Both answer every scenario once; no tools.
- Generator: Qwen3.5-397B-A17B (non-thinking, temperature 0.3), PCSS. Never a judge.
- Judge v2: reason-first JSON ("analysis" then "verdict"), neutral random three-letter labels, both orders. A scenario scores 1 or 0
  only when both orders agree on the same arm, else 0.5. Judge chain GLM-5.1, then GLM-5.2, then gpt-oss_120b: the first whose
  slot-1 rate (share of decisive picks in the first position) is inside 0.4 to 0.6 scores the skill; all biased means no verdict.
  Each judge's slot-1 rate is reported.
- Scenarios: 60 per skill, fresh. Seeds are drawn by the generator model with instructions to avoid the skill's existing seeds and
  are rejected if close to any existing bench seed. Scenarios are written in batches of 6 from the skill's own existing writer
  brief (the same brief that produced its current held-out set). Disjoint from the skill's frozen held-out and tune sets and from
  every scenario, seed and prompt file under `docs/bench` (outputs and judge records excluded): any scenario sharing more than
  10% of its 6-word shingles with that corpus, or with another new scenario, is regenerated before freezing. The harness's own
  split check (frozen hash, disjoint from tune, no duplicates) must also pass. The new set is frozen by hash
  (SHA256-frozen.txt) before any answer is generated.
- Rival answers are generated once per scenario and cached; nothing is regenerated, re-judged with a different protocol, or
  dropped after the fact. A failed generation or an unusable verdict removes that scenario from n and is reported.

## Analysis and decision rule

- Win rate = mean of per-scenario scores. 95% CI = percentile bootstrap over scenarios, 10,000 resamples, seed 1 (as in the harness).
- PASS for a skill = CI lower bound above 0.5. Otherwise FAIL. No verdict (all judges biased, or n under 10) counts as not PASS.
- Each skill is judged on its own; no multiplicity correction (three tests, reported as three). A FAIL stays a FAIL: it is
  published as is and is not retried, re-seeded or re-judged on this set.
- Reported per skill: n, win rate and CI, verdict, judge used, slot-1 rate of every judge tried, errors verbatim.

## Known limits (stated up front)

One generator family wrote the scenarios and both arms' answers; the judges are other models but synthetic. A PASS here supports
"beats this rival on this fictional scenario distribution under this judge", not a claim about real users.
