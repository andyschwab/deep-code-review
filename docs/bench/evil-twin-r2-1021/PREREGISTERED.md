# Pre-registration: evil-twin bench R2 (frozen before any scored model call)

Question: does the `idea-critic` skill (the evil twin) catch a planted fatal flaw in a proposal more often than no skill, and more often than a generic brainstorm prompt, without killing sound proposals that only need revision?

Why R2 exists: R1 (`docs/bench/evil-twin-r1-1021`) was INCONCLUSIVE because the no-skill arm caught 24 of 24 flaws (no headroom). R1 also had a judge defect: its `KILLED` flag counted a "revise / do not approve yet" answer (case p15) as a kill, which broke the R1 false-kill guard (perun 2/6 against none 0/6 plus one case). R2 fixes both: harder flaws, calibrated before the freeze, and a precise kill definition.

## Frozen inputs
`SHA256-frozen.txt` lists the R2 driver `scripts/evil_twin_bench_r2.py`, the R1 driver it imports (`scripts/evil_twin_bench.py`), the shared PCSS client `scripts/rival_eval.py`, the R2 corpus `cases.txt` (cases plus hidden answer keys), the arm snapshots `skill-arm.txt` and `brainstorm-arm.txt` from the R1 directory (byte-identical to R1; the skill snapshot is a copy of `.claude/skills/idea-critic/SKILL.md` at the base commit) and this file. The first line of `ledger.jsonl` is the hash of that list, written in a commit that carries no results. The skill text is not edited by this bench in any case.

## Calibration (done before the freeze, discarded, never scored in R2)
A separate 8-case set (`calibration/cases.txt`, ids k01-k08, all flawed) was tuned until the no-skill arm, run through the same generator, judge and prompts, scored at most 0.70 recall. Every iteration is archived (`calibration/cases-iter1.txt` to `cases-iter7.txt`; iteration 7 is the final `cases.txt`), and the generations and judge outputs of the final iteration are in `calibration/cache/`.

| Iteration | What changed | No-skill recall |
|---|---|---|
| 1 | arithmetic and inference flaws | 1.000 |
| 2 | more buried flaws | 0.875 |
| 3 to 5 | concept-level flaws (cannibalization, leakage, attribution, interference, cost-avoidance baseline) | 0.750 |
| 6 | added a "risk register" of plausible distractors to six cases | 0.750 |
| 7 | replaced three caught cases with selective labels, right-censoring and queueing flaws | 0.625 (5/8) |

Calibration used the same generator as the bench, so it selects flaw classes this generator misses; the result generalizes to this model only. The R2 corpus cases are written fresh and share no text with the calibration set (a test checks this).

## Hypothesis
The skill text raises flaw recall over no skill (and over the brainstorm prompt) without extra false kills.

## Corpus
36 fictional proposals (Acme-style names, invented numbers, no real parties): 24 flawed cases (f01-f24), each hiding one fatal flaw that needs a two-step inference, buried among 2 to 3 minor distractor issues (and, in some, a "risk register" of individually mitigated issues); 12 sound controls (c01-c12), each with 1 to 2 minor fixable issues, whose intended outcome is "proceed with changes", never abandon. Written before the freeze; no corpus case was run against any arm first.

## Arms
Same system prefix and same user prompt for all; only the guidance block differs: `none`; `perun` (skill text appended as "Follow this guidance"); `brainstorm` (a generic prompt written for R1, no third-party text). Generator `Qwen3.5-397B-A17B` on the free PCSS endpoint, non-thinking, temperature 0, one generation per case and arm, max 2,500 tokens. Judge `GLM-5.1`, a different model, non-thinking, temperature 0, sees the proposal, the hidden key and one response, never the arm name. No paid call, public fictional data only.

## Metric (defined exactly in `judge_prompt()` of the driver)
- `FLAW_CAUGHT` = 1 only if the response identifies the keyed flaw (same underlying problem, reached by the same inference) and treats it as something that must be fixed or resolved before proceeding. Always 0 on controls. Recall = mean over the 24 flawed cases.
- `KILLED` = 1 only if the final recommendation is to abandon, reject or cancel the proposal (drop the idea, do not do it at all, or revising it is not worthwhile). 0 for proceed, proceed with changes, conditional approval, "fix X and resubmit", "hold until Y is resolved", "do not approve yet", "revise" and requests for more information. Revision is not a kill. False-kill = mean `KILLED` over the 12 controls.
- `BLOCKED` = 1 if the response does not approve as written. Descriptive only (not in the keep rule).
- Unparsed judge output counts as 0 and is tallied. Percentile bootstrap, 10,000 resamples, seed 1, cases resampled within the flawed and control strata; contrasts are paired.

## Verdict (`verdict()` in the driver, evaluated once)
1. INVALID if any arm has more than 2 unparsed judge outputs.
2. INCONCLUSIVE if the no-skill recall is 0.85 or higher (headroom ceiling).
3. Keep rule: the lower bound of the `perun` recall 95% CI is above the `none` recall point estimate AND `perun` false-kill is at most `none` false-kill plus 1/12 (one control).
4. WIN if the keep rule holds and the paired `perun - brainstorm` recall CI lower bound is above 0; TIE if the keep rule holds only; REVERT otherwise.
If the skill shows false kills they are reported, not fixed.

## Known limits (declared up front)
n = 24 flawed and 12 controls, so the false-kill interval is wide and the guard is coarse (one control is 0.083). One generator, one judge, one generation per cell. The skill's `references/` files are not available to the model. The judge sees response style, so it is not fully blind to the arm in practice. Flaws were planted by the same side that wrote the skill and were calibrated against the no-skill arm of this generator. The perun-versus-brainstorm contrast is secondary. Results describe this corpus, not proposals in general.
