# Rows closed on 2026-10-17: contribution, product-output-safety, mutation filter

Bottom line: product-output-safety passes against a like-for-like rival; contribution still loses and stays a loss
(the one allowed fix was tested on a fresh set, did worse, and was reverted); the mutation filter meets both
preregistered bars on the existing held-out set, but it was tuned on that set, so the result is in-sample.

## Design

`PREREGISTERED.md` (frozen first; hashes in `SHA256-frozen.txt`) holds the question, rivals, sets and decision rule.
No paid `claude -p` calls. Generator Qwen3.5-397B-A17B; judges rubric-free and blind, both answer orders,
DeepSeek-V4-Flash with GLM-5.2 as tiebreak on scenarios where DeepSeek's two orders disagree. 20 fictional scenarios
per set, bootstrap 10,000 resamples, seed 1; PASS only if the 95% CI lower bound is above 0.5.
`bench.py ROW SET scen|run|report` reruns everything from the cached outputs.

Freeze check (`shasum -a 256 -c SHA256-frozen.txt`): the preregistration, seeds, every arm, rival and judge prompt
and the rival texts match. Four harness files differ because they were fixed after the freeze and before any scenario
or result existed in that form: `pcss.py` and `bench.py` (thinking disabled for the generator, retry on empty or
truncated replies, `### NN` scenario parsing) and the two `writer_brief.txt` files (output format changed from JSON to
`### NN` blocks after the generator ignored JSON). No judge, arm or rival text changed after the freeze.

## Results

| Row | Arm vs rival | Set | Win rate [95% CI] | Verdict |
|---|---|---|---|---|
| product-output-safety | Perun vs NIST AI RMF skill (like-for-like) | N1 | 0.950 [0.875, 1.000] | PASS |
| product-output-safety | Perun vs promptfoo red-team skill (exploratory, not in the decision) | N1 | 0.925 [0.800, 1.000] | exploratory |
| contribution | Perun vs github-contributor skill | N1 | 0.175 [0.025, 0.350] | FAIL |
| contribution | Perun with one edit (PERUN_FIX) vs same rival | N2 | 0.275 [0.125, 0.450] | FAIL |
| contribution | frozen Perun vs same rival | N2 | 0.425 [0.225, 0.625] | FAIL |

Rule for the edit: keep only if PERUN_FIX has CI lower bound above 0.5 on N2 and beats frozen Perun on N2. It did
neither (0.275 against 0.425), so the edit to `.claude/skills/contribution/SKILL.md` was reverted. No second round.

Contribution diagnosis (N1 judge reasons): the skill over-applies its skillset-lesson privacy gate and refuses or
reframes ordinary upstream requests. The edit told it to do the work and keep only the privacy and evidence rules.
On N2 it still defers facts to the maintainers and leaves drafts unfinished, and it did worse than before. Caveat,
stated in the preregistration: the skill is scoped to the skillset's own lessons, and the rival is a generic
upstream-PR playbook, so generic upstream scenarios favour the rival. The skill's scope, not just its wording, is the
likely gap; that is an owner decision (widen the skill, or keep the row as a scoped loss).

## Mutation filter (`mutation_changed.py`, `equivalent()`)

Held-out set: 20 vacuous and 20 genuine Python tests (`bench-local/mutation/heldout`). Re-run with the real
mutmut 3.8.0 and the new script, same cases, nothing else changed. `mutation_heldout_results_filtered.json` is the raw
output; `python3 mutation_tally.py <dir>` computes the numbers below.

| Metric | Before | After | Bar |
|---|---|---|---|
| Genuine tests with at least one equivalent mutant flagged | 7/20 | 2/20 (Bp13, Bp20) | at most 2/20 |
| Vacuous tests flagged (recall) | 18/20 | 18/20 | at least 16/20 |
| Equivalent mutants flagged as SURVIVED | 11 | 5 (6 now LIKELY_EQUIVALENT) | |
| Thin-test survivors demoted by mistake | | 0 of 55 | |
| Vacuous cases with a demoted mutant | | 0 | |

Five static rules, each with a near-miss test in `scripts/test_mutation_equivalent.py`: codec name case, falsy
stdlib flag kwarg (`last`, `reverse`, `flush`, `exist_ok`), tail-of-function `break` to `return`, a constant that is only
ever raised, strip set gaining only `X` on lowercased data. A match prints `LIKELY_EQUIVALENT`, is never counted and
never fails `--strict`.

Limits: the five rules were written after reading this set's equivalent mutants, so the 2/20 is in-sample; a fresh
set is the only fair test. The two residual cases (Bp13 DP-table padding and scaling, Bp20 a redundant modulo bound)
need value reasoning the static rules do not do. The strip rule is a heuristic (no `X` in the function, `.lower()`
present, no re-casing), so a match is a hint, not a proof, which is why it is a separate tier.
