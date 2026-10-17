# Preregistration: loss-fix re-test of communication-structure and product-discovery, free PCSS models (2026-10-17)

Written and hashed (SHA256-frozen.txt) before the first scenario or generation call. Only a one-token connectivity ping preceded it. No Claude call is made: the weekly Claude quota was at 1.0, so every call goes to the PCSS endpoint at no cost ($0; each call's token usage is in `ledger.jsonl`).

## Why

Two measured losses on a rubric-free blind judge: communication-structure lost to humanizer 0.100 [0.000, 0.300] (H1e, docs/bench/comms-quality-1016) and product-discovery lost to phuryn/pm-skills 0.300 [0.100, 0.500] (H1d, docs/bench/product-discovery-rubricfree-1016). Root causes found in the judge reasons and the skill text:

- product-discovery: 9 of 10 loss reasons say the Perun answer left kill thresholds, sample sizes and decision rules blank while the rival filled them. Cause: `SKILL.md` told the model to "leave the slot blank rather than guessing". Edit: propose a labelled starting value derived by arithmetic from figures the user gave, show the basis, add a go / narrow / drop rule, say the user adjusts it; blank only when no figure was given. One new and one updated eval.
- communication-structure: the stand-in clutter, invented content and weekday errors were already removed in the shipped revision (never measured against humanizer). The remaining cause is `SKILL.md` "~150 words ... the budgets are the ceilings. Longer needs a reason per block, or a cut", which made answers drop facts ("cut for a nonexistent length limit", "terse"). Edit: line 1 and the ask carry the 30 seconds; budgets are targets; keep every source fact the reader needs to act on or check; never cite a length limit the request did not set. One new eval.

## Arms (system prompt only, no tools, one model, one task wrapper)

Generator for every arm: Qwen3.5-397B-A17B on the PCSS endpoint, temperature 0.7, max_tokens 3000, thinking off, identical for all arms.

- PERUN: the edited skill. communication-structure: `SKILL.md` plus `references/artifact-templates.md` (`prompts/cs_perun.txt`); product-discovery: `SKILL.md` (`prompts/pd_perun.txt`). No lint-and-rewrite loop (the pre-send hook only warns and never blocks).
- RIVAL: the same rival as the original runs, unmodified: humanizer v3.1.0 (`prompts/cs_rival.txt`, copied from comms-rubricfree-1016, MIT) and phuryn/pm-skills 3 SKILL.md files (`prompts/pd_rival.txt`, copied from product-discovery-rubricfree-1016, MIT).
- BASE (descriptive only, not part of the keep rule): the skill as on origin/main before the edit, same generator, to show whether the edit changed anything.
- Task wrappers and judge sentence are byte-identical to the original runs (`cs_*` from comms-quality-1016, `pd_*` from product-discovery-rubricfree-1016).

## Scenarios

20 fresh scenarios per skill (`prompts/cs_seeds.txt`, `prompts/pd_seeds.txt`; the seeds differ from the H1d and H1e sets), written by GLM-5.1 in two batches of 10 from the earlier writer briefs (the writer never sees a skill; GLM-5.1 is neither generator nor judge). Used unedited, none dropped. Public, fictional data only.

## Judges (no rubric, blind, randomized order)

Primary: DeepSeek-V4-Flash, both orders per scenario (`prompts/*_judge.txt`, no criteria, verdict only). If its two orders agree on a non-tie, that is the scenario's verdict (1 or 0). If they disagree or tie, GLM-5.2 decides with one call in a seeded random order (1, 0 or 0.5 for a tie). The generator model is never a judge. The original Claude judge is not run (quota). Also reported, descriptive: the DeepSeek-only mean over both orders.

## Keep rule (per skill, PERUN over RIVAL)

Win rate over the 20 scenarios with a bootstrap 95% CI (10,000 resamples, seed 1, percentile) whose lower bound is above 0.5. Both skills are evaluated separately. KEEP the edit only if it passes; otherwise REVERT the SKILL.md and eval edits and commit the bench only. No re-runs after seeing results, no edits to the arms after the freeze, no multiple-comparison correction.

## Caveats (state with any outcome)

- The host is a non-Claude model: both skills were written and tuned against Claude. A pass here does not show the skill wins on Claude; a fail does not show it loses there. Only a Claude run on the original judge could show that, and none is possible while the quota is exhausted.
- The judges are non-Claude models of two families that the original runs never used; the originals used a Claude judge. Rates are not comparable with H1d or H1e.
- n=20 per skill, one set, sampling not seeded, no lint loop for communication-structure, references of product-discovery unavailable (no tools). The three-arm design does not isolate the effect of the earlier shipped communication-structure revision from the new edit; BASE shows the edit's marginal effect only.
