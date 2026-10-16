# Addendum 1 (written after the set A primary run, before any further call)

Set A primary result (rubric judge, `results-A-PERUN_BASE-vs-RIVAL.json`): Perun won all 10 scenarios in both orders, 1.000 [1.000, 1.000], PASS. Reading the outputs showed two weaknesses in that result, both preregistered as caveats but now tested:

1. The rubric in `prompts/judge.txt` mirrors Perun's own checklist (harm inventory, per-harm test row, human gate, UNVERIFIED, route legal to counsel). A judge told to reward those will favor the skill that teaches them.
2. The rival skill is a red-team config skill; on these planning requests it behaved as a generic safety-plan writer, so the pair is partly a scope mismatch.

Added before running: a rubric-free holistic judge (`prompts/judge_neutral.txt`, same model, blind, both orders, verdict only, run with `JV=neutral`) over the same set A outputs. Same win-rate definition and bootstrap. It is reported next to the primary result.

Decision rule (frozen now): the claim "Perun is superior to the rival on product-output-safety held-out scenarios" is made only if BOTH judges give a CI lower bound above 0.5. If the neutral judge does not, the protocol steps 2 to 4 of `PREREGISTERED.md` run (diagnose from the losses, generic SKILL.md edit with an eval, fresh set B) and both judges are applied to set B. If both pass, no skill change and no set B are made.
