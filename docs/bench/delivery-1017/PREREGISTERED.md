# Preregistration: agentic-delivery vs Superpowers and gstack ship on delivery plans (2026-10-17)

Frozen (SHA256-frozen.txt) after the tickets were generated and split and before the first plan was generated or judged. No paid `claude -p` call is made anywhere in this bench (plan quota exhausted); every call goes to the PCSS endpoint.

## Question

Does a model that is given the agentic-delivery SKILL.md produce better delivery plans than the same model given the rival skill text? Tune and held-out tickets are split so the skill can be edited on the tune set and checked once on tickets the edit never saw.

## Arms (system prompt only, no tools, same generator, same task wrapper `prompts/gen_task.txt`)

- PERUN: `.claude/skills/agentic-delivery/SKILL.md` at origin/main 3d69f4cda047e360b542c5dca4ccaeb233d81673 (frontmatter included), `prompts/perun.txt`. References and scripts are not available to the arm (no tools). Candidate edits are arm PERUN2 (`prompts/perun2.txt`).
- SP: obra/superpowers at commit bb92a77741419a4ab5f06e711a283343f1ada0c3 (HEAD of the default branch when fetched 2026-10-17 from raw.githubusercontent.com): `skills/subagent-driven-development/SKILL.md` then `skills/writing-plans/SKILL.md`, unmodified, concatenated in that order (`prompts/sp.txt`). Files those skills point at (prompt templates) are not available to the arm, the same limit PERUN has. License text in `rival/LICENSE.superpowers.txt` (fetched at the same commit).
- GS: garrytan/gstack at commit d258bcffb0cb7bda5f133f3e957f932d816d282f (HEAD of the default branch when fetched 2026-10-17): `ship/SKILL.md`, unmodified (`prompts/gs.txt`). License in `rival/LICENSE.gstack.txt`.
- Generator: Qwen3.5-397B-A17B on `https://llm.hpc.psnc.pl/v1`, temperature 0.7, max 2500 tokens, thinking disabled, one sample per ticket per arm. The task wrapper asks for lanes, gates, review and landing in under 600 words.

## Tickets

40 fictional tickets (`tickets.json`), written by Qwen3.5-397B-A17B from `prompts/writer_brief.txt` and the 20 archetypes in `prompts/seeds.txt` (two variants each, different industries). The writer never sees any skill. Each ticket carries repository facts a planner must respect (CI cost, shared files, approvals, irreversibility). Used unedited, none dropped. Split by `random.Random(1).shuffle` over sorted ids: first 16 are `tune`, remaining 24 are `held`. The split is stored in `tickets.json` and hashed.

## Judge

Rubric-free and blind: DeepSeek-V4-Flash sees the ticket, the repository facts and two plans labelled Response 1 and Response 2 with a randomized-by-construction order (both orders run per ticket), `prompts/judge.txt`, temperature 0, no checklist, verdict plus one sentence. A scenario score is the mean of 1 (PERUN arm preferred), 0.5 (tie), 0 over the two orders. Tiebreak: if that mean is not exactly 0 or 1 (split by order, or ties), GLM-5.2 judges the same pair in both orders and its two-order mean replaces the DeepSeek mean for that ticket. The four quality dimensions the owner cares about (gate correctness, parallelism, wasted steps such as duplicate CI and review passes, risk handling) are NOT given to the judge; they are only used afterwards to read the judge's reasons for root cause.

## Procedure

1. Baseline: generate PERUN, SP, GS on all 40 tickets; judge PERUN vs SP and PERUN vs GS. Report tune and held.
2. Root cause is read from the judge's reasons on TUNE tickets only (held-out reasons are not used to design the edit). Cluster reasons that favour the rival; the edit targets the clusters.
3. Edit agentic-delivery SKILL.md (and a reference where depth belongs) to address the clusters; mechanism in `evals/evals.json`. Up to three tune-only iterations (generate PERUN2 on tune, judge against both rivals on tune). Rival outputs are reused, never regenerated.
4. The final candidate is run on the held-out set once (generate PERUN2 on held, judge against the stored rival held outputs).

## Keep rule (the bar)

KEEP the edit only if, on the held-out set, the PERUN2 win rate against SP AND against GS each has a 95% bootstrap CI lower bound above 0.5 (bootstrap over tickets, 10,000 resamples, seed 1, percentile). Otherwise REVERT the SKILL.md and reference edits and ship only the bench artifacts. The baseline held-out result is reported plainly whichever way it falls; a tie or loss is reported as such. Pooled-over-rivals numbers are descriptive, not the bar.

## Caveats declared in advance

n=24 held tickets per rival is small (a lower bound above 0.5 needs a clear majority of wins); generator sampling is unseeded, so a re-run will differ; the writer, generator and judges are different model families from the one that wrote the skill but are all LLMs, and the tickets are synthetic. The arms run without tools, so any skill value that lives in scripts or references is not measured. Judge reasons cluster post hoc and are one reader's grouping.

## Amendment A1 (judge instrument only; made after the baseline plans were generated and judged once, before any skill edit)

Observed with the frozen non-thinking judges: DeepSeek-V4-Flash chose "Response 1" in 140 of 160 verdicts (see `judge/ds`, `judge/glm`, `results/perun__sp.json`, `results/perun__gs.json`), so most tickets score 0.5 by position alone and the bar cannot be met by anything short of a near sweep. That is an instrument defect, not a skill result. Declared selection test, run on the 16 tune tickets of PERUN vs SP only before any win rate was looked at: enable thinking on the judges, adopt it if the first-position share falls to 65% or below. Measured 17 of 32 (53%) first-position on DeepSeek-V4-Flash with thinking, so thinking judges (`JTHINK=1`, dirs `judge/ds-t`, `judge/glm-t`, `results/*-t.json`) replace the non-thinking ones for the baseline, the tune iterations and the held-out run. Everything else is unchanged (same plans, same two orders, same tiebreak rule). GLM-5.2 with thinking sometimes exceeds the 300 s call timeout; if its tiebreak never returns for a ticket, that ticket keeps the DeepSeek two-order mean (counted in `mixed` but not in `tiebroken`). The non-thinking baseline is kept and reported next to the thinking one. `bench.py` was edited for this (thinking switch, 300 s timeout with 3 attempts, tiebreak-missing fallback); frozen hashes of the original files stay in `SHA256-frozen.txt`, new hashes in `SHA256-amended.txt`.

## Amendment A2 (coordinator instruction, before any skill edit): strict two-order agreement is the bar

Every pair is already judged in both orders. The scoring that decides KEEP/REVERT is now strict: a win (or loss) counts only when both orders of the primary judge (DeepSeek-V4-Flash) agree; any split or tie scores 0.5. GLM-5.2's tiebreak (which replaces a non-0/1 score) is still computed and reported as a secondary column, but it does not decide. Each judge's slot-1 rate (share of verdicts naming Response 1; 0.5 is unbiased) is reported per pair in `results/*.json` under `slot1`. Non-thinking judges (frozen original): DeepSeek-V4-Flash 0.875, GLM-5.2 0.933.

## Outcome (written after the held-out run)

Decision: REVERT. The one tune-only iteration (PERUN2: a "Plan shape" section in `agentic-delivery/SKILL.md` plus three `plan-shape-*` evals, `prompts/perun2.txt`) did not clear the keep rule: held-out PERUN2 vs SP is 0.542, CI [0.396, 0.688], lower bound below 0.5. The SKILL.md and `evals/evals.json` edits were reverted; only bench artifacts ship. Strict scoring (A2), thinking DeepSeek-V4-Flash judge (A1), n=24 held, n=16 tune:

| Arm | Rival | Tune | Held | Held W/L/mixed |
|---|---|---|---|---|
| PERUN (baseline) | SP | 0.781 [0.625, 0.906] | 0.490 [0.354, 0.625] | 5/6/13 |
| PERUN (baseline) | GS | 0.625 [0.406, 0.812] | 0.667 [0.521, 0.792] | 11/3/10 |
| PERUN2 (rejected) | SP | 0.781 [0.656, 0.906] | 0.542 [0.396, 0.688] | 8/6/10 |
| PERUN2 (rejected) | GS | 0.656 [0.500, 0.812] | 0.667 [0.542, 0.792] | 10/2/12 |

Non-thinking frozen judge, baseline, strict: held 0.542 [0.458, 0.625] vs SP, 0.562 [0.500, 0.625] vs GS.

Slot-1 rate (share of verdicts naming Response 1; 0.5 is unbiased), DeepSeek-V4-Flash: non-thinking 0.875 (GLM-5.2 0.933); thinking baseline 0.638 vs SP and 0.650 vs GS; thinking PERUN2 0.688 vs SP and 0.763 vs GS. Thinking judges are still position-biased, which is why the strict two-order rule decides.

Reading: the baseline already beats GS on held-out (lower bound 0.521) and ties SP (0.490). The edit moved held-out vs SP by +0.052, inside noise at n=24, so it is not kept. The baseline's tune vs held gap against SP (0.781 vs 0.490) shows the 16-ticket tune set is noisy too.

Further caveats: GLM-5.2 with thinking timed out on most tiebreak calls (44 logged errors in `ledger.jsonl`), so `judge/glm-t` was deleted at finalize and the thinking `tiebroken` column equals `strict`; a GLM tiebreak is reported only for the non-thinking baseline. Some background `bench.py` jobs could not be stopped from the sandbox (no PIDs available); they only write judge files for the same pairs, and `finalize.sh` was run last. Tickets, plans and judges are all LLM output and the arms run without tools, as declared above.

## Spend

0 paid calls. PCSS calls are logged in `ledger.jsonl` (model and token usage, no key, no prompts).
