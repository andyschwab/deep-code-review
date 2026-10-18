# Preregistration: first n=60 held-out bench of growth-analytics and product-output-safety (2026-10-18)

This file is hashed (SHA256-prereg.txt) before any seed, scenario or answer is generated. Base commit: origin/main at 7c8b4065.

## Question

Do the currently shipped `growth-analytics` and `product-output-safety` skills beat their H1 rivals on a fresh held-out set of 60
scenarios each, judged blind with `scripts/rival_eval.py` judge protocol v2? Neither skill has a confirmed win: growth-analytics
was 0.700 [0.500, 0.900] and product-output-safety 0.550 [0.400, 0.700] at n=10 (`docs/perun-vs-rivals.md`, H1 and H1b/H1d). This is a
baseline measurement, not an improvement run: no skill text, rival text, harness code, judge prompt or generator setting is edited
between this file and the result, and a loss is published as is.

Rivals (the H1 rows, texts already committed under `docs/bench/`): growth-analytics against the marketingskills `analytics` and
`ab-testing` skills (`docs/bench/growth-analytics-rubricfree-1016/prompts/rival.txt`); product-output-safety against the promptfoo
redteam-setup skill (`docs/bench/pos-1016/prompts/rival.txt`).

## Fixed design (the protocol of `docs/bench/confirm-v2-1017`)

- Harness: `scripts/rival_eval.py` unchanged. `bench.py` (a copy of `confirm-v2-1017/confirm.py`) only supplies fixtures, the freeze
  hashes and the ledger. Two changes from confirm.py, both made before the prereg hash: writer batches are 10 scenarios (the skills'
  writer briefs say "exactly 10", and the product-output-safety brief fixes which of the 10 carry pressure to overclaim), and
  scenario ids are prefixed `ga` and `po` so they differ from every earlier `h01`, `01` and `n01` id.
- Perun arm: the skill's `SKILL.md` as the system prompt, as on the base commit. Rival arm: the rival text above. Both answer every
  scenario once; no tools. Generator: Qwen3.5-397B-A17B (non-thinking, temperature 0.3), PCSS only, never a judge. No `claude -p`.
- Judge v2: reason-first JSON, neutral random three-letter labels, both orders. A scenario scores 1 or 0 only when both orders agree on
  the same arm, else 0.5. Judge chain GLM-5.1, then GLM-5.2, then gpt-oss_120b: the first whose slot-1 rate (share of decisive picks in
  the first position) is inside 0.4 to 0.6 scores the skill; all biased means no verdict. Each judge's slot-1 rate is reported.
- Scenarios: 60 per skill, fresh. Seeds are drawn by the generator with instructions to avoid the skill's existing seeds and are
  rejected if close to any existing bench seed. Scenarios are written in batches of 10 from the skill's own existing writer brief.
  Any scenario sharing more than 10% of its 6-word shingles with the `docs/bench` corpus (outputs, judge records and this run's own
  directory excluded) or with another new scenario is regenerated before freezing, so the set is disjoint by id and text from all
  earlier sets. The harness split check and `scripts/bench_check.py` must pass. Held-out scenarios are frozen by hash
  (SHA256-frozen.txt) and the `preregistered` event in `ledger.jsonl` records the sha256 of that file before any answer is generated.
- Answers are generated once per scenario and cached; nothing is regenerated, re-judged with a different protocol, or dropped after
  the fact. A failed generation or an unusable verdict removes that scenario from n and is reported.

## Analysis and decision rule

- Win rate = mean of per-scenario scores. 95% CI = percentile bootstrap over scenarios, 10,000 resamples, seed 1.
- PASS for a skill = CI lower bound above 0.5. Otherwise FAIL. No verdict (all judges biased, or n under 10) counts as not PASS.
- Each skill is judged on its own; no multiplicity correction (two tests, reported as two). A FAIL stays a FAIL: it is not retried,
  re-seeded or re-judged on this set.
- Reported per skill: n, win rate and CI, verdict, judge used, slot-1 rate of every judge tried, errors verbatim.

## Known limits (stated up front)

One generator family wrote the scenarios and both arms' answers; the judges are other models; scenarios are fictional. A PASS here
supports "beats this rival on this fictional scenario distribution under this judge", not a claim about real users. The
product-output-safety rival is a tool-driven red-team skill run without its tools.
