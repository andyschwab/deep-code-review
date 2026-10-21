# Evil-twin bench R1 (2026-10-21, pilot, not preregistered, free): INCONCLUSIVE (no headroom)

Disclosure, read first. (a) R1 is a pilot and is NOT preregistered: its freeze list and its results landed in the same commit, and `scripts/rival_eval.py` is not in the frozen list. The rules in `PREREGISTERED.md` were written before the model calls, but nothing in git proves that order, so treat them as a declared plan, not a verified preregistration. (b) The `cases.txt` proposal names were amended after the results: three real-looking third-party company names were replaced by fictional placeholders. The first `cases.txt` line in `SHA256-frozen.txt` (line 2) holds the pre-amendment hash and no longer matches the file; line 6 re-lists the amended hash and `bench_check` follows the last-listed line, so the check passes by amendment, not because the original hash still holds. The cache was rekeyed to the new text, but the model responses were generated from the old names and never regenerated. R2 (`docs/bench/evil-twin-r2-1021`) is the preregistered round.

Bottom line: the verdict is INCONCLUSIVE. With no skill at all, the generator already caught the planted flaw in 24 of 24 proposals, above the declared 0.90 headroom ceiling, so this corpus cannot show that the idea-critic skill adds recall. No claim that the skill helps, or that it does not, follows from this run. Judge caveat: the reported perun false-kill of 2/6 is a scoring artifact, not a measured kill rate. The R1 judge counted a "revise / do not approve yet" answer as KILLED, so p15 (and p25), where the skill said REVISE, were scored as kills; that broke the false-kill guard (perun 2/6 against none 0/6 plus one case). R2 (`docs/bench/evil-twin-r2-1021`) defines KILLED as abandon or reject only.

Question, rules and limits are declared in `PREREGISTERED.md` (hash list `SHA256-frozen.txt`; the file name is historical, see the disclosure above).

## Setup
- 30 fictional proposals (`cases.txt`): 24 with one planted fatal flaw and a hidden answer key, 6 sound controls.
- Arms: `none`; `perun` (the `idea-critic` SKILL.md as guidance, `skill-arm.txt`); `brainstorm` (generic "list pros and cons, then recommend", `brainstorm-arm.txt`, own wording).
- Generator `Qwen3.5-397B-A17B`, judge `GLM-5.1` (a different model, blind to the arm name), both on the free PCSS endpoint at temperature 0; one generation per cell. No paid call.
- Recall = flaw caught over the 24 flawed cases. False-kill = control rejected or held over the 6 controls. 95% percentile bootstrap, 10,000 resamples, seed 1.

## Results
| Arm | Recall (24 flawed) | 95% CI | False-kill (6 controls) | 95% CI | Rejected a flawed case |
|---|---|---|---|---|---|
| none | 24/24 = 1.000 | 1.000 to 1.000 | 0/6 = 0.000 | 0.000 to 0.000 | 24/24 |
| perun (idea-critic) | 24/24 = 1.000 | 1.000 to 1.000 | 2/6 = 0.333 | 0.000 to 0.667 | 24/24 |
| brainstorm | 23/24 = 0.958 | 0.875 to 1.000 | 0/6 = 0.000 | 0.000 to 0.000 | 20/24 |

Paired recall differences: perun minus none +0.000 [0.000, 0.000]; perun minus brainstorm +0.042 [0.000, +0.125]; brainstorm minus none -0.042 [-0.125, 0.000]. Unparsed judge outputs: 0 in every arm. Per-case scores: `per-case-scores.tsv`; raw rows and the verdict: `results.json`; every generation and judge output: `cache/`.

## What the numbers do and do not say
- Ceiling: every planted flaw is stated in the proposal text, and an unprompted 397B-parameter model finds almost all of them. The corpus is too easy for this generator. The only miss in any arm is `p02` (brainstorm), where the model saw the 7-day-window problem but recommended going ahead with changes.
- Perun false kills are `p15` (canary release) and `p25` (fix-it window). In both the response said the idea was sound in outline but answered "do not approve yet, revise", and the judge counted a send-back as a kill. That is the skill's `REVISE` verdict read as a rejection, so the false-kill count depends on that judging rule (declared in `judge_prompt()`); with 6 controls it is 2 events.
- The brainstorm arm sent back fewer flawed proposals (20/24) than the other two but caught the flaw in nearly all of them; recall and rejection differ because the judge scores them separately.

## Not covered
Subtle or buried flaws, a weaker generator (where the no-skill arm would have headroom), several samples per cell, a second judge, and the skill's `references/` files (not loaded into the prompt). Spot-check of four judge outputs (p15 and p25 perun, p23 none, p02 brainstorm) read as consistent with the key; the other 86 were not read.

## Next
A round 2 needs a corpus with subtler flaws or a smaller generator so the no-skill arm sits below 0.90, preregistered in an earlier commit than its results and with a fresh corpus (this one is now a development set). Reproduce this run offline: `python3 scripts/evil_twin_bench.py --cache-only` (test: `scripts/test_evil_twin_bench.py`); a live rerun needs `PCSS_KEY`.
