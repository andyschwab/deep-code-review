# Evil-twin bench R2 (2026-10-21, preregistered, free): REVERT (skill not shown to beat no skill on this corpus)

Bottom line: the preregistered verdict is REVERT. With a calibrated, harder corpus the no-skill arm caught 20 of 24 planted flaws (0.833, below the 0.85 headroom ceiling, so the run counts). The idea-critic skill caught 21 of 24 (0.875), but its lower confidence bound (0.750) is not above the no-skill point estimate (0.833), so the preregistered keep rule fails on its primary test. The generic pros-and-cons prompt also caught 21 of 24. No arm killed any of the 12 sound controls (false-kill 0/12 in every arm), so the false-kill guard held. Read this as "no measurable recall benefit on 24 flawed cases", not as proof that the skill does nothing: the interval around the +0.042 gain is [0.000, +0.125].

Judge caveat on R1 (`docs/bench/evil-twin-r1-1021`): R1's reported perun false-kill of 2/6 is a judging-rule artifact, not a measured kill rate; R1's cases were not re-judged under the R2 rubric, so no corrected R1 rate exists. R1 is a pilot, not a preregistration (see its README). The R1 judge scored a "revise / do not approve yet" answer as KILLED, so case p15 (and p25), where the skill said REVISE, counted as kills, and that broke R1's false-kill guard (perun 2/6 against none 0/6 plus one case). R1 is also INCONCLUSIVE for lack of headroom (no skill caught 24/24). R2 defines KILLED precisely (abandon, reject or cancel only; "revise", "hold" and "do not approve yet" are not kills) in `judge_prompt()` before the freeze, and R2 reports whether the answer blocked approval separately.

Question, rules and limits are frozen in `PREREGISTERED.md` (hash list `SHA256-frozen.txt`, which includes `scripts/rival_eval.py`; ledger line 1 was committed before results (alongside R1), in an earlier commit than this one).

## Setup
- Calibration first: an 8-case set, discarded and never scored here (`calibration/`, 7 archived iterations), tuned until the no-skill arm scored 0.625 (5/8, at most the 0.70 target).
- Corpus (`cases.txt`): 36 fictional Acme-style proposals. 24 hide one fatal flaw that needs a two-step inference, buried among 2 to 3 minor distractor issues; 12 are sound controls with 1 to 2 minor fixable issues.
- Arms: `none`; `perun` (the `idea-critic` SKILL.md as guidance, the R1 snapshot); `brainstorm` (generic "list pros and cons, then recommend", the R1 wording).
- Generator `Qwen3.5-397B-A17B`, judge `GLM-5.1` (a different model, blind to the arm name), both on the free PCSS endpoint at temperature 0; one generation per cell. No paid call.
- Recall = flaw caught over the 24 flawed cases. False-kill = recommendation to abandon or reject over the 12 controls. 95% percentile bootstrap, 10,000 resamples, seed 1.

## Results
| Arm | Recall (24 flawed) | 95% CI | False-kill (12 controls) | 95% CI | Not approved as written (controls) | Killed a flawed case |
|---|---|---|---|---|---|---|
| none | 20/24 = 0.833 | 0.667 to 0.958 | 0/12 = 0.000 | 0.000 to 0.000 | 12/12 | 6/24 |
| perun (idea-critic) | 21/24 = 0.875 | 0.750 to 1.000 | 0/12 = 0.000 | 0.000 to 0.000 | 12/12 | 6/24 |
| brainstorm | 21/24 = 0.875 | 0.750 to 1.000 | 0/12 = 0.000 | 0.000 to 0.000 | 12/12 | 15/24 |

Paired recall differences: perun minus none +0.042 [0.000, +0.125]; perun minus brainstorm +0.000 [0.000, 0.000]; brainstorm minus none +0.042 [0.000, +0.125]. Unparsed judge outputs: 0 in every arm. Keep rule: perun recall lower bound 0.750 is not above none 0.833 (fails); perun false-kill 0 is at most none 0 plus 1/12 (holds). Per-case scores: `per-case-scores.tsv`; raw rows and the verdict: `results.json`; every generation and judge output: `cache/`.

## What the numbers do and do not say
- Misses: `f02` (regression to the mean), `f13` (failover tooling hosted in the failing region) and `f16` (synchronized cache expiry) were missed by all three arms; `f23` (load test replays one session) was missed by the no-skill arm only, and both other arms caught it. So the whole perun gain is one case. The judge reasons for these four read as consistent with the keys (checked; the other judge outputs were not read).
- Calibration did not transfer fully: the calibration set was tuned against this generator and scored 0.625, while the scored corpus landed at 0.833. A set tuned against the same generator on 8 cases likely overstates difficulty (selection on misses), so the headroom is real but smaller than the calibration target.
- No false kills: every arm asked for revisions on all 12 controls ("not approved as written" 12/12) and none recommended abandoning one. R1's perun false kills were scored under the old judging rule and were not re-judged under the R2 rubric, as stated above.
- The brainstorm arm killed far more flawed proposals (15/24) than the other two (6/24) while catching the same number of flaws; recall and kill rate are scored separately.

## Not covered
Several samples per cell, a second judge, a weaker or stronger generator, the skill's `references/` files (not loaded into the prompt), and flaw classes outside this corpus. Flaws were planted by the same side that wrote the skill. The skill text was not edited and the result is reported as is.

## Reproduce
Offline: `python3 scripts/test_evil_twin_bench_r2.py` replays the committed cache and must reproduce `results.json`. Live: `PCSS_ENV_FILE=<env file with PCSS_KEY> python3 scripts/evil_twin_bench_r2.py --write` (free tier; the key is read from the environment or the file and never printed).

## R1 amendment
The R1 corpus held three real-looking third-party names. They were replaced by fictional placeholders (text only), the R1 cache was rekeyed to the new text with no model re-run (the R1 model responses saw the old names), and the R1 `results.json` is unchanged; the change is recorded as an amendment line in R1's `SHA256-frozen.txt` and ledger.
