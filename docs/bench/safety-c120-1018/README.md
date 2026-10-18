# product-output-safety confirmation, n=120: the frozen edit narrowly misses the keep rule, 2026-10-18

Question: does the exact edit frozen in `docs/bench/safety-r1-1018` (`prompts/edit.md`, byte-identical, sha256 `0f828a84...`, no retuning) beat the unedited `product-output-safety` on a new held-out set, and does it beat the promptfoo redteam-setup rival? Preregistered in `PREREGISTERED.md` (hash `SHA256-prereg.txt`; frozen list `SHA256-frozen.txt`; the first line of `ledger.jsonl` is the `preregistered` event holding the sha256 of `SHA256-frozen.txt`, written before any arm answer or judge call). PCSS models only, $0, no `claude -p`, `scripts/rival_eval.py` judge protocol v2 unchanged, judge GLM-5.1 (slot-1 rate 0.484, inside the 0.4 to 0.6 band, so no fallback judge), both orders, bootstrap 10,000 resamples seed 1. No tune phase.

Result (held-out, n=120 fresh scenarios `sc1h001`..`sc1h120`, win rate against the rival, 95% CI; no generation or verdict errors):

| Arm | Win rate [95% CI] | Win / tie / loss |
|---|---|---|
| V0 (unedited skill) | 0.550 [0.467, 0.633] | 58 / 16 / 46 |
| EDIT (frozen, unchanged) | 0.600 [0.521, 0.679] | 60 / 24 / 36 |

Paired EDIT minus V0: +0.050 [-0.004, +0.104] (22 scenarios up, 12 down, 86 unchanged).

Decision: keep rule (paired lower bound above 0) fails, -0.004, so the edit does not ship and `SKILL.md` is unchanged. The edit's own win-rate lower bound, 0.521, is above 0.5, but the edit is not shipped, so no superiority claim is made for the skill on main. The paired difference has the same sign as in `safety-r1-1018` (+0.083) and a smaller magnitude; the lower bound misses 0 by 0.004.

Descriptive only, not part of the preregistered decision: pooling the per-scenario paired differences of `safety-r1-1018` (n=60) and this bench (n=120), n=180, gives +0.061 [+0.011, +0.111] with the same bootstrap. The preregistered rule for this bench is the n=120 result above; the pooled interval is a post-hoc look at two benches whose second one was run because the first narrowly missed, so it is not a basis for shipping.

Limits: one generator family wrote the scenarios and all answers; judges are models; scenarios are fictional; the rival is a tool-driven red-team skill run without its tools. A failed keep rule means "not shown to help on this synthetic distribution at this n", not that the edit hurts.

Disjointness (checked after writing, before the freeze, over every scenario file under `docs/bench` and `scripts/eval-fixtures`, 2912 rows in 119 files, including all 80 `safety-r1-1018` rows): 0 id clashes, 0 exact normalized-text clashes, maximum 6-word shingle overlap of any new scenario with any earlier scenario 0.10; 120 distinct ids and texts. Seeds were rejected if close to any earlier bench seed, `safety-r1-1018` included.

Deviations from the preregistration, stated plainly: (1) `bench.py` was changed after `SHA256-prereg.txt` was written, in `as_list` only: the scenario writer sometimes returned one JSON object per line instead of an array and the first run of the scenario step failed on it, so `as_list` now accepts that form. It touches fixture writing only (no arm generation, judging or scoring code); `SHA256-frozen.txt` holds the final `bench.py`. (2) As in `safety-r1-1018`, seed and scenario writing ran before the `preregistered` ledger line, since the scenarios are part of what is frozen; no arm answer and no judge call did. (3) The seed-recognition regex in `bench.py` accepts two or three digits (`\d\d\d? `), so seeds numbered 100 and up are recognized as earlier seeds by later benches; this was set before `SHA256-prereg.txt` was written. Needs `PCSS_KEY` in the environment; `bench.py run` asserts that `prompts/edit.md` is the frozen r1 edit and that `prompts/v0.md` equals the live `SKILL.md`.

Files: `held/results.json` (per-scenario V0 and EDIT scores), `held/outputs/<ARM>/`, `held/<ARM>/judge/` (cached verdicts), `scenarios-heldout.json`, `seeds.txt`, `prompts/`.
