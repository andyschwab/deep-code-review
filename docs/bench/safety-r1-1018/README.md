# product-output-safety round 1: one targeted edit, 2026-10-18

Question: does one small edit to `product-output-safety/SKILL.md`, aimed at the losses in `docs/bench/baseline-gs-1018`, beat the unedited skill, and does it beat the promptfoo redteam-setup rival? Preregistered in `PREREGISTERED.md`. The binding record is the frozen list `SHA256-frozen.txt`, whose sha256 is held by the `preregistered` event on the first line of `ledger.jsonl`; `SHA256-prereg.txt` and `SHA256-scenarios.txt` are stale (see Deviations). PCSS models only, $0, `scripts/rival_eval.py` judge protocol v2 unchanged, judge GLM-5.1, bootstrap 10,000 resamples seed 1.

Result (held-out, n=60 fresh scenarios `sr1h01`..`sr1h60`, win rate against the rival, 95% CI):

| Arm | Win rate [95% CI] | Win / tie / loss |
|---|---|---|
| V0 (unedited, origin/main) | 0.467 [0.350, 0.575] | 22 / 12 / 26 |
| EDIT (final variant) | 0.550 [0.433, 0.667] | 28 / 10 / 22 |

Paired EDIT minus V0: +0.083 [-0.017, +0.183] (15 scenarios up, 7 down). Slot-1 rate of the judge 0.456, no generation or verdict errors.

Decision: keep rule (paired lower bound above 0) fails, -0.017, so the edit does not ship and `SKILL.md` is unchanged. Superiority rule (EDIT lower bound above 0.5) fails, 0.433. The point estimates favor the edit, and V0 reproduces the baseline's 0.467, but this set cannot tell the edit from no change; the paired interval is a few scenarios away from excluding 0.

The edit (`prompts/edit.md` is the whole edited file, `prompts/v0.md` the base): a bullet in MANAGE, "Answer inside the stated constraint", treating the stated deadline, budget and goal as fixed inputs and leading with a plan that meets them. It was paid for by removing duplicated text so the file stays at 13375 bytes against a 13378 budget. Cause read from the baseline losses and from judge analyses on tune pairs: judges prefer the answer that fits the stated constraint (a phased rollout instead of "delay launch", a dated timeline, feasibility for the team) and engineering specifics, over framework vocabulary and lecture notes.

Tune (n=20 fresh, selection only, `ledger-tune.jsonl`, three variants, `prompts/edit-var1.md`, `edit-var2.md`, `edit.md`):

| Variant | Judge | V0 | EDIT | Paired EDIT minus V0 |
|---|---|---|---|---|
| 1 (lead with shippable controls) | GLM-5.1 | 0.350 | 0.325 | -0.025 [-0.150, 0.125] |
| 2 (concrete mechanisms named) | GLM-5.1 | 0.350 | 0.400 | +0.050 [-0.125, 0.250] |
| 3 (constraints as fixed inputs; final) | GLM-5.2 | 0.425 | 0.550 | +0.125 [-0.125, 0.375] |

Variant 3 was scored by GLM-5.2 because GLM-5.1's slot-1 rate on that run was 0.388, below the 0.4 band, so the tune rows are not comparable across judges. Variant 3 was chosen as the best paired mean; the held-out run happened once.

Limits: one generator family wrote the scenarios and all answers; judges are models; scenarios are fictional; the rival is a tool-driven red-team skill run without its tools; held-out n=60 gives a paired interval about 0.2 wide. A failed keep rule means "not shown to help on this synthetic distribution", not that the edit hurts.

Deviations from the preregistration, stated plainly: scenario writing and tune generation ran before the `preregistered` ledger line, as in `baseline-gs-1018`, and are outside `ledger.jsonl`; the tune directories `tune2` and `tune3` reuse the V0 and rival answers of `tune` (copied), so only the EDIT arm was regenerated there. `bench.py run` asserts that `prompts/edit.md` equals the live `SKILL.md`; because the edit did not ship, reproducing a run means first applying `prompts/edit.md` to `SKILL.md`. `SHA256-prereg.txt` and `SHA256-scenarios.txt` were written during tuning and still list `prompts/edit.md` as tune variant 1 (`233c161e…`), so `shasum -c` fails on that one entry against the committed variant 3 (every other entry verifies); they are kept as written, not as verification records. For the same reason, the line in `PREREGISTERED.md` saying it was hashed before any seed, scenario or answer was generated does not hold for those two files; `PREREGISTERED.md` is unchanged because `SHA256-frozen.txt` hashes it. Needs `PCSS_KEY` in the environment.

Files: `held/results.json` (per-scenario V0 and EDIT scores), `held/outputs/<ARM>/`, `held/<ARM>/judge/` (cached verdicts), `tune*/`, `scenarios-*.json`, `seeds.txt`, `prompts/`.
