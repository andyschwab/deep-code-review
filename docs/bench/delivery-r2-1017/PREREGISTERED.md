# Preregistration: agentic-delivery round 2, clean held-out replication (2026-10-17)

Frozen with `SHA256-frozen.txt` and a timestamped `ledger.jsonl` line before any ticket, plan or judge record of this round exists. All calls go to the PCSS endpoint ($0, no paid call).

## Why this round exists

Round 1 (`../delivery-r1-1017`) shipped a SKILL.md edit on a held-out win rate of 0.688 [0.588, 0.775] against Superpowers. Its `bench.py` had a defect: its tune split reused ticket ids 01b..12b, which are also held-out ids, and `gen` and `judge` skip files that already exist, so 10 held-out tickets silently reused tune-ticket outputs for sp, v0 and e1. On the 30 clean tickets the paired ship minus v0 difference is -0.050 [-0.183, 0.083] and the round-1 keep rule fails (see `../delivery-r1-1017/ERRATA.md`). This round re-tests the same edit on fresh tickets, with a new id namespace and new output directories, so nothing can collide.

## Design

- Tickets: 40 new tickets, ids `h2-01` to `h2-40`, one per archetype in `prompts/seeds.txt` (40 archetypes not used in `../delivery-1017` or `../delivery-r1-1017`), written by Qwen3.5-397B-A17B with the round-0 writer brief. Never edited, never dropped.
- Arms: `sp` = Superpowers text (`../delivery-1017/prompts/sp.txt`, generated once per ticket); `v0` = origin/main `agentic-delivery/SKILL.md` (`prompts/v0.txt`); `ship` = the branch SKILL.md as shipped in PR #1641 (`prompts/ship.txt`). Generator Qwen3.5-397B-A17B, temperature 0.7, unseeded, 2500 max tokens, one plan per arm per ticket, round-0 generation task (600-word cap). Arms run without tools.
- Judge: prompt v2 from `scripts/rival_eval.py` (`JUDGE_SYSTEM`: random neutral three-letter labels, a short analysis before the verdict, no rubric), imported unchanged. Three judges (DeepSeek-V4-Flash with thinking, GLM-5.2, gpt-oss_120b), each in both orders. The generator is never a judge.
- Scoring: per judge, a ticket is a win or loss only if both orders agree, else 0.5; per ticket, a win or loss needs at least 2 of 3 judges, else 0.5 (majority). Win rate is the mean over the 40 tickets; 95% intervals are percentile bootstrap over tickets (10000 resamples, seed 1). The paired difference is the bootstrap of the per-ticket (ship minus v0) majority scores. Judge slot-1 rates are reported as a health metric.

## Decision rules (fixed now)

1. SHIP the SKILL.md edit only if the paired ship minus v0 95% CI lower bound is above 0. Otherwise revert `SKILL.md` and its eval to origin/main and keep the bench only.
2. A superiority claim over Superpowers needs the ship win rate vs sp to have a CI lower bound above 0.5. Without it no such claim is made.
3. The result is reported plainly whichever way it falls. No arm, ticket or judge record is dropped, edited or regenerated after seeing a result; a failed call (nothing written) may be re-run.

## Caveats declared in advance

n=40 has little power: a true paired lift of +0.075 will usually give a lower bound below 0, so a failing rule 1 means "not shown", not "shown harmful". Generator sampling is unseeded; a re-run differs. Judges are position-biased, which is why strict two-order agreement and a 3-judge majority decide. Tickets, plans and judges are LLM output; arms run without tools, so value that lives in scripts or references is not measured.
