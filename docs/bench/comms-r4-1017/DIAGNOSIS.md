# Why communication-structure loses to humanizer: diagnosis (2026-10-17)

Reproduce every number with `python3 diagnose.py` (output in diagnosis_output.txt). Source: every per-verdict judge reason and generated answer in ../comms-round2-1017, ../comms-round3-1017 and ../loss-fix-1017 (communication-structure half), 1,334 verdicts in total; the rival won 963 (72%). Rubric-free blind judges: DeepSeek-V4-Flash, GLM-5.2, gpt-oss_120b. The earlier rounds ../comms-quality-1016 and ../comms-rubricfree-1016 used a Claude judge on n=10 and are not in the counts.

## Result history (rival = humanizer v3.1.0; win rate of our arm, both orders strict)

| Round | Edit | Edited | Unedited (v0) |
|---|---|---|---|
| round 2 (DeepSeek, n=40) | email form + derived lean | 0.438 [0.312, 0.562] | 0.312 |
| loss-fix re-test (DeepSeek, n=20) | same edit | 0.175 [0.075, 0.275] | 0.150 |
| round 3 (3-judge majority, n=40) | no trailing notes, PR template | 0.325 [0.225, 0.438] | 0.212 [0.125, 0.300] |

Every edit was a wording or template change to the same text. Each moved the score by about +0.10 to +0.12 with overlapping intervals and none reached 0.5.

## Reason clusters (rival-win reasons vs ours-win reasons; keyword regexes in diagnose.py, approximate)

- Completeness or a stated recommendation appears in 64% of rival-win reasons (completeness 34%, recommendation or next step 44%). Typical: "includes key metrics and financial impact", "gives Priya a direct recommendation with specific reasoning", "Response 2 only presents options and unknowns without guidance", "omits key details".
- Ready-to-send form (placeholders, sign-off, subject line, "needs edits") 39%; meta-notes, emoji, clutter 24% (3% of ours-win reasons). These are the surface problems rounds 2 and 3 fixed; they explain the small gains.
- Fabrication or unsupported additions by our arm: 5%. Conciseness is cited in 23% of rival-win reasons and 42% of ours-win reasons, so judges do reward concision when content is equal; it is not what separates the arms.

## The structural cause: output shape, not wording

The skill's output contract is a compressed digest: line 1 in 30 words, "~150 words by default", "core value only", "no recommendation or rationale the author did not give", executive summaries "cut to three findings". The rival (humanizer is a tone skill, so the generator keeps its natural completeness) writes a complete decision brief: situation, constraints, every option with its pros, cons, cost and time, a recommendation, a concrete next step, the ask. Blind judges asked "which would you rather receive" prefer the brief. Evidence:

1. Length relative to the rival predicts the loss. Per scenario, corr(our words / rival words, rival share of the six verdicts) = -0.39 (BASE, round 2), -0.43 (round-2 edit), -0.65 (BASE, round 3), -0.67 (round-3 edit) on the 40-scenario held-out sets. When our answer is under 0.9x the rival's, the rival takes 0.74 to 0.89 of verdicts (BASE), 0.81 to 0.85 (edits); at 0.9x or longer it still takes 0.54 to 0.64, so length is not the whole cause. Unedited answers average 0.80 to 0.85x the rival's length. The round-2 README said length was not the cause because it compared the totals on the tune split (4,513 vs 4,618 words), which hides the per-scenario ratio; the edits raised the ratio to about 1.0 and that is where their gain came from.
2. The shortfall is content, not words. At parity length the edited arm still lost (0.54 to 0.60) because the rival more often states a lean plus next step (regex match in 17 of its 40 round-3 held-out answers; its share of verdicts is 0.76 on those scenarios vs 0.57 on the rest, in diagnose.py) and keeps content the digest drops and our template forces fields the source lacks (a forced Why / Risk line was filled by inference; the round-3 PR template then scored below the unedited skill on PR bodies, 0.333 vs 0.458).
3. By type (round 3, C2 vs BASE): status notes 0.312 vs 0.062, PR bodies 0.333 vs 0.458, executive summaries 0.333 vs 0.167. Notes gained from the email form; the other two kinds, whose rival answers are the most complete briefs, did not.
4. Unconstrained models write the brief by default. The only rule in the skill that pushes against it is the budget and the no-recommendation clause; both are measurable in the verdicts as "condensed", "omits key details", "no guidance".

## What this implies for candidates

Wording edits cannot fix a mismatch between contract and reader. Three structurally different levers, each addressing "complete decision brief with a stated, source-backed recommendation" while keeping the integrity rule (no invented numbers, dates, owners):
- A: change the output skeleton (labelled brief with per-option cost, time and risk).
- B: replace the length goal with a coverage invariant (every fact that changes a decision survives), no template change.
- C: replace rule text with full-length worked examples per artifact kind (the generator copies exemplars more reliably than it follows length rules).
Preregistered in PREREGISTERED.md; nothing in the diagnosis is a causal proof (the data are observational reasons from judges; the held-out test is the experiment).

## Limits

Keyword clusters are regex-based and overlap; the correlation is across 40 scenarios per arm and mixes judge families; both skills were written for Claude and the generator and judges are not Claude.
