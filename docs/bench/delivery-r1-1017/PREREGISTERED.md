# Preregistration: agentic-delivery round 1 vs Superpowers (2026-10-17)

Frozen with `SHA256-frozen.txt` before any held-out plan is generated or judged. All calls go to the PCSS endpoint ($0, no paid call). The round-0 bench (`../delivery-1017`) found a tie with Superpowers on delivery plans (0.490 held, CI [0.354, 0.625]) and one rejected edit. This round tries three smaller edits derived from the round-0 judge reasons, on fresh scenarios.

## Root cause (round-0 judge reasons where Superpowers won or tied, plus a read of the paired plans; `../delivery-1017/judge/ds-t`)

Superpowers plans win on behaviours that the baseline SKILL.md does not state for a plan answer:
1. Cheapest check first and a costly CI run once per candidate (baseline plans re-run the $12 suite on the merged SHA and use gate numbers G1/G4/G5 and role titles instead of the ticket's files and tests).
2. An irreversible or outward step is dry-run on a snapshot or shipped dark behind a kill switch, rolled back code-first and data-last, and published only in the final change (judges cite "feature flag", "dry-run", "runtime kill switch", "disables external publication until the final PR").
3. Each ticket fact and tempting shortcut gets an explicit decision (flaky check retried with its log cited, locked file touched with owner approval, review not dropped under deadline).

## Arms

Generator Qwen3.5-397B-A17B, temperature 0.7, 2500 max tokens, thinking off, system prompt = skill text, no tools, one sample per ticket per arm, task wrapper `../delivery-1017/prompts/gen_task.txt`.
- v0: `.claude/skills/agentic-delivery/SKILL.md` at origin/main 78ab50cf (`prompts/v0.txt`).
- e1, e2, e3: v0 plus the paragraph in `edits/e1.txt`, `edits/e2.txt`, `edits/e3.txt`, inserted before the "No files/tools (plain chat)?" paragraph. `all`: v0 plus the three.
- sp: obra/superpowers subagent-driven-development then writing-plans, the text in `../delivery-1017/prompts/sp.txt` (commit bb92a77), generated ONCE per ticket and reused for every Perun arm. Tune plans are the round-0 plans, copied.

## Scenarios

- Tune, n=10: the first 10 sorted ids of the round-0 tune split (01b 02a 03b 05b 06b 09b 11a 11b 12a 12b). Their judge reasons were read to design the edits.
- Held-out, n=40: 20 NEW archetypes (`prompts/seeds_held.txt`, none shared with the round-0 seeds or `scripts/eval-fixtures/rival/agentic-delivery/seeds.txt`) x 2 variants, written by Qwen3.5-397B-A17B from the round-0 writer brief; the writer never sees any skill. Used unedited, none dropped. No held-out text was read before this file was frozen, and no edit is changed after the first held-out plan is generated.

## Judges and scoring

Three blind, rubric-free judges, temperature 0, prompt `../delivery-1017/prompts/judge.txt`, each pair judged in both orders: DeepSeek-V4-Flash (thinking on), GLM-5.2 (thinking off; thinking timed out in round 0), gpt-oss_120b (default). The generator is never a judge. Per judge and scenario, strict: a win or loss counts only when both orders agree, else 0.5. Scenario score = majority over the three judges (at least two wins = 1, at least two losses = 0, else 0.5). Win rate = mean scenario score; CI = percentile bootstrap over scenarios, 10,000 resamples, seed 1. Per-judge win rates and slot-1 rates (share of verdicts naming Response 1) are reported as health metrics, not as the bar.
Each judge record is written once (`open(f, "x")`); an existing record is never overwritten and a failed call writes nothing, so a failed parallel pass cannot null a completed record. `score` refuses to run until all 6 records per scenario exist.

## Procedure and keep rule

1. Tune: generate v0, e1, e2, e3, all and sp on the 10 tune tickets; judge each against sp.
2. Candidate = the arm with the highest tune win rate vs sp, ties broken toward the smaller edit (e1, e2, e3, then all). If the best is below v0's tune win rate, nothing proceeds to held-out: revert, bench artifacts only.
3. Held-out, once: generate v0 and the candidate on the 40 held tickets (and sp once); judge both against sp.
4. KEEP the edit(s) only if candidate held win rate vs sp has CI lower bound above 0.5 AND its win rate is at least v0's held win rate. Otherwise revert and ship only the bench. The held result is reported plainly whichever way it falls.

## Caveats declared in advance

n=10 tune is noise-dominated (CI about plus or minus 0.3). n=40 needs roughly 0.64 or higher for a lower bound above 0.5. Generator sampling is unseeded, so a re-run differs. Arms run without tools, so value that lives in scripts or references is not measured. Tickets, plans and judges are LLM output; judges are position-biased, which is why strict two-order agreement and a 3-judge majority decide.

## Amendment A1 (harness defect, before any held-out plan; no result was used)

The first tune pass ran with the network gate closed (HTTP 403 on every call after the launching shell exited), and `bench.py gen` opened the output file before calling the model, so each failed call left an empty plan file; 43 empty files were then judged as if they were plans (judges named the empty side the loser). Fix: `gen` calls the model first and writes the file only on success. The empty plan files were deleted, and the whole first tune pass (`void-tune-pass1/judge`, `void-tune-pass1/results`) was moved aside unscored and is not used; the non-empty plans that existed were kept, the rest regenerated, and the tune pass was re-run in full. `bench.py` and its hash in `SHA256-frozen.txt` were updated; no arm text, scenario, judge, scoring rule or keep rule changed.

## Outcome (written after the held-out runs; `SHA256-frozen.txt` lists the original hashes taken before any held-out plan, then later lines for `bench.py` and `PREREGISTERED.md` after Amendment A2 and for `prompts/ship.txt`, then the final `PREREGISTERED.md`; the post-A1 `bench.py` was not hashed on its own)

Tune (n=10, 3 judges strict, majority) vs sp: v0 0.550 [0.500, 0.650]; e1 0.650 [0.500, 0.800]; e2 0.600 [0.400, 0.800]; e3 0.550 [0.400, 0.700]; all 0.650 [0.500, 0.800]. e1 and all tie at the top; the smaller edit wins the tie, so the candidate is e1 (0.650 is at or above v0's 0.550, so it proceeded).

Held-out (n=40 fresh tickets, one generation per arm per ticket, sp generated once), win rate vs Superpowers:

| Arm | Win rate [95% CI] | W / L / mixed | DeepSeek-V4-Flash | GLM-5.2 | gpt-oss_120b | Slot-1 rate (ds, glm, j3) |
|---|---|---|---|---|---|---|
| v0 (origin/main) | 0.613 [0.537, 0.688] | 11 / 2 / 27 | 0.600 | 0.562 | 0.575 | 0.75, 0.91, 0.75 |
| e1 (candidate) | 0.637 [0.550, 0.725] | 13 / 2 / 25 | 0.675 | 0.537 | 0.637 | 0.68, 0.96, 0.71 |

Decision on e1: it met the keep rule (lower bound 0.550 is above 0.5, and 0.637 is at least v0's 0.613). e2 and e3 were not carried to held-out and are bench-only. The text that ships is `ship` (Amendment A2), judged next.

Reading, stated plainly: (1) the unedited v0 already clears the bar against Superpowers on this held-out set (lower bound 0.537), unlike the round-0 tie (0.490 [0.354, 0.625]); the instruments differ (three judges, strict agreement, majority, fresh tickets, 600-word plans), so the two results are not comparable. (2) e1 minus v0 is +0.025 (paired bootstrap over scenarios, 95% CI [-0.088, 0.125], 9 scenarios up, 8 down): the edit is not distinguishable from v0, so the held-out result does not show that e1 helps; it shows only that it does not hurt and meets the keep rule. (3) All three judges are position-biased (slot-1 0.68-0.96), which is why 25-27 of 40 scenarios are 0.5 under strict agreement; a bar of "lower bound above 0.5" therefore rewards a few clean wins. (4) The generator is not any judge's family, but all models, tickets and plans are LLM output, arms run without tools, and the plans are capped at 600 words.

## Spend

0 paid calls. `ledger.jsonl` logs every PCSS call (model, token usage, no key, no prompt); its 302 error lines are the 403 failures of the voided first tune pass plus one probe of an unsupported model (Devstral, HTTP 400) made while choosing the third judge, and a few retried timeouts.

## Amendment A2 (after the held-out run of v0 and e1; the shipped text must be what is judged)

The e1 arm text is v0 plus the paragraph, 24346 bytes. The repository's routing gate caps `agentic-delivery/SKILL.md` at 24000 bytes (`scripts/test-ci-gates.sh`, "within the 24000-byte cap"), so the paragraph cannot ship as tested. The shipped file (`prompts/ship.txt`) is e1 with about 370 bytes of other wording tightened (a citation clause, a stacked-lane sentence, one unattended-mode sentence, one failure bullet, a roster phrase, a Shape Up aside, a heading parenthetical), 23978 bytes, 11 below the old budget, so no size-budget raise is needed. Because that wording differs from the tested e1 arm, the shipped text is judged as arm `ship` on the same 40 held-out tickets (new sample, same sp plans, same judges, same scoring). Rule: KEEP only if ship's held win rate vs sp has a CI lower bound above 0.5 AND is at least v0's held win rate (0.613 from the run above); otherwise revert the SKILL.md edit and ship the bench only. The e1 result above stays reported as measured; the final decision rests on `ship`.

### Held-out, shipped text (Amendment A2)

| Arm | Win rate [95% CI] | W / L / mixed | DeepSeek-V4-Flash | GLM-5.2 | gpt-oss_120b | Slot-1 rate (ds, glm, j3) |
|---|---|---|---|---|---|---|
| ship (shipped SKILL.md) | 0.688 [0.588, 0.775] | 18 / 3 / 19 | 0.713 | 0.625 | 0.662 | 0.66, 0.82, 0.69 |

Decision: KEEP. ship's lower bound 0.588 is above 0.5 and 0.688 is at least v0's 0.613 (A2 rule). Paired ship minus v0 is +0.075 (95% CI [-0.050, 0.188], 15 scenarios up, 8 down): positive, but the interval includes zero, so the edit is not shown to beat the unedited skill at n=40. What is shown: both the baseline and the shipped skill beat Superpowers on this held-out set (lower bounds 0.537 and 0.588). The ship, e1 and v0 results are three separate samples (one generation per ticket each), so the spread between e1 (0.637) and ship (0.688) is sampling noise plus the small wording difference, which this bench cannot separate. All three arms were judged by judges with slot-1 rates between 0.66 and 0.96.
