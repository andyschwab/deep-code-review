# Preregistration: communication-structure round 5, decision-brief mode (2026-10-17)

Written and hashed (SHA256-frozen.txt) before any scenario, seed or arm generation. Free PCSS models only; no `claude -p`.

## Question and owner decision
Round 4 (../comms-r4-1017/DIAGNOSIS.md) found the skill's ~150-word digest contract loses to a rival that writes a complete decision brief when the message asks its reader to decide. Owner decision: keep the ~150-word digest as the default and add a decision-brief mode (recommendation + rationale) for messages that ask for a decision. This round tests that addition.

## Arms (prompts/, built by mk_arms.py from SKILL.md at base commit 3d9a30ff; each arm's whole text is the generator's system prompt)
- V0: the unedited skill.
- E1: V0 + compact brief-mode section. E2: V0 + labelled brief skeleton. E3: V0 + E1 section + one worked Before/After brief.
- RIVAL: humanizer v3.1.0 text (prompts/RIVAL.txt, MIT, LICENSE.rival.txt), generated once per scenario and shared by every comparison.

## Harness
Judge v2 = scripts/rival_eval.py: no-rubric blind pairwise judge, random three-letter labels, analysis before verdict, both orders, strict agreement (win/loss only when both orders agree, else 0.5). Judge cascade GLM-5.1 -> GLM-5.2 -> gpt-oss_120b: the first whose pooled slot-1 rate (every arm vs RIVAL pooled, so both arms of a paired comparison share one judge) lies in 0.4 to 0.6 is the primary judge; the other two are reported as sensitivity only. Generator Qwen3.5-397B-A17B (never a judge), rival_eval.GEN_TASK, temperature 0.3, thinking off. Scenario and seed writer DeepSeek-V4-Flash. Bootstrap 95% CI: percentile, 10,000 resamples, seed 1, over scenarios.

## Scenarios
Tags: [ask] decision-asking notes for a senior reader (half state a lean, half none), [status] status notes with no decision, [diff] PR body from a diff summary, [report] executive summary of a long report whose reader must decide (half lean, half none). Tune n=10 (4 ask, 3 status, 2 diff, 1 report). Held-out n=60 (24 ask, 18 status, 9 diff, 9 report; 33 decision-asking, 27 not), written after selection, fresh seeds excluded against every earlier seed file, trigram-Jaccard overlap against every earlier scenario and this round's tune set printed (overlap_*.txt); hashed in SHA256-held.txt before any held-out arm is generated.

## Procedure and decision rules
1. Freeze: this file, prompts/, mk_arms.py, bench5.py hashed (SHA256-frozen.txt) before any generation.
2. Tune (n=10): generate V0, E1, E2, E3, RIVAL; judge; select the edit with the highest win rate vs RIVAL. Ties go to the shorter SKILL.md (E1 < E2 < E3). Tune never produces a verdict. Selection hashed (SHA256-selected.txt) before held-out scenarios are written.
3. Held-out (n=60): generate only V0, the selected edit and RIVAL, once. Never overwrite a record; a failed generation is reported, not retried after seeing scores.
4. SHIP the SKILL.md edit only if the paired difference (selected edit minus V0, per-scenario score under the primary judge) has a 95% bootstrap CI lower bound above 0 on the held-out set. Otherwise REVERT: no SKILL.md or eval edit ships, only this bench.
5. Superiority over humanizer may be claimed only if the selected edit's win rate against RIVAL has a 95% CI lower bound above 0.5. Failing this does not block SHIP; it is reported as "not superior".
6. Descriptive only, no rule attached: per-judge results, split by decision-asking vs no-decision tags, mean words, and the mean count of numeric tokens in an answer that are absent from the scenario (a fabrication proxy; a rise for the edit is reported as a risk).

## Known limits
One generator family, judges not Claude, regex-level fabrication proxy, scenarios written by a model, the skill written for Claude. A held-out pass is evidence for this host and judge set, not a general claim.
