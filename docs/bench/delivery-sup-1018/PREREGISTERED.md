# Preregistration: shipped agentic-delivery vs Superpowers, n=150 forward test (2026-10-18)

Scenarios file: tickets.json

Frozen with `SHA256-frozen.txt` and a timestamped `preregistered` line as the first line of `ledger.jsonl` before any archetype, ticket, plan or judge record of this bench exists. All model calls go to the PCSS endpoint ($0, no paid call). Base: `origin/main` commit `06e6fa48d34d97270b77d316895ec1b643470fa4` (docs/bench tree `11db29e31bab0eb9482c23515997fe856aa4e338`), `agentic-delivery` version 1.593.0.

## Question and disclosure

Does the shipped `agentic-delivery/SKILL.md`, unedited, beat Superpowers on delivery plans? This is a re-test of a near miss, so its multiplicity is stated here:

- `delivery-1017` (n=24 held-out): the baseline skill scored 0.490 [0.354, 0.625] against Superpowers, a tie.
- `delivery-r1-1017`: reported 0.688 [0.588, 0.775] for an edited text; withdrawn (id collision, `delivery-r1-1017/ERRATA.md`).
- `delivery-r2-1017` (n=40): the shipped text scored 0.562 [0.487, 0.637], lower bound below 0.5, the near miss this bench follows up.
- `delivery-r3-1018` (n=60 held-out): the unedited text scored 0.517 [0.450, 0.583], also not a win.

So this is the fourth look at one claim, run after two non-wins. A pass here is one pass among several looks and is reported as such. The pooled earlier evidence points at a tie, which is why n is raised to 150. No Bonferroni-style adjustment is applied to the rule below; the reader should weigh this bench together with the rounds above, not alone.

## Design (same as `../delivery-r2-1017` except n, ids and the single arm)

- Scenarios: 150 fresh tickets `sup-001` to `sup-150`, one per archetype. The archetypes are written by Qwen3.5-397B-A17B (`prompts/seed_brief.txt`, 15 industries, 14 candidate lines each, accepted round-robin in order until 150 pass a word-Jaccard gate of at most 0.22 against every earlier `*seeds.txt` under `docs/bench` and against each earlier accepted archetype). Tickets are written by the same model with the round-0 writer brief (`../delivery-1017/prompts/writer_brief.txt`), temperature 0.9, unseeded. The seeds and tickets steps may be re-run until they produce 150 passing items, but only before their `seeds_frozen` and `tickets_frozen` ledger events; after that no ticket is edited, dropped or redrawn.
- Disjointness (checked by `bench.py tickets` before freezing, re-checked by `scripts/bench_check.py`): ids use the new namespace `sup-` and no earlier bench scenario id starts with it; no title equals an earlier bench ticket title; the share of a ticket's 6-word shingles (lowercased word tokens of title, ticket and repo_context) found in the union of every other `docs/bench` scenario file, or in earlier-accepted new tickets, is at most 0.10. A ticket above 0.10 is redrawn (up to 6 redraws) before any plan exists; if it still fails, the step aborts and nothing is dropped silently.
- Arms: `sp` = the Superpowers text (`../delivery-1017/prompts/sp.txt`) and `ship` = the shipped `.claude/skills/agentic-delivery/SKILL.md` at the base commit (`prompts/ship.txt`, byte-identical, hash in `SHA256-frozen.txt`). No edit, no tuning, no tune split. Generator Qwen3.5-397B-A17B, temperature 0.7, unseeded, 2500 max tokens, one plan per arm per ticket, the round-0 generation task (`../delivery-1017/prompts/gen_task.txt`, 600-word cap). Arms run without tools.
- Judge: prompt v2 from `scripts/rival_eval.py` (`JUDGE_SYSTEM`, random neutral three-letter labels, short analysis before the verdict, no rubric), unchanged. Panel: DeepSeek-V4-Flash with thinking, GLM-5.2, gpt-oss_120b, each in both orders. The generator is never a judge.
- Scoring: per judge, a ticket is a win or loss only if both orders agree, else 0.5; per ticket, a win or loss needs at least 2 of 3 judges, else 0.5. Win rate is the mean over the 150 tickets; the 95% interval is a percentile bootstrap over tickets (10000 resamples, seed 1). Judge slot-1 rates are reported as a health metric. The scoring code is `bench.py`, the r2 code with the same functions.

## Decision rule (fixed now)

Claim superiority over Superpowers if and only if the `ship` win rate against `sp` has a 95% CI lower bound above 0.5. Otherwise no superiority claim is made. The result is reported plainly whichever way it falls. No arm, ticket or judge record is dropped, edited or regenerated after seeing a result; a failed call (nothing written) may be re-run. The `agentic-delivery` row of `docs/perun-vs-rivals.md` is updated with the result and is marked a win only if the rule passes.

## Caveats declared in advance

Back-of-envelope power from r2's tie share (31 of 40 tickets at 0.5, per-ticket sd about 0.23): at n=150 the interval half-width is about 0.037, so a pass needs an observed rate near 0.54 or higher; if the true rate were 0.56 a pass is likely (roughly 0.9), if it were 0.52 a pass is very unlikely. This is an estimate from one earlier run, not a guarantee. Tickets, plans and judges are LLM output from one generator family; judges are position-biased, which is why strict two-order agreement and a 3-judge majority decide. Arms run without tools, so value that lives in scripts or references is not measured. A win means "beats this rival on this synthetic distribution under this judge panel", not a claim about real users. Generator sampling is unseeded; a re-run differs.
