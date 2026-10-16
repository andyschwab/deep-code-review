# Addendum 2 (written after the set A neutral-judge result, before set B is generated)

Set A, rubric-free judge (`results_neutral-A-PERUN_BASE-vs-RIVAL.json`): Perun 0.150 [0.000, 0.400], FAIL; the rival was preferred in 9 of 10 scenarios (one order split). Under the Addendum 1 decision rule the superiority claim is not made, and protocol steps 2 to 4 run.

## Diagnosis (from the neutral judge's stated reasons on set A, read before editing)

Perun lost mostly on fit and implementation, not on safety content. Recurring reasons across the 9 losses:

1. Plans were frameworks, not sequenced against the stated deadline, team size and scarce expert hours.
2. No shadow mode, staged rollout, kill switch or post-launch monitoring.
3. Limits were not placed in the service the model calls; no fixture-account probing.
4. Legal handling deferred to counsel without naming the regime families or what to bring; counsel review was scheduled last.
5. Missed data-honesty points: selection-biased ground truth, and a zero-failure threshold with no bound on what zero observed failures proves.

The one win (set A scenario 09) was a safety win on suitability claims. Edits were made to the SKILL.md generically (three added rules plus one eval, `plan-fits-team-ships-staged-routes-legal-by-family`, which uses a housing-screening case that is not in set A or set B). The edited file is frozen as `prompts/perun_postfix.txt` (sha256 2aec52e37bde7005b88feceadd6c6e14b42cd64947671cde08d0fbf005eddd72, equal to the repo SKILL.md).

## Set B plan

- Generate set B from `prompts/seeds_B.txt` with the same writer brief. Run PERUN_FIX vs RIVAL, both judges (rubric judge primary, neutral judge co-primary). Headline claim requires both lower bounds above 0.5.
- Cost control: PERUN_FIX vs RIVAL on set B is run first. Only if spend stays under the cap afterward, run PERUN_BASE vs RIVAL on set B with the neutral judge only, as a control for scenario difficulty. The cap guard in `pos.py` stops any run that would cross $7.00.
- The skill is not edited again after set B is seen. A result that fails is reported as failing.
