# Preregistration: communication-structure round 3 against humanizer, free PCSS models only (2026-10-17)

Written and hashed (SHA256-frozen.txt) before any scenario was written and before any generation or judge call of round 3. No Claude call is made; every call goes to the PCSS endpoint at no cost (ledger.jsonl records each call's token usage).

## Why

Round 2 (../comms-round2-1017) failed its bar: 0.438 [0.312, 0.562] against humanizer v3.1.0 on 40 held-out scenarios (unedited skill 0.312). By type, the email-form edit lifted status notes from 0.094 to 0.406 but PR bodies and executive summaries stayed at 0.458. Reading the judge reasons of every round-2 verdict that picked the rival (196 verdicts on PERUN and BASE arms, DeepSeek-V4-Flash and GLM-5.2, tune and held) gives these concrete behaviors the rival has and our arms lack:

- Status notes and replies to a named person: a send-ready email with a subject line and greeting, connected prose (done in round 2); and a body that ends at the ask with nothing after it. Our arm appended meta notes ("Derived lean not included per your 'no invented facts' rule", "Note: You mentioned...") and leaked skill vocabulary; judges called these awkward and said they "would need to be edited out before sending". The round-2 edit itself told the model to add a note line about a derived lean.
- PR bodies: a plain title sentence, neutral Changes and Testing sections, and an "Open questions for <reviewer>" section; no sections the source does not support. Our `pr` template forces `Why` and `Risk and rollback` lines, which the model fills by inference ("adds unverified details", "unrequested commentary (rollback, blast radius)", "hallucinated references to unspecified communication rules"), and puts the ask in a bold title ("awkward title formatting").
- Executive summaries: every option in a sentence or two with its cost, time and risk, under short labelled sections (the rival's The Plan, Financial Impact, Key Risks, Decision Needed). Ours cut to three findings and a 200-word target ("omits key details", "condensed summary"), and its lean was sometimes called unjustified.

## Arms (prompts/*.txt; SHA256-frozen.txt)

Every arm is SKILL.md plus references/artifact-templates.md joined as in round 2.
- BASE: origin/main skill as of the branch point (identical to round 2 BASE).
- C0: the round-2 edit (frozen V4 of round 2); reference only, not a candidate.
- C1 (smallest): C0 minus the instruction to add a note line about a derived lean, plus a rule that the artifact is the whole answer (nothing after the ask or sign-off), and the decision-template sentence aligned with the lean rule.
- C2: C1 plus a `pr` template without forced Why / Risk and rollback lines (only when the source states them), a plain title with no ask, Testing and Open questions sections.
- C3: C2 plus a `decision` template that keeps each option's cost, time and risk, allows short labelled sections, and raises the decision budget from 200 to 300 words and 22 to 32 lines.
- RIVAL: humanizer v3.1.0 (MIT), as in rounds 1 and 2.
mk_arms.py builds C1 to C3 from C0 by exact replacement.

## Generator, judges, scoring

Generator for every arm: Qwen3.5-397B-A17B, temperature 0.7, max_tokens 3000, thinking off, identical task wrapper (prompts/gen_task.txt). The RIVAL answer is generated once per scenario and shared by every comparison. The generator is never a judge; the scenario writer (GLM-5.1) is neither generator nor judge.

Judges, all different vendors from the generator: DeepSeek-V4-Flash, GLM-5.2 (non-thinking mode, chosen because thinking mode timed out on one verdict in round 2), gpt-oss_120b. Rubric-free blind prompt (prompts/judge.txt, unchanged), temperature 0, both orders per pair. Per judge a scenario scores 1 only if both orders pick the arm, 0 only if both pick RIVAL, 0.5 for a split or any tie (strict agreement). Across judges the scenario score is the majority: 1 if at least 2 of 3 judges score 1, 0 if at least 2 score 0, else 0.5. A scenario with any missing verdict is re-judged until all verdicts exist; no scenario is dropped. Per-judge win rates and each judge's slot-1 rate are reported descriptively.

## Scenarios

Seeds prompts/tune_seeds.txt (10: 4 notes, 3 diff, 3 report) and prompts/held_seeds.txt (40: 16 notes, 12 diff, 12 report), written by GLM-5.1 from the writer brief of rounds 1 and 2. Topics were chosen to differ from every earlier scenario set; `bench.py overlap` prints each new scenario's maximum word-trigram Jaccard against every earlier scenarios*.json under docs/bench and the output is committed. Used unedited, none dropped.

## Procedure and selection rule

1. Tune (n=10, fresh, SPLIT=tune): generate BASE, C1, C2, C3, RIVAL; judge as above. The candidate with the highest tune majority win rate against RIVAL is selected (ties: the smaller edit, i.e. the lower number). The selection is made even if no candidate beats BASE on tune.
2. Held-out (n=40, fresh, SPLIT=held): generate BASE, the selected candidate and RIVAL once; judge once. No re-runs, no arm edits, no scenario edits after this freeze, no multiple-comparison correction.

## Keep rule

KEEP the selected candidate as a SKILL.md and template edit only if, on the 40 held-out scenarios, the candidate's majority win rate against RIVAL has a bootstrap 95% CI (10,000 resamples over scenarios, seed 1, percentile) with a lower bound above 0.5 AND its point estimate is at least BASE's majority win rate against RIVAL on the same set, with all 40 scenarios scored. Otherwise revert and ship the bench only.

## Caveats (state with any outcome)

Non-Claude generator and judges; both skills were written against Claude, so a pass or fail here does not transfer to Claude. n=40, one scenario set, sampling not seeded, no lint-and-rewrite loop. The candidates were derived from reading round-2 verdicts on a different scenario set, but the same judge families will score them. Judges favor the first slot (round 2: DeepSeek 0.675); both-order scoring cancels this for the win rate.

## Amendment 1 (written after the tune run of C1 to C3, before any held-out scenario was written or any held-out call)

Tune result for C1 to C3 (majority win rate vs RIVAL, n=10): BASE 0.20, C1 0.30, C2 0.35, C3 0.25 (tune_report.txt; all within noise). Reading C2's tune verdicts where the rival won showed two more concrete rival behaviors: it states a clear recommendation and next step where ours still leaves the decision open, and it has no sign-off placeholder (judges: "placeholder note", "[Your name]" needing an edit; "meta-commentary about derived figures"). One more candidate is added, built on C2 (not C3, whose longer decision template did not help on tune):
- C4: C2 plus an email that ends at the ask with no `[Your name]` placeholder; a decision message recommends the option the source's facts favor ("I recommend X: <those facts>", then a next step), the author's own lean keeping its stated strength; "flagged as derived" removed from the templates reference. Built by mk_arms.py (C1 to C3 are byte-identical to the frozen hashes).
The selection rule is unchanged and now runs over C1 to C4 on tune (C4 is tuned on the same 10 scenarios; four candidates were compared on 10 scenarios, so the selection is noisy and is not evidence for the keep rule). SHA256-frozen.txt is regenerated with this amendment; the earlier hash of this file is in SHA256-first.txt.
