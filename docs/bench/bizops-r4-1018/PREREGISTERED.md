# Preregistration: one business-ops SKILL.md edit against the shipped text and its rival, 150 fresh held-out scenarios (2026-10-18)

Written after the tune step and before any held-out seed, scenario or arm answer exists. Every model call goes to the PCSS endpoint ($0); no `claude -p`, no paid API, public data only. Scenarios file: scenarios-heldout.json. Hashes of every input are frozen in SHA256-frozen.txt, whose sha256 is the first line of `ledger.jsonl` (`preregistered`), written after the scenarios are frozen and before any held-out arm answer is generated.

## Background

`../bizops-sup-1018` tested the shipped text (origin/main 18801f12, `.claude/skills/business-ops/SKILL.md`, sha256 39af659d0f34751f187cd40fe5e4ee9f7325d1b314485bbcf1633da87eecf741) against the rival (marketingskills pricing, MIT, same text as before) on 200 fresh scenarios: 0.463 [0.403, 0.522], 72 wins / 41 ties / 87 losses. That set is now spent and is tune data only here.

## Tune (done before this file; records in `ledger-tune.jsonl` and `tune/`)

Loss analysis of the 87 losses (outputs only; the judge files hold verdicts, no reasons): by a keyword split, non-legal arithmetic prompts score 0.298 (62 scenarios, 36 losses) and legal or tax prompts 0.536 (138, 51 losses); the shipped answers contain a self-correction marker ("Wait", "Correction", "Re-evaluating", "Actually,") in 33 of 200 answers against 18 for the rival, and those 33 average 0.379. Read losses show: a call written before the arithmetic and contradicted by it, a stated user figure left out (a $4 shipping fee that is revenue), an invented input (a monthly burn the user never gave), and a requested figure answered with "give me your bean cost" instead of a closed form.

Three candidate snippets, each inserted into the shipped text before the line starting `Do not print "tier"` (`prompts/variants/`, built by `bench.py mkvariants`): a (work the arithmetic first, use every figure, no invented inputs, no printed self-corrections), b (answer every question in order with a labelled result; a missing input gets a closed form plus one worked example), c (legal, tax and accounting questions name the specific rule, test or threshold). Each was generated once on the 200 sup-1018 scenarios against that run's rival outputs and judged by GLM-5.1 in both orders; the shipped score is that run's. Tune result (paired difference to shipped, informational only, the data are spent):

| variant | win rate vs rival | paired vs shipped |
|---|---|---|
| shipped (sup-1018) | 0.463 [0.403, 0.522] | n/a |
| a | 0.512 [0.450, 0.575] | +0.050 [0.000, 0.100] |
| b | 0.517 [0.460, 0.578] | +0.055 [0.005, 0.107] |
| c | 0.500 [0.440, 0.560] | +0.037 [-0.010, 0.087] |

Chosen: b, the largest paired gain and the fewest losses (70). Skeptic: the three gains are close together, each tune interval is wide and the shipped score is one sample, so some of the gain may be selection; the held-out run below decides, and a, c and the unchosen combinations are not tested there. The chosen edit is `prompts/perun_business-ops_edit.txt`, byte-equal to `prompts/variants/perun_business-ops_b.txt`.

## Arms

- SHIPPED: `prompts/perun_business-ops_shipped.txt`, a byte copy of `.claude/skills/business-ops/SKILL.md` at origin/main, system prompt.
- EDIT: `prompts/perun_business-ops_edit.txt`, SHIPPED plus the one paragraph of variant b, system prompt.
- RIVAL: `prompts/rival_business-ops.txt`, byte copy of the sup-1018 rival text.
- Each arm answers every scenario once with the harness wrapper `GEN_TASK` (`scripts/rival_eval.py`), generator Qwen3.5-397B-A17B, thinking off, temperature 0.3, no tools, unseeded; no regeneration.

## Scenarios

150 scenarios, ids r4-001 to r4-150, drawn fresh by the sup-1018 procedure (one-line settings from the generator in calls of 50 with a rotating industry focus, new against every earlier business-ops seed line, written into full requests by the harness writer brief that never sees skill text). Disjointness is enforced by `bench.py check` and `python3 scripts/bench_check.py --changed origin/main` against every scenario set under `docs/bench` and `scripts/eval-fixtures`, including the spent sup-1018 set: no shared id, no identical normalized text, 6-word-shingle overlap at most 0.10 for every pair (also inside the set). A failing scenario is redrawn from the same seed (up to 12 rounds); a seed that cannot pass stops the run.

## Judging and decision rules (fixed now)

- Judge: `scripts/rival_eval.py` judge v2, GLM-5.1 only, both orders, random three-letter labels, no rubric. EDIT and SHIPPED are each judged against RIVAL (separate judge directories). A scenario scores 1 (wins both orders), 0 (loses both), else 0.5; an order with no usable verdict scores 0.5 and is reported.
- Per-scenario paired difference d = score(EDIT vs RIVAL) minus score(SHIPPED vs RIVAL), same scenario. CI: percentile bootstrap, 10,000 resamples, seed 1, over scenarios (`rival_eval.boot`).
- Ship rule: edit `SKILL.md` if and only if the 95% CI lower bound of mean d is above 0. Otherwise `SKILL.md` is not changed and only this record ships.
- Win claim: claim superiority over the rival if and only if EDIT's win-rate 95% CI lower bound against RIVAL is above 0.5 and the EDIT judge slot-1 rate is within 0.4 to 0.6. A shipped edit does not by itself imply a win claim.
- The held-out set is judged once. No second run, no extra scenarios, no change of judge, candidate or rule after the result is seen. SHIPPED's own win rate on this set is reported, never pooled with sup-1018.

## Caveats declared in advance

Open models on one cluster; system-prompt-only arms; synthetic scenarios from a single writer; generator and judge are open models on the same cluster, so shared bias is not controlled. The ship rule is a low bar (lower bound above zero) and says nothing about effect size or real-user value. The candidate was chosen on spent data with one judge sample; the tune table is selection-biased in favour of the chosen edit and is not evidence of the held-out result. The snippet asks the generator to answer every question and to give closed forms, which may lengthen answers; the harness caps answers at 600 words for both arms.
