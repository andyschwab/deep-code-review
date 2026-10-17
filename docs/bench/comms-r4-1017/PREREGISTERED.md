# Preregistration: communication-structure round 4 against humanizer, free PCSS models only (2026-10-17)

Written and hashed (SHA256-frozen.txt) before any scenario was written and before any generation or judge call of round 4. No Claude call is made; every call goes to the PCSS endpoint at no cost (ledger.jsonl records each call's token usage). Only the topic seeds (prompts/tune_seeds.txt, prompts/held_seeds.txt) existed when this file was hashed.

## Why a structural round

Rounds 2 and 3 and the loss-fix re-test (../comms-round2-1017, ../comms-round3-1017, ../loss-fix-1017) each edited wording of the same skill text and each failed the bar: 0.438, 0.325 and 0.175 against humanizer v3.1.0 (unedited skill 0.312, 0.212, 0.150). DIAGNOSIS.md (this directory, numbers reproduced by diagnose.py) reads the judge reasons of all 1,334 verdicts and finds a structural cause: the skill's output contract is a compressed digest (about 150 words, "core value only", no rationale, no recommendation, three findings), while the blind "which would you rather receive" judges reward a complete decision brief: every option with its cost, time and risk, a stated recommendation with a next step, and no leftover meta text. Per scenario, the ratio of our answer length to the rival's correlates with the rival's share of verdicts at -0.39 to -0.67 on the 40-scenario held-out sets. The earlier README claim that length was not the cause compared totals, not per-scenario ratios.

## Arms (prompts/*.txt; SHA256-frozen.txt)

Every skill arm is SKILL.md plus references/artifact-templates.md joined as in rounds 1 to 3 (BASE.txt is byte-identical to round 3's BASE and to origin/main's skill at the branch point). The generator sees the arm text as its system prompt and prompts/gen_task.txt plus the scenario as the user turn (unchanged from round 3).
- BASE ("v0"): the unedited skill.
- PLAIN: "You are a helpful assistant." Descriptive control for what the skill costs or adds against no skill; never selectable.
- C1: round 3's smallest edit, reference only (descriptive; never selectable).
- S (shared prefix of A, B, C): C1 plus the round-3 C4 fixes (no sign-off placeholder, a stated recommendation with a next step, derived lean with its basis). Built by mk_arms.py; not an arm.
- A (shape lever): S plus a labelled decision-brief skeleton (Where it stands / Options with cost, time, risk / Not known / Recommendation / Ask), a PR template with Changes / Testing / Open question and no forced Why or Risk lines, "length follows the decision" in place of the 150-word default, budgets raised in the lint table (status 250/24, pr 300/40, decision 350/36).
- B (invariant lever): S plus one rule, "every fact that changes a decision survives" (list the source's numbers, dates, options with cost, time and risk, unknowns; each is present), with the 150-word default removed, a longer-report cut that keeps every option, and the same raised budgets. No new template.
- C (exemplar lever): S plus three full-length worked examples (status email, PR body, executive summary), "match the worked examples" in place of the 150-word default, and the same raised budgets.
- RIVAL: humanizer v3.1.0 (MIT, license in LICENSE.rival.txt), identical to rounds 1 to 3; its answer is generated once per scenario and shared by every comparison.
A, B and C share S and the budgets and differ only in the lever; all three keep the "add nothing the source lacks" rule for numbers, dates, owners and promises.

## Generator, judges, scoring

Generator for every arm: Qwen3.5-397B-A17B, temperature 0.7, max_tokens 3000, thinking off. It never judges. Judges, all different vendors from the generator: GLM-5.1, GLM-5.2 (both non-thinking), gpt-oss_120b; prompts/judge.txt unchanged from round 3 (rubric-free, blind), temperature 0, both orders. Per judge a scenario scores 1 only if both orders pick the arm, 0 only if both pick RIVAL, 0.5 for a split or any tie. Majority across the three judges: 1 if at least two judges give 1, 0 if at least two give 0, else 0.5. CI: bootstrap over scenarios, 10,000 resamples, seed 1, percentile. Scenario and seed writer: DeepSeek-V4-Flash (neither generator nor judge); GLM-5.1 judges this round, so it does not write scenarios.

## Scenarios

Tune: 10 fresh (4 notes, 3 diff, 3 report). Held-out: 40 fresh (16, 12, 12), disjoint from tune and from every scenario file of earlier rounds: seeds were written with all earlier seeds listed as topics to avoid, and `bench.py overlap` prints each scenario's maximum word-trigram Jaccard against every earlier scenario and against this round's tune set (output committed). A batch with any scenario above 0.15 is regenerated once before any arm is generated.

## Procedure and selection rule

1. Tune (SPLIT=tune): generate BASE, PLAIN, C1, A, B, C, RIVAL; judge BASE, PLAIN, C1, A, B, C against RIVAL. Select the one of A, B, C with the highest tune majority win rate; ties go to the smaller prompt file. The selection is made even if no candidate beats BASE on tune. Nothing is tuned further: the prompts above are final.
2. Freeze (SHA256-selected.txt): record the selection, its tune numbers and the hashes of every file, before any held-out scenario is written.
3. Held-out (SPLIT=held): write 40 scenarios, generate BASE, the selected candidate and RIVAL once, judge once. No re-runs, no arm edits, no scenario edits, no multiple-comparison correction. A missing verdict is retried until cached; the keep rule needs all 40 scenarios scored.

## Keep rule

KEEP the selected candidate as a SKILL.md and template edit only if, on the 40 held-out scenarios, its majority win rate against RIVAL has a bootstrap 95% CI lower bound above 0.5 AND its point estimate is at least BASE's majority win rate against RIVAL on the same set. Otherwise revert and ship only this directory. If KEEP: the edit lands as the selected arm's replacement strings applied to the real files (the arm text is the file text), with the lint table, evals and tests updated so every repo gate passes.

## Caveats (state with any outcome)

Non-Claude generator and judges; both skills were written against Claude, so a pass or fail here does not transfer to Claude. n=40, one scenario set, sampling not seeded, no lint-and-rewrite loop and no tools for either arm. The structural diagnosis was built from earlier verdicts by the same judge families (not GLM-5.1, which is new); the DIAGNOSIS.md keyword clusters are approximate. Judges favor the first slot (earlier rounds 0.58 to 0.68 for some models); both-order scoring cancels this. Candidates are chosen on 10 scenarios, so the selection is noisy.

## Amendments

Only driver fixes (batching, timeouts, token limits) are allowed after the freeze, each logged here with its hash; none may change an arm, a scenario, a judge prompt or a rule.
